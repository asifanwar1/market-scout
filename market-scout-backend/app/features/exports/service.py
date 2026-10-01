import csv
import hashlib
import io
import json
import re
import tempfile
from collections.abc import Iterator, Sequence
from datetime import datetime
from typing import IO

from sqlalchemy.orm import Session

from app.core.constants import BYTES_PER_MEGABYTE
from app.core.scouting.sources.registry import source_label
from app.core.sheets.client import Cell
from app.features.businesses import service as businesses_service
from app.features.businesses.models import Business, ContactKind
from app.features.businesses.schemas import BusinessSort, SortDirection
from app.features.businesses.service import BusinessFilters
from app.features.profiles.models import Profile

WHATSAPP_CHAT_URL = "https://wa.me/"
MAPS_URL = "https://www.google.com/maps?q="


SPOOL_MAX_MEGABYTES = 8
CHUNK_BYTES = 64 * 1024


LEAD_HEADERS: list[str] = [
    "Lead ID", "Name", "Industry", "Segment", "Score", "Status", "Assigned to", "Notes",
    "Phone numbers", "WhatsApp chat", "Email", "Website", "Facebook", "Instagram",
    "Address", "City", "Province", "Rating", "Reviews", "Map", "Found by", "First found", "Last seen",
]

_PHONE_KINDS = (ContactKind.PHONE.value, ContactKind.WHATSAPP.value)
_NON_DIGITS = re.compile(r"\D")
_BOM = "﻿"


def _date(value: datetime | None) -> str:
    return value.strftime("%Y-%m-%d") if value else ""


def _lead_row(business: Business, lookups, profile_names: dict[int, str], profile_id: int | None) -> list[Cell]:
    classifications = [c for c in business.classifications if profile_id is None or c.profile_id == profile_id]
    chosen = max(classifications, key=lambda c: c.score, default=None)
    segment = lookups.segments.get(chosen.segment_id) if chosen and chosen.segment_id else None

    contacts = sorted(business.contact_points, key=lambda c: c.id)
    phones = sorted((c for c in contacts if c.kind in _PHONE_KINDS), key=lambda c: (not c.whatsapp_likely, c.id))
    phone_numbers = list(dict.fromkeys(c.value for c in phones))
    chat = next((c.value for c in phones if c.whatsapp_likely or c.kind == ContactKind.WHATSAPP.value), None)
    chat_link = f"{WHATSAPP_CHAT_URL}{_NON_DIGITS.sub('', chat)}" if chat else ""

    def first(kind: ContactKind) -> str:
        return next((c.value for c in contacts if c.kind == kind.value), "")

    emails = list(dict.fromkeys(c.value for c in contacts if c.kind == ContactKind.EMAIL.value))
    city = business.geography
    province = city.parent if city is not None else None
    has_position = business.latitude is not None and business.longitude is not None
    assigned = lookups.users.get(business.assigned_to_id, "") if business.assigned_to_id is not None else ""

    return [
        business.id,
        business.name,
        profile_names.get(chosen.profile_id, "") if chosen else "",
        segment[1] if segment else "",
        chosen.score if chosen else "",
        business.lead_status.replace("_", " ").capitalize(),
        assigned,
        business.notes or "",
        "; ".join(phone_numbers),
        chat_link,
        "; ".join(emails),
        business.website or "",
        first(ContactKind.FACEBOOK),
        first(ContactKind.INSTAGRAM),
        business.address or "",
        city.name if city else "",
        province.name if province else "",
        business.rating if business.rating is not None else "",
        business.review_count if business.review_count is not None else "",
        f"{MAPS_URL}{business.latitude},{business.longitude}" if has_position else "",
        ", ".join(source_label(key) for key in lookups.sources.get(business.id, [])),
        _date(business.first_seen_at),
        _date(business.last_seen_at),
    ]


def iter_lead_rows(
    db: Session,
    filters: BusinessFilters,
    sort: BusinessSort | None = None,
    direction: SortDirection | None = None,
) -> Iterator[list[Cell]]:
    profile_names = dict(db.query(Profile.id, Profile.name).all())
    for businesses, lookups in businesses_service.iter_business_batches(db, filters, sort, direction):
        for business in businesses:
            yield _lead_row(business, lookups, profile_names, filters.profile_id)


_FORMULA_START = ("=", "@", "\t", "\r")
_PHONE_LIKE = re.compile(r"^[+-]?[\d\s()+\-;,]+$")


def csv_safe(value: Cell) -> Cell:
    if not isinstance(value, str) or not value:
        return value
    if value.startswith(_FORMULA_START):
        return "'" + value
    if value.startswith(("+", "-")) and not _PHONE_LIKE.match(value):
        return "'" + value
    return value


def write_leads_csv(
    db: Session,
    filters: BusinessFilters,
    sort: BusinessSort | None = None,
    direction: SortDirection | None = None,
) -> tuple[IO[bytes], int]:
    buffer = tempfile.SpooledTemporaryFile(max_size=SPOOL_MAX_MEGABYTES * BYTES_PER_MEGABYTE)
    text = io.TextIOWrapper(buffer, encoding="utf-8", newline="")
    text.write(_BOM)
    writer = csv.writer(text)
    writer.writerow(LEAD_HEADERS)
    count = 0
    for row in iter_lead_rows(db, filters, sort, direction):
        writer.writerow([csv_safe(cell) for cell in row])
        count += 1
    text.flush()
    text.detach()
    buffer.seek(0)
    return buffer, count


def iter_file(file: IO[bytes], chunk_size: int = CHUNK_BYTES) -> Iterator[bytes]:
    try:
        while chunk := file.read(chunk_size):
            yield chunk
    finally:
        file.close()


def rows_fingerprint(header: Sequence[str], rows: Sequence[Sequence[Cell]]) -> str:
    payload = json.dumps([list(header), *map(list, rows)], ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
