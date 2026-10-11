from typing import Optional

from fastapi import Query

from app.core.constants import SCORE_MAX, SCORE_MIN, SEARCH_MAX_LENGTH
from app.features.businesses.models import LeadStatus
from app.features.businesses.service import BusinessFilters


def business_filters(
    profile_id: Optional[int] = Query(None),
    segment: Optional[str] = Query(None, description="Segment slug; needs profile_id"),
    geography_id: Optional[int] = Query(None, description="A city, or a province/country for every city inside"),
    has_phone: Optional[bool] = Query(None),
    whatsapp_likely: Optional[bool] = Query(None),
    has_email: Optional[bool] = Query(None),
    has_website: Optional[bool] = Query(None),
    status: Optional[LeadStatus] = Query(None),
    assigned_to_id: Optional[int] = Query(None),
    unassigned: bool = Query(False),
    source: Optional[str] = Query(None, description="Only businesses this source reported"),
    min_score: Optional[int] = Query(None, ge=SCORE_MIN, le=SCORE_MAX),
    min_ai_fit: Optional[int] = Query(None, ge=SCORE_MIN, le=SCORE_MAX, description="Only leads the AI rated at least this fit"),
    search: Optional[str] = Query(None, max_length=SEARCH_MAX_LENGTH, description="Name, address, phone or email"),
) -> BusinessFilters:
    return BusinessFilters(
        profile_id=profile_id, segment=segment, geography_id=geography_id, has_phone=has_phone,
        whatsapp_likely=whatsapp_likely, has_email=has_email, has_website=has_website, status=status,
        assigned_to_id=assigned_to_id, unassigned=unassigned, source=source, min_score=min_score, min_ai_fit=min_ai_fit, search=search,
    )
