import re
import sqlite3
from dataclasses import dataclass
from functools import lru_cache

from app.core.constants import CONDITION_OPERATOR_EQUALS, CONDITION_OPERATOR_PATTERN, PLATFORM_FACEBOOK
from app.core.scouting import overture_store
from app.core.scouting.sources.base import SourceError
from app.core.scouting.types import RawBusiness, SearchQuery, SearchResult

NAME_KEY = "name"
PATTERN_CACHE_SIZE = 256


SOURCE_KEY = "overture"

RESULT_LIMIT = 2000

_CONDITION = re.compile(r"^([A-Za-z0-9_:]+)(=|~)(.+)$")
_PERMANENTLY_CLOSED = "permanently_closed"

_ELECTRICAL_AND_ENERGY = frozenset(
    {
        "electronics_store", "electronic_equipment_supplier", "lighting_store", "appliance_store",
        "solar_installation", "b2b_energy_and_utility_service", "energy_company", "electrician",
    }
)
_HARDWARE = frozenset({"hardware_store", "hardware_home_and_garden_store", "home_improvement_store", "building_supply_store"})
_WHOLESALE = frozenset(
    {
        "wholesaler", "computer_wholesaler", "fmcg_wholesaler", "supplier_or_distributor", "distribution_service",
        "importer", "import_export_service",
    }
)
_CONTRACTORS = frozenset(
    {
        "contractor", "building_or_construction_service", "engineering_service", "electrician", "solar_installation",
        "structural_engineer", "civil_engineer",
    }
)

TAG_CATEGORIES: dict[str, frozenset[str] | None] = {
    "shop=electrical": _ELECTRICAL_AND_ENERGY,
    "shop=electronics": frozenset(
        {"electronics_store", "electronic_equipment_supplier", "appliance_store", "audio_visual_equipment_store"}
    ),
    "shop=hardware": _HARDWARE,
    "shop=doityourself": _HARDWARE,
    "shop=trade": _WHOLESALE | _HARDWARE | frozenset({"electronic_equipment_supplier", "metal_supplier"}),
    "shop=wholesale": _WHOLESALE | frozenset({"electronic_equipment_supplier"}),
    "shop=lighting": frozenset({"lighting_store", "lighting_fixtures_and_equipment"}),
    "shop=appliance": frozenset({"appliance_store"}),
    "shop=computer": frozenset({"computer_hardware_company", "electronics_store", "computer_wholesaler"}),
    "craft=electrician": frozenset({"electrician"}),
    "craft=hvac": frozenset({"hvac_service", "hvac_supplier"}),
    "craft=builder": frozenset({"contractor", "building_or_construction_service"}),
    "office=company": None,
    "office=energy_supplier": frozenset({"energy_company", "electric_utility_provider", "b2b_energy_and_utility_service"}),
    "office=engineer": frozenset({"engineering_service", "structural_engineer", "civil_engineer"}),
    "office=construction_company": frozenset({"contractor", "building_or_construction_service"}),
    "office=contractor": _CONTRACTORS,
}


@dataclass(frozen=True)
class Clause:
    categories: frozenset[str] | None
    name_patterns: tuple[str, ...]


def _translate_clause(conditions: list[str]) -> Clause | None:
    categories: frozenset[str] | None = None
    constrained = False
    patterns: list[str] = []

    for condition in conditions:
        match = _CONDITION.match(condition.strip())
        if not match:
            return None
        key, operator, value = match.groups()

        if key == NAME_KEY:
            pattern = value if operator == CONDITION_OPERATOR_PATTERN else f"^{re.escape(value)}$"
            try:
                re.compile(pattern)
            except re.error:
                return None
            patterns.append(pattern)
        elif operator == CONDITION_OPERATOR_EQUALS and f"{key}={value}" in TAG_CATEGORIES:
            wanted = TAG_CATEGORIES[f"{key}={value}"]
            if wanted is not None:
                categories = wanted if categories is None else categories & wanted
                constrained = True
        else:
            return None

    if constrained and not categories:
        return None
    if not constrained and not patterns:
        return None
    return Clause(categories=categories if constrained else None, name_patterns=tuple(patterns))


def translate_filter(osm_filter: dict | None) -> list[Clause]:
    if not osm_filter:
        return []
    clauses = (_translate_clause(list(clause)) for clause in osm_filter.get("clauses", []))
    return [clause for clause in clauses if clause is not None]


def supports(osm_filter: dict | None) -> bool:
    return bool(translate_filter(osm_filter))


@lru_cache(maxsize=PATTERN_CACHE_SIZE)
def _compiled(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE)


def _regexp(pattern: str, value: str | None) -> int:
    return 1 if value and _compiled(pattern).search(value) else 0


def build_where(clauses: list[Clause]) -> tuple[str, list]:
    groups: list[str] = []
    params: list = []
    for clause in clauses:
        parts: list[str] = []
        if clause.categories is not None:
            ordered = sorted(clause.categories)
            parts.append("(" + " OR ".join("instr(categories, ?) > 0" for _ in ordered) + ")")
            params.extend(f"|{category}|" for category in ordered)
        for pattern in clause.name_patterns:
            parts.append("regexp(?, name)")
            params.append(pattern)
        groups.append("(" + " AND ".join(parts) + ")")
    return " OR ".join(groups), params


def place_to_business(place: overture_store.Place, release: str) -> RawBusiness:
    address = place.address
    if place.city and (not address or place.city.lower() not in address.lower()):
        address = ", ".join(part for part in (address, place.city) if part)
    own_site = place.websites[0] if place.websites else None
    facebook_page = next((social for social in place.socials if PLATFORM_FACEBOOK in social), None)
    website = own_site or facebook_page
    return RawBusiness(
        source_key=SOURCE_KEY,
        external_id=place.id,
        name=place.name,
        address=address or None,
        latitude=place.latitude,
        longitude=place.longitude,
        phones=place.phones,
        emails=place.emails,
        website=website,
        categories=place.categories,
        raw={"confidence": place.confidence, "dataset": place.dataset, "release": release, "socials": place.socials},
    )


class OvertureSource:
    key = SOURCE_KEY

    def __init__(self, path: str, min_confidence: float = 0.0):
        self._path = path
        self._min_confidence = min_confidence

    def search(self, query: SearchQuery, max_requests: int | None = None) -> SearchResult:
        clauses = translate_filter(query.osm_filter)
        if not clauses:
            return SearchResult(businesses=[], requests_made=0)

        where, params = build_where(clauses)
        south, west, north, east = query.area.rectangle
        sql = (
            f"SELECT {overture_store.PLACE_COLUMNS} FROM places "
            "WHERE latitude BETWEEN ? AND ? AND longitude BETWEEN ? AND ? AND confidence >= ? "
            f"AND (status IS NULL OR status != ?) AND ({where}) ORDER BY confidence DESC, id LIMIT ?"
        )
        arguments = [south, north, west, east, self._min_confidence, _PERMANENTLY_CLOSED, *params, RESULT_LIMIT]

        try:
            connection = overture_store.connect(self._path)
        except overture_store.StoreError as exc:
            raise SourceError(str(exc)) from exc
        try:
            connection.create_function("regexp", 2, _regexp, deterministic=True)
            release = connection.execute("SELECT value FROM meta WHERE key = 'release'").fetchone()[0]
            rows = connection.execute(sql, arguments).fetchall()
        except sqlite3.DatabaseError as exc:
            raise SourceError(f"The Overture data file can't be searched ({exc}). Download it again.") from exc
        finally:
            connection.close()

        businesses = [place_to_business(place, release) for place in overture_store.rows_to_places(rows)]
        return SearchResult(businesses=businesses, requests_made=0)

    def test_connection(self) -> tuple[bool, str]:
        try:
            info = overture_store.read_info(self._path)
        except overture_store.StoreError as exc:
            return False, str(exc)
        return True, f"Overture {info.release}: {info.places:,} places on this computer"
