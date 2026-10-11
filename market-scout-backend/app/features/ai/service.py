import logging
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.ai.analyzer import (
    MAX_OUTPUT_TOKENS,
    SYSTEM_TEMPLATE,
    UNKNOWN_SEGMENT,
    AiError,
    AiStopError,
    AnalysisOutcome,
    LeadAnalyzer,
    LeadBrief,
    SegmentOption,
    build_client,
)
from app.core.ai.models import DEFAULT_MODEL_ID, MODELS, AiModel, cost_usd, get_model
from app.core.config import settings
from app.core.crypto import decrypt_secret, encrypt_secret, mask_secret
from app.core.database import WorkerSessionLocal
from app.core.exceptions import BadRequestException, NotFoundException
from app.core.scouting.enrichment.website import EnrichmentError, WebsiteEnricher
from app.features.ai.models import (
    ACTIVE_BATCH_STATUSES,
    AiBatch,
    AiUsage,
    AnalysisStatus,
    BatchStatus,
    LeadAiResult,
)
from app.features.ai.schemas import AiSettingsUpdate, AnalyzeRequest, EstimateRequest
from app.features.businesses.models import Business, BusinessClassification
from app.features.compliance import service as compliance_service
from app.features.jobs import service as jobs_service
from app.features.jobs.handler import JobHandler
from app.features.jobs.models import JobKind
from app.features.pipeline import service as pipeline_service
from app.features.pipeline.models import ActivityKind
from app.features.profiles.models import Profile, ProfileSegment
from app.features.sheets.models import AppSetting
from app.features.sources import service as sources_service

logger = logging.getLogger(__name__)

SETTINGS_KEY = "ai"
PAGE_TEXT_MAX_CHARS = 8000
PAGE_TEXT_MIN_CHARS = 200
PROMPT_OVERHEAD_CHARS = 1500
CHARS_PER_TOKEN_ESTIMATE = 3
ERROR_SAMPLES_MAX = 20
ERROR_TEXT_MAX_LENGTH = 300
INTERRUPTED_MESSAGE = "Interrupted by a server restart. Start it again to continue."
NOT_READY_MESSAGES = {
    "off": "The AI assistant is switched off. An administrator can turn it on under AI assistant.",
    "no_key": "The AI assistant has no Anthropic API key yet. An administrator can add one under AI assistant.",
    "unreadable_key": "The saved Anthropic API key can no longer be read. An administrator needs to enter it again.",
    "no_budget": "This month's AI budget is used up. An administrator can raise it under AI assistant.",
}
BUDGET_STOP_MESSAGE = "Stopped: the next analysis could have gone over this month's AI budget."
NO_WEBSITE_MESSAGE = "This business has no website to read."
BLOCKED_MESSAGE = "The website asks not to be read by automated tools (robots.txt)."
TOO_LITTLE_TEXT_MESSAGE = "The website has too little text to judge."
UNREADABLE_SITE_MESSAGE = "Couldn't read the website: {reason}"
NO_SUCH_SEGMENT_MESSAGE = "The AI didn't suggest a segment for this lead."
SEGMENT_GONE_MESSAGE = "That segment no longer exists in the profile."
NO_RESULT_MESSAGE = "This lead has not been analysed yet."

AnalyzerFactory = Callable[[str, AiModel], LeadAnalyzer]
EnricherFactory = Callable[[], WebsiteEnricher]


def _now() -> datetime:
    return datetime.now(UTC)


def _month_start() -> datetime:
    now = _now()
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _read(db: Session) -> dict:
    row = db.get(AppSetting, SETTINGS_KEY)
    return dict(row.value) if row is not None else {}


def _write(db: Session, value: dict) -> None:
    row = db.get(AppSetting, SETTINGS_KEY)
    if row is None:
        db.add(AppSetting(key=SETTINGS_KEY, value=value))
    else:
        row.value = value
    db.commit()


def _saved_key(stored: dict) -> tuple[str | None, bool]:
    token = stored.get("encrypted_key")
    if not token:
        return None, False
    plaintext = decrypt_secret(token)
    return plaintext, plaintext is None


def _resolve_key(stored: dict) -> tuple[str | None, str | None, bool]:
    saved, needs_reentry = _saved_key(stored)
    if saved:
        return saved, "saved", False
    if settings.ANTHROPIC_API_KEY:
        return settings.ANTHROPIC_API_KEY, "environment", needs_reentry
    return None, None, needs_reentry


def _model_for(stored: dict) -> AiModel:
    return get_model(stored.get("model", DEFAULT_MODEL_ID)) or get_model(DEFAULT_MODEL_ID)


def _budget(stored: dict) -> float:
    return float(stored.get("monthly_budget_usd", settings.AI_MONTHLY_BUDGET_USD))


def spent_this_month(db: Session) -> tuple[float, int]:
    spent, count = (
        db.query(func.coalesce(func.sum(AiUsage.cost_usd), 0.0), func.count(AiUsage.id))
        .filter(AiUsage.created_at >= _month_start())
        .one()
    )
    return float(spent), int(count)


def get_settings(db: Session) -> dict:
    stored = _read(db)
    key, key_source, needs_reentry = _resolve_key(stored)
    spent, count = spent_this_month(db)
    budget = _budget(stored)
    return {
        "is_enabled": bool(stored.get("is_enabled", False)),
        "has_key": key is not None,
        "key_hint": mask_secret(key) if key else None,
        "key_source": key_source,
        "key_needs_reentry": needs_reentry,
        "model": _model_for(stored).id,
        "models": [
            {
                "id": model.id,
                "label": model.label,
                "input_per_mtok_usd": model.input_per_mtok_usd,
                "output_per_mtok_usd": model.output_per_mtok_usd,
            }
            for model in MODELS
        ],
        "monthly_budget_usd": budget,
        "spent_this_month_usd": round(spent, 4),
        "remaining_usd": round(max(budget - spent, 0.0), 4),
        "analyses_this_month": count,
    }


def update_settings(db: Session, update_in: AiSettingsUpdate) -> dict:
    stored = _read(db)
    given = update_in.model_fields_set

    if "model" in given:
        if update_in.model is None or get_model(update_in.model) is None:
            raise BadRequestException("Choose one of the listed models")
        stored["model"] = update_in.model
    if "monthly_budget_usd" in given:
        if update_in.monthly_budget_usd is None:
            raise BadRequestException("The monthly budget needs a number")
        stored["monthly_budget_usd"] = update_in.monthly_budget_usd
    if update_in.api_key:
        stored["encrypted_key"] = encrypt_secret(update_in.api_key)
    elif update_in.clear_api_key:
        stored.pop("encrypted_key", None)
    if "is_enabled" in given:
        if update_in.is_enabled is None:
            raise BadRequestException("is_enabled must be true or false")
        stored["is_enabled"] = update_in.is_enabled

    key, _, _ = _resolve_key(stored)
    if stored.get("is_enabled") and key is None:
        if update_in.is_enabled is True:
            raise BadRequestException("Add an Anthropic API key before switching the AI assistant on")
        stored["is_enabled"] = False

    _write(db, stored)
    return get_settings(db)


def _not_ready_reason(stored: dict, db: Session) -> str | None:
    if not stored.get("is_enabled"):
        return "off"
    key, _, needs_reentry = _resolve_key(stored)
    if key is None:
        return "unreadable_key" if needs_reentry else "no_key"
    spent, _ = spent_this_month(db)
    if spent >= _budget(stored):
        return "no_budget"
    return None


def get_status(db: Session) -> dict:
    stored = _read(db)
    reason = _not_ready_reason(stored, db)
    spent, _ = spent_this_month(db)
    return {
        "is_ready": reason is None,
        "reason": NOT_READY_MESSAGES[reason] if reason else None,
        "model_label": _model_for(stored).label,
        "remaining_usd": round(max(_budget(stored) - spent, 0.0), 4),
    }


def _default_analyzer(api_key: str, model: AiModel) -> LeadAnalyzer:
    return LeadAnalyzer(build_client(api_key), model)


def test_key(db: Session, analyzer_factory: AnalyzerFactory | None = None) -> dict:
    stored = _read(db)
    key, _, needs_reentry = _resolve_key(stored)
    if key is None:
        return {"ok": False, "message": NOT_READY_MESSAGES["unreadable_key" if needs_reentry else "no_key"]}
    model = _model_for(stored)
    try:
        (analyzer_factory or _default_analyzer)(key, model).check_key()
    except AiError as exc:
        return {"ok": False, "message": str(exc)}
    return {"ok": True, "message": f"The key works with {model.label}."}


def _profile_with_segments(db: Session, profile_id: int) -> Profile:
    profile = db.get(Profile, profile_id)
    if profile is None:
        raise NotFoundException("Profile not found")
    return profile


def _segment_options(profile: Profile) -> list[SegmentOption]:
    return [SegmentOption(segment.slug, segment.name, segment.description) for segment in profile.segments]


def max_cost_per_lead(model: AiModel, profile: Profile) -> float:
    prompt_chars = (
        len(SYSTEM_TEMPLATE)
        + len(profile.ideal_customer or "")
        + sum(len(segment.name) + len(segment.description or "") + len(segment.slug) for segment in profile.segments)
        + PAGE_TEXT_MAX_CHARS
        + PROMPT_OVERHEAD_CHARS
    )
    return cost_usd(model, prompt_chars // CHARS_PER_TOKEN_ESTIMATE, MAX_OUTPUT_TOKENS)


def _visible_leads(db: Session, business_ids: list[int]) -> list[Business]:
    return (
        db.query(Business)
        .filter(Business.id.in_(set(business_ids)), compliance_service.not_blocked_filter())
        .order_by(Business.id)
        .all()
    )


def _analysed_ids(db: Session, business_ids: list[int], profile_id: int) -> set[int]:
    rows = db.query(LeadAiResult.business_id).filter(
        LeadAiResult.business_id.in_(set(business_ids)),
        LeadAiResult.profile_id == profile_id,
        LeadAiResult.status == AnalysisStatus.OK.value,
    )
    return {row[0] for row in rows}


def estimate(db: Session, estimate_in: EstimateRequest) -> dict:
    profile = _profile_with_segments(db, estimate_in.profile_id)
    stored = _read(db)
    model = _model_for(stored)
    leads = _visible_leads(db, estimate_in.business_ids)
    analysed = _analysed_ids(db, [lead.id for lead in leads], profile.id)

    without_website = sum(1 for lead in leads if not lead.website)
    already = 0 if estimate_in.refresh else sum(1 for lead in leads if lead.website and lead.id in analysed)
    to_analyze = sum(1 for lead in leads if lead.website) - already
    cost = round(to_analyze * max_cost_per_lead(model, profile), 4)

    spent, _ = spent_this_month(db)
    remaining = max(_budget(stored) - spent, 0.0)
    warnings = []
    if without_website:
        warnings.append(f"{without_website} without a website can't be read and will be skipped.")
    if already:
        warnings.append(f"{already} already analysed and will be skipped (turn on re-analyse to repeat them).")
    if cost > remaining:
        warnings.append("The worst-case cost is above what is left of this month's budget; the run stops before it is exceeded.")
    return {
        "leads": len(leads),
        "to_analyze": to_analyze,
        "without_website": without_website,
        "already_analyzed": already,
        "estimated_cost_usd": cost,
        "remaining_usd": round(remaining, 4),
        "within_budget": cost <= remaining,
        "model_label": model.label,
        "warnings": warnings,
    }


def start_batch(db: Session, analyze_in: AnalyzeRequest, user_id: int) -> AiBatch:
    stored = _read(db)
    reason = _not_ready_reason(stored, db)
    if reason is not None:
        raise BadRequestException(NOT_READY_MESSAGES[reason])
    _profile_with_segments(db, analyze_in.profile_id)
    leads = _visible_leads(db, analyze_in.business_ids)
    if not leads:
        raise NotFoundException("None of those leads were found")

    batch = AiBatch(
        profile_id=analyze_in.profile_id,
        created_by_id=user_id,
        status=BatchStatus.QUEUED.value,
        business_ids=[lead.id for lead in leads],
        refresh=analyze_in.refresh,
        total=len(leads),
    )
    db.add(batch)
    db.flush()
    jobs_service.enqueue(db, JobKind.AI_BATCH, batch.id)
    db.commit()
    db.refresh(batch)
    return batch


def get_batch(db: Session, batch_id: int) -> AiBatch:
    batch = db.get(AiBatch, batch_id)
    if batch is None:
        raise NotFoundException("Batch not found")
    return batch


def _upsert_result(
    db: Session, business_id: int, profile_id: int, user_id: int | None, outcome_fields: dict
) -> None:
    result = (
        db.query(LeadAiResult)
        .filter(LeadAiResult.business_id == business_id, LeadAiResult.profile_id == profile_id)
        .first()
    )
    if result is None:
        result = LeadAiResult(business_id=business_id, profile_id=profile_id)
        db.add(result)
    elif result.status == AnalysisStatus.OK.value and outcome_fields["status"] != AnalysisStatus.OK.value:
        return
    for name, value in outcome_fields.items():
        setattr(result, name, value)
    result.analyzed_at = _now()
    result.analyzed_by_id = user_id


def _failure_fields(status: AnalysisStatus, message: str, model: AiModel | None, pages_read: int = 0) -> dict:
    return {
        "status": status.value, "summary": None, "segment_slug": None, "segment_reason": None, "fit_score": None,
        "fit_reason": None, "confidence": None, "model": model.id if model else None, "pages_read": pages_read,
        "truncated": False, "error": message,
    }


def _success_fields(outcome: AnalysisOutcome, model: AiModel, segment_slugs: set[str], pages_read: int, truncated: bool) -> dict:
    payload = outcome.payload
    slug = payload.segment_slug if payload.segment_slug in segment_slugs else None
    score = None if payload.fit_score is None else max(0, min(100, payload.fit_score))
    return {
        "status": AnalysisStatus.OK.value, "summary": payload.summary.strip(), "segment_slug": slug,
        "segment_reason": payload.segment_reason.strip(), "fit_score": score, "fit_reason": payload.fit_reason.strip(),
        "confidence": payload.confidence, "model": model.id, "pages_read": pages_read, "truncated": truncated,
        "error": None,
    }


def _sample(batch: AiBatch, business_name: str, message: str) -> None:
    if len(batch.error_samples or []) < ERROR_SAMPLES_MAX:
        batch.error_samples = [*(batch.error_samples or []), f"{business_name}: {message}"[:ERROR_TEXT_MAX_LENGTH]]


def _finish(db: Session, batch: AiBatch, status: BatchStatus, error: str | None = None) -> None:
    batch.status = status.value
    batch.finished_at = _now()
    if error:
        batch.error = error
    db.commit()


def _lead_facts(db: Session, business_id: int) -> LeadBrief | None:
    lead = (
        db.query(Business)
        .filter(Business.id == business_id, compliance_service.not_blocked_filter())
        .first()
    )
    if lead is None:
        return None
    city = lead.geography.name if lead.geography is not None else None
    return LeadBrief(
        name=lead.name, address=lead.address, city=city, categories=list(lead.categories or []),
        website=lead.website, page_text="", truncated=False,
    )


def run_batch(
    db: Session, batch_id: int, *, analyzer_factory: AnalyzerFactory | None = None,
    enricher_factory: EnricherFactory | None = None,
) -> AiBatch | None:
    batch = db.get(AiBatch, batch_id)
    if batch is None or batch.status != BatchStatus.QUEUED.value:
        return batch
    batch.status = BatchStatus.RUNNING.value
    batch.started_at = _now()
    db.commit()

    stored = _read(db)
    key, _, _ = _resolve_key(stored)
    profile = db.get(Profile, batch.profile_id) if batch.profile_id else None
    if key is None or profile is None:
        _finish(db, batch, BatchStatus.FAILED, "The AI assistant isn't set up, or the profile was removed.")
        return batch

    model = _model_for(stored)
    budget = _budget(stored)
    per_lead_max = max_cost_per_lead(model, profile)
    segments = _segment_options(profile)
    segment_slugs = {segment.slug for segment in segments}
    ideal_customer = profile.ideal_customer
    profile_id = profile.id
    analyzer = (analyzer_factory or _default_analyzer)(key, model)
    enricher = (enricher_factory or _default_enricher)()
    already = set() if batch.refresh else _analysed_ids(db, list(batch.business_ids), profile_id)
    db.commit()

    for business_id in list(batch.business_ids)[batch.done:]:
        facts = _lead_facts(db, business_id)
        if facts is None or (business_id in already and facts.website):
            _count(db, batch, "skipped")
            continue

        if not facts.website:
            no_website = _failure_fields(AnalysisStatus.NO_TEXT, NO_WEBSITE_MESSAGE, None)
            _upsert_result(db, business_id, profile_id, batch.created_by_id, no_website)
            _count(db, batch, "skipped")
            continue

        spent, _ = spent_this_month(db)
        if spent + per_lead_max > budget:
            _finish(db, batch, BatchStatus.STOPPED, BUDGET_STOP_MESSAGE)
            return batch

        db.commit()
        site = _read_site(enricher, facts.website)
        if isinstance(site, str):
            _upsert_result(db, business_id, profile_id, batch.created_by_id, _failure_fields(AnalysisStatus.NO_TEXT, site, None))
            _sample(batch, facts.name, site)
            _count(db, batch, "skipped")
            continue

        text, truncated, pages = site
        brief = replace(facts, page_text=text, truncated=truncated)
        try:
            outcome = analyzer.analyze(brief, segments, ideal_customer)
        except AiStopError as exc:
            _finish(db, batch, BatchStatus.STOPPED, str(exc))
            return batch

        _record_outcome(db, batch, business_id, profile_id, facts.name, outcome, model, segment_slugs, pages, truncated)

    _finish(db, batch, BatchStatus.COMPLETED)
    return batch


def _default_enricher() -> WebsiteEnricher:
    return WebsiteEnricher(user_agent=sources_service.user_agent())


def _read_site(enricher: WebsiteEnricher, website: str) -> tuple[str, bool, int] | str:
    try:
        page = enricher.read_text(website, PAGE_TEXT_MAX_CHARS)
    except EnrichmentError as exc:
        return UNREADABLE_SITE_MESSAGE.format(reason=exc)
    except Exception:
        logger.exception("Unexpected error reading %s", website)
        return UNREADABLE_SITE_MESSAGE.format(reason="unexpected error")
    if page.blocked_by_robots:
        return BLOCKED_MESSAGE
    if len(page.text) < PAGE_TEXT_MIN_CHARS:
        return TOO_LITTLE_TEXT_MESSAGE
    return page.text, page.truncated, page.pages_read


def _count(db: Session, batch: AiBatch, field: str) -> None:
    batch.done += 1
    setattr(batch, field, getattr(batch, field) + 1)
    db.commit()


def _record_outcome(
    db: Session, batch: AiBatch, business_id: int, profile_id: int, name: str, outcome: AnalysisOutcome, model: AiModel,
    segment_slugs: set[str], pages: int, truncated: bool,
) -> None:
    cost = cost_usd(model, outcome.input_tokens, outcome.output_tokens)
    if outcome.input_tokens or outcome.output_tokens:
        db.add(
            AiUsage(
                business_id=business_id, model=model.id, input_tokens=outcome.input_tokens,
                output_tokens=outcome.output_tokens, cost_usd=cost, status=outcome.status,
            )
        )
        batch.spent_usd = round(batch.spent_usd + cost, 6)

    if outcome.status == "ok":
        fields = _success_fields(outcome, model, segment_slugs, pages, truncated)
        field_name = "analyzed"
    elif outcome.status == "declined":
        fields = _failure_fields(AnalysisStatus.DECLINED, outcome.error or "", model, pages)
        field_name = "declined"
        _sample(batch, name, outcome.error or "")
    else:
        fields = _failure_fields(AnalysisStatus.FAILED, outcome.error or "", model, pages)
        field_name = "failed"
        _sample(batch, name, outcome.error or "")
    _upsert_result(db, business_id, profile_id, batch.created_by_id, fields)
    _count(db, batch, field_name)


def run_batch_in_new_session(batch_id: int) -> None:
    db = WorkerSessionLocal()
    try:
        run_batch(db, batch_id)
    except Exception:
        logger.exception("AI batch %s failed", batch_id)
        db.rollback()
        batch = db.get(AiBatch, batch_id)
        if batch is not None and batch.status in ACTIVE_BATCH_STATUSES:
            _finish(db, batch, BatchStatus.FAILED, "Unexpected error (see the server log).")
    finally:
        db.close()


def recover_batch(db: Session, batch_id: int, retries_left: bool) -> bool:
    batch = db.get(AiBatch, batch_id, populate_existing=True)
    if batch is None or batch.status != BatchStatus.RUNNING.value:
        return False
    if retries_left:
        batch.status = BatchStatus.QUEUED.value
        batch.error = None
        db.commit()
        return True
    batch.status = BatchStatus.FAILED.value
    batch.error = INTERRUPTED_MESSAGE
    batch.finished_at = _now()
    db.commit()
    return False


def _queued_batch_ids(db: Session) -> list[int]:
    return [row[0] for row in db.query(AiBatch.id).filter(AiBatch.status == BatchStatus.QUEUED.value).order_by(AiBatch.id)]


def _running_batch_ids(db: Session) -> list[int]:
    return [row[0] for row in db.query(AiBatch.id).filter(AiBatch.status == BatchStatus.RUNNING.value).order_by(AiBatch.id)]


JOB_HANDLER = JobHandler(
    execute=run_batch_in_new_session, recover=recover_batch, queued_ids=_queued_batch_ids, running_ids=_running_batch_ids
)


def get_result_view(db: Session, business_id: int, profile_id: int | None) -> dict | None:
    query = db.query(LeadAiResult).filter(LeadAiResult.business_id == business_id)
    if profile_id is not None:
        query = query.filter(LeadAiResult.profile_id == profile_id)
    result = query.order_by(LeadAiResult.analyzed_at.desc(), LeadAiResult.id.desc()).first()
    if result is None:
        return None
    segment_ids = {
        slug: segment_id
        for segment_id, slug in db.query(ProfileSegment.id, ProfileSegment.slug).filter(ProfileSegment.profile_id == result.profile_id)
    }
    names = dict(db.query(ProfileSegment.slug, ProfileSegment.name).filter(ProfileSegment.profile_id == result.profile_id))
    current_segment_id = (
        db.query(BusinessClassification.segment_id)
        .filter(BusinessClassification.business_id == business_id, BusinessClassification.profile_id == result.profile_id)
        .scalar()
    )
    current_slug = next((slug for slug, segment_id in segment_ids.items() if segment_id == current_segment_id), None)
    return {
        "profile_id": result.profile_id, "status": result.status, "summary": result.summary,
        "segment_slug": result.segment_slug, "segment_name": names.get(result.segment_slug),
        "segment_reason": result.segment_reason, "current_segment_slug": current_slug, "fit_score": result.fit_score,
        "fit_reason": result.fit_reason, "confidence": result.confidence, "model": result.model,
        "pages_read": result.pages_read, "truncated": result.truncated, "error": result.error,
        "analyzed_at": result.analyzed_at,
    }


def apply_segment(db: Session, business_id: int, profile_id: int, user_id: int) -> dict:
    business = (
        db.query(Business).filter(Business.id == business_id, compliance_service.not_blocked_filter()).first()
    )
    if business is None:
        raise NotFoundException("Business not found")
    result = (
        db.query(LeadAiResult)
        .filter(LeadAiResult.business_id == business_id, LeadAiResult.profile_id == profile_id)
        .first()
    )
    if result is None or result.status != AnalysisStatus.OK.value:
        raise BadRequestException(NO_RESULT_MESSAGE)
    if not result.segment_slug or result.segment_slug == UNKNOWN_SEGMENT:
        raise BadRequestException(NO_SUCH_SEGMENT_MESSAGE)
    segment = (
        db.query(ProfileSegment)
        .filter(ProfileSegment.profile_id == profile_id, ProfileSegment.slug == result.segment_slug)
        .first()
    )
    if segment is None:
        raise BadRequestException(SEGMENT_GONE_MESSAGE)

    classification = (
        db.query(BusinessClassification)
        .filter(BusinessClassification.business_id == business_id, BusinessClassification.profile_id == profile_id)
        .first()
    )
    if classification is None:
        classification = BusinessClassification(business_id=business_id, profile_id=profile_id, score=0)
        db.add(classification)
    before = (
        db.query(ProfileSegment.name).filter(ProfileSegment.id == classification.segment_id).scalar()
        if classification.segment_id
        else None
    )
    if classification.segment_id != segment.id:
        classification.segment_id = segment.id
        pipeline_service.add_system_activity(
            db, business_id, ActivityKind.SEGMENT_CHANGED, user_id, from_value=before, to_value=segment.name,
            summary="Applied the AI's suggestion",
        )
    db.commit()
    return get_result_view(db, business_id, profile_id)


def fit_scores(db: Session, business_ids: list[int], profile_id: int | None) -> dict[int, int]:
    if not business_ids:
        return {}
    query = db.query(LeadAiResult.business_id, func.max(LeadAiResult.fit_score)).filter(
        LeadAiResult.business_id.in_(business_ids), LeadAiResult.status == AnalysisStatus.OK.value,
        LeadAiResult.fit_score.isnot(None),
    )
    if profile_id is not None:
        query = query.filter(LeadAiResult.profile_id == profile_id)
    return {business_id: score for business_id, score in query.group_by(LeadAiResult.business_id)}
