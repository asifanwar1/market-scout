import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestException, ConflictException
from app.core.scouting.types import RawBusiness
from app.features.businesses import ingest as businesses_ingest
from app.features.businesses.ingest import IngestContext
from app.features.geographies.models import Geography, GeographyLevel
from app.features.profiles.models import Profile
from app.features.public_api.schemas import PublicLeadCreate

API_SOURCE_KEY = "api"
NO_PROFILE_MESSAGE = "There is no profile yet; create one in the app first"
PROFILE_MISSING_MESSAGE = "That profile doesn't exist"
SEGMENT_MISSING_MESSAGE = "That business type isn't part of the chosen profile"
CITY_MESSAGE = "city_id must be one of the cities"
BLOCKED_MESSAGE = "This business or one of its contacts is on the do-not-contact list"
NO_CONTACT_MESSAGE = "Give at least one phone, email or website"


def create_lead(db: Session, lead_in: PublicLeadCreate) -> dict:
    if not (lead_in.phones or lead_in.emails or lead_in.website):
        raise BadRequestException(NO_CONTACT_MESSAGE)

    if lead_in.profile_id is not None:
        profile = db.get(Profile, lead_in.profile_id)
        if profile is None:
            raise BadRequestException(PROFILE_MISSING_MESSAGE)
    else:
        profile = db.query(Profile).order_by(Profile.id).first()
        if profile is None:
            raise BadRequestException(NO_PROFILE_MESSAGE)
    if lead_in.segment_slug and lead_in.segment_slug not in {segment.slug for segment in profile.segments}:
        raise BadRequestException(SEGMENT_MISSING_MESSAGE)

    geography_id = None
    if lead_in.city_id is not None:
        city = db.get(Geography, lead_in.city_id)
        if city is None or city.level != GeographyLevel.CITY.value:
            raise BadRequestException(CITY_MESSAGE)
        geography_id = city.id

    raw = RawBusiness(
        source_key=API_SOURCE_KEY, external_id=uuid.uuid4().hex, name=lead_in.name, address=lead_in.address,
        phones=lead_in.phones, emails=lead_in.emails, website=lead_in.website,
    )
    context = IngestContext(
        run_id=None, geography_id=geography_id, hint_segment_slug=lead_in.segment_slug, now=datetime.now(UTC),
        profile=businesses_ingest.build_profile_scoring(profile),
    )
    outcome = businesses_ingest.ingest_business(db, raw, context)
    if outcome.blocked or outcome.business is None:
        db.rollback()
        raise ConflictException(BLOCKED_MESSAGE)
    db.commit()
    return {"id": outcome.business.id, "created": outcome.created}
