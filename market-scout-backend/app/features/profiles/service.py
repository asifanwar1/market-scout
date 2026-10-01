from sqlalchemy.orm import Session

from app.core.constants import FIRST_PAGE
from app.core.exceptions import BadRequestException, ConflictException, NotFoundException
from app.core.utils import slugify
from app.features.profiles.models import Profile, ProfileSearchTerm, ProfileSegment
from app.features.profiles.schemas import (
    ProfileCreate,
    ProfileUpdate,
    SearchTermCreate,
    SearchTermUpsert,
    SegmentCreate,
    SegmentUpsert,
)

DEFAULT_LIMIT = 10



def _generate_unique_slug(db: Session, name: str) -> str:
    base_slug = slugify(name, fallback="profile")
    slug = base_slug
    counter = 2

    while db.query(Profile).filter(Profile.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


def _ensure_name_available(db: Session, name: str, exclude_id: int | None = None) -> None:
    query = db.query(Profile).filter(Profile.name == name)
    if exclude_id is not None:
        query = query.filter(Profile.id != exclude_id)
    if query.first():
        raise ConflictException("A profile with this name already exists")


def _fill_segment(segment: ProfileSegment, segment_in: SegmentCreate) -> None:
    segment.name = segment_in.name.strip()
    segment.slug = segment_in.slug
    segment.description = segment_in.description
    segment.match_rules = segment_in.match_rules.model_dump()
    segment.sort_order = segment_in.sort_order


def _fill_search_term(term: ProfileSearchTerm, term_in: SearchTermCreate, segment: ProfileSegment) -> None:
    term.segment = segment
    term.text = term_in.text
    term.osm_filter = term_in.osm_filter.model_dump() if term_in.osm_filter else None
    term.language = term_in.language.value
    term.is_active = term_in.is_active


def _sync_segments(db: Session, profile: Profile, segments_in: list[SegmentUpsert] | list[SegmentCreate]) -> None:
    existing = {segment.id: segment for segment in profile.segments}
    wanted_ids = {segment_in.id for segment_in in segments_in if getattr(segment_in, "id", None) is not None}

    unknown = wanted_ids - existing.keys()
    if unknown:
        raise BadRequestException(f"Segment {min(unknown)} does not belong to this profile")

    for segment_id, segment in existing.items():
        if segment_id not in wanted_ids:
            profile.segments.remove(segment)
    db.flush()
    db.expire(profile, ["search_terms"])

    for segment_in in segments_in:
        segment_id = getattr(segment_in, "id", None)
        if segment_id is None:
            segment = ProfileSegment()
            profile.segments.append(segment)
        else:
            segment = existing[segment_id]
        _fill_segment(segment, segment_in)
    db.flush()


def _sync_search_terms(db: Session, profile: Profile, terms_in: list[SearchTermUpsert] | list[SearchTermCreate]) -> None:
    segments_by_slug = {segment.slug: segment for segment in profile.segments}
    existing = {term.id: term for term in profile.search_terms}
    wanted_ids = {term_in.id for term_in in terms_in if getattr(term_in, "id", None) is not None}

    unknown = wanted_ids - existing.keys()
    if unknown:
        raise BadRequestException(f"Search term {min(unknown)} does not belong to this profile")
    for term_in in terms_in:
        if term_in.segment_slug not in segments_by_slug:
            raise BadRequestException(f"Unknown segment '{term_in.segment_slug}'")

    for term_id, term in existing.items():
        if term_id not in wanted_ids:
            profile.search_terms.remove(term)
    db.flush()

    for term_in in terms_in:
        term_id = getattr(term_in, "id", None)
        if term_id is None:
            term = ProfileSearchTerm()
            profile.search_terms.append(term)
        else:
            term = existing[term_id]
        _fill_search_term(term, term_in, segments_by_slug[term_in.segment_slug])
    db.flush()


def get_profiles(
    db: Session,
    page: int = FIRST_PAGE,
    limit: int = DEFAULT_LIMIT,
    search: str | None = None,
    is_active: bool | None = None,
) -> dict:
    query = db.query(Profile)

    if is_active is not None:
        query = query.filter(Profile.is_active == is_active)
    if search:
        normalized_search = search.strip()
        if normalized_search:
            search_term = f"%{normalized_search}%"
            query = query.filter(Profile.name.ilike(search_term) | Profile.description.ilike(search_term))

    total_count = query.count()
    offset = (page - 1) * limit
    profiles = query.order_by(Profile.name, Profile.id).offset(offset).limit(limit).all()
    return {"data": profiles, "count": total_count}


def get_profile_by_id(db: Session, profile_id: int) -> Profile:
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile:
        raise NotFoundException("Profile not found")
    return profile


def get_profile_by_slug(db: Session, slug: str) -> Profile | None:
    return db.query(Profile).filter(Profile.slug == slug).first()


def create_profile(db: Session, profile_in: ProfileCreate) -> Profile:
    _ensure_name_available(db, profile_in.name)

    profile = Profile(
        name=profile_in.name.strip(),
        slug=_generate_unique_slug(db, profile_in.name),
        description=profile_in.description,
        is_active=profile_in.is_active,
        scoring_config=profile_in.scoring_config.model_dump(),
    )
    db.add(profile)
    _sync_segments(db, profile, profile_in.segments)
    _sync_search_terms(db, profile, profile_in.search_terms)
    db.commit()
    db.refresh(profile)
    return profile


def update_profile(db: Session, profile_id: int, profile_in: ProfileUpdate) -> Profile:
    profile = get_profile_by_id(db, profile_id)
    update_data = profile_in.model_dump(exclude_unset=True, exclude={"segments", "search_terms"})

    if update_data.get("name") is not None:
        _ensure_name_available(db, update_data["name"], exclude_id=profile.id)
        profile.name = update_data["name"].strip()
    if "description" in update_data:
        profile.description = update_data["description"]
    if update_data.get("is_active") is not None:
        profile.is_active = update_data["is_active"]
    if update_data.get("scoring_config") is not None:
        profile.scoring_config = update_data["scoring_config"]

    if profile_in.segments is not None:
        _sync_segments(db, profile, profile_in.segments)
    if profile_in.search_terms is not None:
        _sync_search_terms(db, profile, profile_in.search_terms)

    db.commit()
    db.refresh(profile)
    return profile


def delete_profile(db: Session, profile_id: int) -> None:
    profile = get_profile_by_id(db, profile_id)
    db.delete(profile)
    db.commit()
