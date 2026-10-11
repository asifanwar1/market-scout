import csv
import io
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import IO

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import BYTES_PER_MEGABYTE
from app.core.scouting.sources.registry import source_label
from app.features.businesses import service as businesses_service
from app.features.businesses.models import Business, ContactKind, LeadStatus
from app.features.businesses.schemas import BusinessSort, SortDirection
from app.features.businesses.service import BusinessFilters
from app.features.exports.service import csv_safe
from app.features.pipeline.models import LeadOutcome

SPOOL_MAX_MEGABYTES = 8
BOM = "﻿"
DEFAULT_COUNTRY = "Pakistan"
LEAD_SOURCE = "Market Scout"
PHONE_KINDS = (ContactKind.PHONE.value, ContactKind.WHATSAPP.value)
NAME_SEPARATOR = " "
LIST_SEPARATOR = "; "
DATE_FORMAT = "%Y-%m-%d"


class CrmLayout(str, Enum):
    HUBSPOT = "hubspot"
    ZOHO = "zoho"
    GENERIC = "generic"


HUBSPOT_LIFECYCLE = {
    LeadStatus.NEW.value: "Lead",
    LeadStatus.CONTACTED.value: "Lead",
    LeadStatus.INTERESTED.value: "Sales Qualified Lead",
    LeadStatus.MEETING.value: "Opportunity",
    LeadStatus.QUOTED.value: "Opportunity",
    LeadStatus.CUSTOMER.value: "Customer",
    LeadStatus.NOT_INTERESTED.value: "Other",
}

ZOHO_LEAD_STATUS = {
    LeadStatus.NEW.value: "Not Contacted",
    LeadStatus.CONTACTED.value: "Contacted",
    LeadStatus.INTERESTED.value: "Pre-Qualified",
    LeadStatus.MEETING.value: "Pre-Qualified",
    LeadStatus.QUOTED.value: "Pre-Qualified",
    LeadStatus.CUSTOMER.value: "Contacted",
    LeadStatus.NOT_INTERESTED.value: "Lost Lead",
}

HUBSPOT_HEADERS = [
    "Company name", "Company Domain Name", "Phone Number", "City", "State/Region", "Country/Region", "Street Address",
    "Description", "Lifecycle Stage", "Contact Name", "Contact Email", "All phone numbers", "Market Scout status",
    "Market Scout score", "Market Scout segment", "Market Scout lead ID",
]

ZOHO_HEADERS = [
    "Company", "First Name", "Last Name", "Email", "Phone", "Mobile", "Website", "Street", "City", "State", "Country",
    "Lead Source", "Lead Status", "Description", "Market Scout status", "Market Scout score", "Market Scout lead ID",
]

GENERIC_HEADERS = [
    "Lead ID", "Company", "Contact name", "Phone", "Mobile", "Email", "Website", "Address", "City", "State/Province", "Country",
    "Status", "Score", "Segment", "Found by", "Notes", "Deal outcome", "Deal value", "Deal currency", "Deal product",
    "Loss reason", "Closed on",
]


@dataclass(frozen=True)
class Facts:
    business: Business
    phone: str
    mobile: str
    all_phones: list[str]
    emails: list[str]
    city: str
    province: str
    segment: str
    score: int | str
    sources: str
    outcome: LeadOutcome | None


def _split_name(contact_name: str | None, company: str) -> tuple[str, str]:
    parts = (contact_name or "").split()
    if not parts:
        return "", company
    return NAME_SEPARATOR.join(parts[:-1]), parts[-1]


def _status_text(status: str) -> str:
    return status.replace("_", NAME_SEPARATOR).capitalize()


def _hubspot(facts: Facts) -> list:
    business = facts.business
    return [
        business.name, business.website_domain or "", facts.phone or facts.mobile, facts.city, facts.province, DEFAULT_COUNTRY,
        business.address or "", business.notes or "", HUBSPOT_LIFECYCLE.get(business.lead_status, ""),
        business.contact_name or "", facts.emails[0] if facts.emails else "", LIST_SEPARATOR.join(facts.all_phones),
        _status_text(business.lead_status), facts.score, facts.segment, business.id,
    ]


def _zoho(facts: Facts) -> list:
    business = facts.business
    first, last = _split_name(business.contact_name, business.name)
    return [
        business.name, first, last, facts.emails[0] if facts.emails else "", facts.phone, facts.mobile, business.website or "",
        business.address or "", facts.city, facts.province, DEFAULT_COUNTRY, LEAD_SOURCE,
        ZOHO_LEAD_STATUS.get(business.lead_status, ""), business.notes or "", _status_text(business.lead_status), facts.score,
        business.id,
    ]


def _generic(facts: Facts) -> list:
    business = facts.business
    outcome = facts.outcome
    return [
        business.id, business.name, business.contact_name or "", facts.phone, facts.mobile, LIST_SEPARATOR.join(facts.emails),
        business.website or "", business.address or "", facts.city, facts.province, DEFAULT_COUNTRY,
        _status_text(business.lead_status), facts.score, facts.segment, facts.sources, business.notes or "",
        outcome.kind if outcome else "", outcome.value if outcome and outcome.value is not None else "",
        settings.DEAL_CURRENCY if outcome and outcome.value is not None else "", outcome.product or "" if outcome else "",
        outcome.loss_reason or "" if outcome else "", outcome.closed_at.strftime(DATE_FORMAT) if outcome else "",
    ]


LAYOUTS: dict[CrmLayout, tuple[list[str], Callable[[Facts], list]]] = {
    CrmLayout.HUBSPOT: (HUBSPOT_HEADERS, _hubspot),
    CrmLayout.ZOHO: (ZOHO_HEADERS, _zoho),
    CrmLayout.GENERIC: (GENERIC_HEADERS, _generic),
}


def _facts(business: Business, lookups, outcomes: dict[int, LeadOutcome], profile_id: int | None) -> Facts:
    classifications = [c for c in business.classifications if profile_id is None or c.profile_id == profile_id]
    chosen = max(classifications, key=lambda c: c.score, default=None)
    segment = lookups.segments.get(chosen.segment_id) if chosen and chosen.segment_id else None
    contacts = sorted(business.contact_points, key=lambda c: c.id)
    phones = sorted((c for c in contacts if c.kind in PHONE_KINDS), key=lambda c: (not c.whatsapp_likely, c.id))
    mobiles = [c for c in phones if c.is_mobile or c.kind == ContactKind.WHATSAPP.value]
    landlines = [c for c in phones if c not in mobiles]
    phone = landlines[0].value if landlines else (mobiles[0].value if mobiles else "")
    mobile = mobiles[0].value if mobiles and mobiles[0].value != phone else ""
    city = business.geography
    province = city.parent if city is not None else None
    return Facts(
        business=business,
        phone=phone,
        mobile=mobile,
        all_phones=list(dict.fromkeys(c.value for c in phones)),
        emails=list(dict.fromkeys(c.value for c in contacts if c.kind == ContactKind.EMAIL.value)),
        city=city.name if city else "",
        province=province.name if province else "",
        segment=segment[1] if segment else "",
        score=chosen.score if chosen else "",
        sources=", ".join(source_label(key) for key in lookups.sources.get(business.id, [])),
        outcome=outcomes.get(business.id),
    )


def write_crm_csv(
    db: Session,
    filters: BusinessFilters,
    layout: CrmLayout,
    sort: BusinessSort | None = None,
    direction: SortDirection | None = None,
) -> tuple[IO[bytes], int]:
    headers, build = LAYOUTS[layout]
    buffer = tempfile.SpooledTemporaryFile(max_size=SPOOL_MAX_MEGABYTES * BYTES_PER_MEGABYTE)
    text = io.TextIOWrapper(buffer, encoding="utf-8", newline="")
    text.write(BOM)
    writer = csv.writer(text)
    writer.writerow(headers)
    count = 0
    for businesses, lookups in businesses_service.iter_business_batches(db, filters, sort, direction):
        ids = [business.id for business in businesses]
        outcomes = {row.business_id: row for row in db.query(LeadOutcome).filter(LeadOutcome.business_id.in_(ids)).all()}
        for business in businesses:
            writer.writerow([csv_safe(cell) for cell in build(_facts(business, lookups, outcomes, filters.profile_id))])
            count += 1
    text.flush()
    text.detach()
    buffer.seek(0)
    return buffer, count
