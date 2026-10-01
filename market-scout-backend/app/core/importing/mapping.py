import hashlib
import re
from dataclasses import dataclass, field

from app.core.scouting.normalize import extract_emails, extract_phones_from_many, normalize_name, normalize_website
from app.core.scouting.types import RawBusiness

EXTERNAL_ID_LENGTH = 20


SINGLE_FIELDS = ("name", "website", "address", "city", "latitude", "longitude", "category")
LIST_FIELDS = ("phones", "emails")
ALL_FIELDS = SINGLE_FIELDS + LIST_FIELDS

_HINTS: dict[str, tuple[str, ...]] = {
    "name": (
        "company name", "business name", "firm name", "name of company", "shop name",
        "organisation", "organization", "company", "business", "firm", "name",
    ),
    "phones": ("phone", "mobile", "cell", "tel", "contact no", "contact number", "whatsapp", "landline", "contact"),
    "emails": ("email", "e-mail", "mail"),
    "website": ("website", "web site", "web", "url", "site", "link"),
    "address": ("address", "location", "street"),
    "city": ("city", "town", "district", "area"),
    "latitude": ("latitude", "lat"),
    "longitude": ("longitude", "longtitude", "lng", "lon", "long"),
    "category": ("category", "type", "business type", "segment", "activity", "technology", "trade"),
}

_EMPTY_WORDS = {"", "-", "--", "n/a", "na", "nil", "none", "null", "not available", "nan", "."}
_LAT_RANGE = (23.0, 37.5)
_LON_RANGE = (60.0, 78.0)


@dataclass
class Mapping:
    name: str
    phones: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    website: str | None = None
    address: str | None = None
    city: str | None = None
    latitude: str | None = None
    longitude: str | None = None
    category: str | None = None

    def referenced_headers(self) -> list[str]:
        headers = [self.name, *self.phones, *self.emails]
        headers += [h for h in (self.website, self.address, self.city, self.latitude, self.longitude, self.category) if h]
        return headers


def suggest_mapping(headers: list[str]) -> dict:
    taken: set[str] = set()
    suggestion: dict = {"name": None, "phones": [], "emails": [], "website": None, "address": None, "city": None,
                        "latitude": None, "longitude": None, "category": None}

    def candidates(hints: tuple[str, ...]) -> list[str]:
        ordered: list[str] = []
        for hint in hints:
            for header in headers:
                lowered = header.lower()
                if header not in ordered and (lowered == hint or _word(hint).search(lowered)):
                    ordered.append(header)
        return ordered

    for field_name in ("name", "emails", "latitude", "longitude", "website", "phones", "city", "address", "category"):
        matches = [h for h in candidates(_HINTS[field_name]) if h not in taken]
        if not matches:
            continue
        if field_name in LIST_FIELDS:
            chosen = [h for h in matches if _is_exact_family(h, _HINTS[field_name])] or matches[:1]
            suggestion[field_name] = chosen
            taken.update(chosen)
        else:
            suggestion[field_name] = matches[0]
            taken.add(matches[0])
    return suggestion


def _word(hint: str) -> "re.Pattern[str]":
    return re.compile(rf"\b{re.escape(hint)}s?\b")


def _is_exact_family(header: str, hints: tuple[str, ...]) -> bool:
    lowered = header.lower()
    return any(_word(hint).search(lowered) for hint in hints)


@dataclass
class ParsedRow:
    row_number: int
    raw: RawBusiness | None
    city_text: str | None = None
    skipped: str | None = None


SKIP_NO_NAME = "no_name"
SKIP_NO_CONTACT = "no_contact"


def clean_cell(value: str | None) -> str:
    text = " ".join((value or "").split())
    return "" if text.lower() in _EMPTY_WORDS else text


def stable_external_id(name: str, first_phone: str | None, domain: str | None, place: str = "") -> str:
    where = "" if (first_phone or domain) else normalize_name(place)
    key = f"{normalize_name(name)}|{first_phone or ''}|{domain or ''}" + (f"|{where}" if where else "")
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:EXTERNAL_ID_LENGTH]  # noqa: S324 (an identifier, not a secret)


def parse_row(
    row_number: int,
    values: dict[str, str],
    mapping: Mapping,
    source_key: str,
    require_contact: bool,
) -> ParsedRow:
    name = clean_cell(values.get(mapping.name))
    if not name:
        return ParsedRow(row_number, None, skipped=SKIP_NO_NAME)

    phones = extract_phones_from_many(_phone_texts([clean_cell(values.get(header)) for header in mapping.phones]))
    email_text = " ".join(clean_cell(values.get(header)) for header in mapping.emails)
    emails = extract_emails(email_text)
    site = normalize_website(clean_cell(values.get(mapping.website)) if mapping.website else None)

    if require_contact and not (phones or emails or site.url):
        return ParsedRow(row_number, None, skipped=SKIP_NO_CONTACT)

    latitude = longitude = None
    if mapping.latitude and mapping.longitude:
        latitude, longitude = _coordinates(values.get(mapping.latitude), values.get(mapping.longitude))

    category = clean_cell(values.get(mapping.category)) if mapping.category else ""
    city = clean_cell(values.get(mapping.city)) if mapping.city else ""
    address = clean_cell(values.get(mapping.address)) if mapping.address else ""
    raw = RawBusiness(
        source_key=source_key,
        external_id=stable_external_id(name, phones[0].e164 if phones else None, site.domain, f"{city} {address or ''}"),
        name=name,
        address=address or None,
        latitude=latitude,
        longitude=longitude,
        phones=[phone.e164 for phone in phones],
        emails=emails,
        website=site.url,
        categories=[category] if category else [],
        raw={header: value for header, value in values.items() if clean_cell(value)},
    )
    return ParsedRow(row_number, raw, city_text=city or None)


_DIGITS_ONLY = re.compile(r"[\d\s\-()]+")


def _phone_texts(cells: list[str]) -> list[str]:
    texts = []
    for cell in cells:
        if not cell:
            continue
        if _DIGITS_ONLY.fullmatch(cell) and not cell.startswith("0") and not extract_phones_from_many([cell]):
            texts.append("0" + cell)
        else:
            texts.append(cell)
    return texts


def _coordinates(lat_text: str | None, lon_text: str | None) -> tuple[float | None, float | None]:
    try:
        lat, lon = float(clean_cell(lat_text).replace(",", ".")), float(clean_cell(lon_text).replace(",", "."))
    except ValueError:
        return None, None
    if _LAT_RANGE[0] <= lat <= _LAT_RANGE[1] and _LON_RANGE[0] <= lon <= _LON_RANGE[1]:
        return lat, lon
    return None, None
