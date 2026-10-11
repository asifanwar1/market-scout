import math
from datetime import UTC, datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.constants import SCORE_MAX, SCORE_MIN
from app.core.exceptions import BadRequestException, NotFoundException
from app.core.scouting.classify import LeadSignals, classify, score_lead
from app.features.businesses import ingest as businesses_ingest
from app.features.businesses.models import Business, BusinessClassification, CheckStatus, ContactKind, ContactPoint, WebsiteStatus
from app.features.pipeline.models import LeadOutcome, OutcomeKind
from app.features.profiles.models import Profile
from app.features.profiles.schemas import ScoringConfig
from app.features.sheets.models import AppSetting

MIN_CLOSED_DEALS = 30
MIN_PER_SIDE = 5
Z_SIGNIFICANT = 1.64
SHARE_OF_DIFFERENCE = 0.5
MAX_STEP = 25
PERCENT = 100
CHUNK = 500
MIN_REVIEWS_FOR_BONUS = 3
PREVIOUS_KEY = "quality_scoring_previous_{profile_id}"
PHONE_KINDS = (ContactKind.PHONE.value, ContactKind.WHATSAPP.value)

TRAIT_LABELS = {
    "has_phone": "Has a phone number",
    "has_whatsapp_likely": "Has a mobile number (likely WhatsApp)",
    "has_website": "Has a working website",
    "has_email": "Has a working email",
    "has_reviews": "Has 3 or more reviews",
    "name_matches_segment": "Name matches its kind of business",
}

NOTE_NEEDS_DATA = "Not enough leads on both sides to say anything yet"
NOTE_NOT_CLEAR = "No clear difference"
NOTE_RAISE = "Leads with this closed more often, so it earns more weight"
NOTE_LOWER = "Leads with this closed less often, so it earns less weight"
NOTE_AT_LIMIT = "Clearly linked to winning, but the weight is already at its limit"
NOT_ENOUGH_MESSAGE = "There are not enough closed deals yet to suggest changes"
NOTHING_TO_CHANGE_MESSAGE = "Nothing to change: no trait shows a clear difference"
NO_PREVIOUS_MESSAGE = "There is no earlier weighting to go back to"
PROFILE_NOT_FOUND = "Profile not found"


def _now() -> datetime:
    return datetime.now(UTC)


def _chunks(values: list[int]):
    for start in range(0, len(values), CHUNK):
        yield values[start:start + CHUNK]


def lead_traits(db: Session, profile: Profile, business_ids: list[int]) -> dict[int, tuple[LeadSignals, bool]]:
    scoring = businesses_ingest.build_profile_scoring(profile)
    slug_by_id = {segment_id: slug for slug, segment_id in scoring.segment_ids.items()}
    result: dict[int, tuple[LeadSignals, bool]] = {}
    for ids in _chunks(business_ids):
        leads = {
            row.id: row
            for row in db.query(Business.id, Business.name, Business.website, Business.website_status, Business.review_count).filter(
                Business.id.in_(ids)
            )
        }
        contacts: dict[int, list[tuple[str, bool]]] = {}
        rows = db.query(ContactPoint.business_id, ContactPoint.kind, ContactPoint.whatsapp_likely).filter(
            ContactPoint.business_id.in_(ids),
            or_(ContactPoint.check_status.is_(None), ContactPoint.check_status != CheckStatus.BAD.value),
        )
        for business_id, kind, likely in rows:
            contacts.setdefault(business_id, []).append((kind, likely))
        segments = dict(
            db.query(BusinessClassification.business_id, BusinessClassification.segment_id).filter(
                BusinessClassification.profile_id == profile.id, BusinessClassification.business_id.in_(ids)
            )
        )
        for business_id, lead in leads.items():
            found = contacts.get(business_id, [])
            signals = LeadSignals(
                has_phone=any(kind in PHONE_KINDS for kind, _ in found),
                has_whatsapp_likely=any(likely or kind == ContactKind.WHATSAPP.value for kind, likely in found),
                has_website=bool(lead.website) and lead.website_status != WebsiteStatus.DEAD.value,
                has_email=any(kind == ContactKind.EMAIL.value for kind, _ in found),
                review_count=lead.review_count,
            )
            hint = slug_by_id.get(segments.get(business_id))
            matched = classify(lead.name, hint, scoring.segment_rules).name_matched
            result[business_id] = (signals, matched)
    return result


def _trait_flags(signals: LeadSignals, name_matched: bool) -> dict[str, bool]:
    return {
        "has_phone": signals.has_phone,
        "has_whatsapp_likely": signals.has_whatsapp_likely,
        "has_website": signals.has_website,
        "has_email": signals.has_email,
        "has_reviews": (signals.review_count or 0) >= MIN_REVIEWS_FOR_BONUS,
        "name_matches_segment": name_matched,
    }


def _weights(profile: Profile) -> dict[str, int]:
    return {**ScoringConfig().model_dump(), **(profile.scoring_config or {})}


def _z_score(with_wins: int, with_count: int, without_wins: int, without_count: int) -> float:
    if not with_count or not without_count:
        return 0.0
    pooled = (with_wins + without_wins) / (with_count + without_count)
    spread = math.sqrt(pooled * (1 - pooled) * (1 / with_count + 1 / without_count))
    if spread == 0:
        return 0.0
    return (with_wins / with_count - without_wins / without_count) / spread


def _clamp(value: int) -> int:
    return max(SCORE_MIN, min(SCORE_MAX, value))


def _assess(key: str, tally: dict[str, int], current: int) -> dict:
    with_count, with_wins = tally["with_count"], tally["with_wins"]
    without_count, without_wins = tally["without_count"], tally["without_wins"]
    enough = with_count >= MIN_PER_SIDE and without_count >= MIN_PER_SIDE
    rate_with = with_wins / with_count if with_count else None
    rate_without = without_wins / without_count if without_count else None
    difference = (rate_with - rate_without) * PERCENT if enough else None
    significant = enough and abs(_z_score(with_wins, with_count, without_wins, without_count)) >= Z_SIGNIFICANT

    suggested, note = current, NOTE_NEEDS_DATA
    if enough:
        note = NOTE_NOT_CLEAR
    if significant:
        step = max(-MAX_STEP, min(MAX_STEP, round(difference * SHARE_OF_DIFFERENCE)))
        suggested = _clamp(current + step)
        note = NOTE_RAISE if difference > 0 else NOTE_LOWER
        if suggested == current:
            note = NOTE_AT_LIMIT
    return {
        "key": key,
        "label": TRAIT_LABELS[key],
        "with_count": with_count,
        "with_wins": with_wins,
        "without_count": without_count,
        "without_wins": without_wins,
        "win_rate_with": None if rate_with is None else round(rate_with * PERCENT, 1),
        "win_rate_without": None if rate_without is None else round(rate_without * PERCENT, 1),
        "difference": None if difference is None else round(difference, 1),
        "significant": significant,
        "current_weight": current,
        "suggested_weight": suggested,
        "note": note,
    }


def _get_profile(db: Session, profile_id: int) -> Profile:
    profile = db.get(Profile, profile_id)
    if profile is None:
        raise NotFoundException(PROFILE_NOT_FOUND)
    return profile


def analyse(db: Session, profile_id: int) -> dict:
    profile = _get_profile(db, profile_id)
    closed = dict(
        db.query(LeadOutcome.business_id, LeadOutcome.kind)
        .join(BusinessClassification, BusinessClassification.business_id == LeadOutcome.business_id)
        .filter(BusinessClassification.profile_id == profile.id, LeadOutcome.kind.in_([OutcomeKind.WON.value, OutcomeKind.LOST.value]))
        .all()
    )
    traits = lead_traits(db, profile, list(closed))
    tallies = {key: dict(with_count=0, with_wins=0, without_count=0, without_wins=0) for key in TRAIT_LABELS}
    for business_id, kind in closed.items():
        if business_id not in traits:
            continue
        won = kind == OutcomeKind.WON.value
        for key, has in _trait_flags(*traits[business_id]).items():
            side = "with" if has else "without"
            tallies[key][f"{side}_count"] += 1
            tallies[key][f"{side}_wins"] += won

    weights = _weights(profile)
    assessed = [_assess(key, tallies[key], weights[key]) for key in TRAIT_LABELS]
    total = len(traits)
    wins = sum(1 for business_id in traits if closed[business_id] == OutcomeKind.WON.value)
    enough = total >= MIN_CLOSED_DEALS
    if not enough:
        assessed = [{**item, "suggested_weight": item["current_weight"], "significant": False} for item in assessed]
    return {
        "profile_id": profile.id,
        "profile_name": profile.name,
        "closed": total,
        "won": wins,
        "lost": total - wins,
        "needed": MIN_CLOSED_DEALS,
        "enough_data": enough,
        "traits": assessed,
        "can_apply": enough and any(item["suggested_weight"] != item["current_weight"] for item in assessed),
        "can_revert": db.get(AppSetting, PREVIOUS_KEY.format(profile_id=profile.id)) is not None,
    }


def rescore_profile(db: Session, profile: Profile) -> int:
    weights = _weights(profile)
    rows = db.query(BusinessClassification.id, BusinessClassification.business_id, BusinessClassification.score).filter(
        BusinessClassification.profile_id == profile.id
    ).all()
    by_business = {business_id: (row_id, score) for row_id, business_id, score in rows}
    for ids in _chunks(list(by_business)):
        traits = lead_traits(db, profile, ids)
        updates = []
        for business_id in ids:
            if business_id not in traits:
                continue
            signals, matched = traits[business_id]
            row_id, score = by_business[business_id]
            new_score = score_lead(signals, matched, weights)
            if new_score != score:
                updates.append({"id": row_id, "score": new_score})
        if updates:
            db.bulk_update_mappings(BusinessClassification, updates)
        db.commit()
    return len(by_business)


def apply_suggestion(db: Session, profile_id: int) -> dict:
    report = analyse(db, profile_id)
    if not report["enough_data"]:
        raise BadRequestException(NOT_ENOUGH_MESSAGE)
    if not report["can_apply"]:
        raise BadRequestException(NOTHING_TO_CHANGE_MESSAGE)

    profile = _get_profile(db, profile_id)
    before = _weights(profile)
    after = {**before, **{item["key"]: item["suggested_weight"] for item in report["traits"]}}
    key = PREVIOUS_KEY.format(profile_id=profile.id)
    value = {"scoring_config": before, "applied_at": _now().isoformat()}
    row = db.get(AppSetting, key)
    if row is None:
        db.add(AppSetting(key=key, value=value))
    else:
        row.value = value
    profile.scoring_config = after
    db.commit()
    return {"weights": after, "rescored": rescore_profile(db, profile)}


def revert(db: Session, profile_id: int) -> dict:
    profile = _get_profile(db, profile_id)
    row = db.get(AppSetting, PREVIOUS_KEY.format(profile_id=profile.id))
    if row is None:
        raise BadRequestException(NO_PREVIOUS_MESSAGE)
    profile.scoring_config = dict(row.value["scoring_config"])
    db.delete(row)
    db.commit()
    return {"weights": _weights(profile), "rescored": rescore_profile(db, profile)}
