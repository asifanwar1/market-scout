import re
import sqlite3
from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache

from app.core.constants import CONDITION_OPERATOR_EQUALS, CONDITION_OPERATOR_PATTERN, PLATFORM_FACEBOOK
from app.core.scouting import place_store
from app.core.scouting.sources.base import SourceError
from app.core.scouting.types import RawBusiness, SearchQuery, SearchResult

NAME_KEY = "name"
PATTERN_CACHE_SIZE = 256
RESULT_LIMIT = 2000

_CONDITION = re.compile(r"^([A-Za-z0-9_:]+)(=|~)(.+)$")

TagCategories = Mapping[str, frozenset[str] | None]


@dataclass(frozen=True)
class Clause:
    categories: frozenset[str] | None
    name_patterns: tuple[str, ...]


def _translate_clause(conditions: list[str], tag_categories: TagCategories) -> Clause | None:
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
        elif operator == CONDITION_OPERATOR_EQUALS and f"{key}={value}" in tag_categories:
            wanted = tag_categories[f"{key}={value}"]
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


def translate_filter(osm_filter: dict | None, tag_categories: TagCategories) -> list[Clause]:
    if not osm_filter:
        return []
    clauses = (_translate_clause(list(clause), tag_categories) for clause in osm_filter.get("clauses", []))
    return [clause for clause in clauses if clause is not None]


@lru_cache(maxsize=PATTERN_CACHE_SIZE)
def _compiled(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE)


def _regexp(pattern: str, value: str | None) -> int:
    return 1 if value and _compiled(pattern).search(value) else 0


def build_where(clauses: list[Clause], exact_categories: bool = True) -> tuple[str, list]:
    groups: list[str] = []
    params: list = []
    for clause in clauses:
        parts: list[str] = []
        if clause.categories is not None:
            ordered = sorted(clause.categories)
            column = "categories" if exact_categories else "lower(categories)"
            parts.append("(" + " OR ".join(f"instr({column}, ?) > 0" for _ in ordered) + ")")
            params.extend(f"|{category}|" if exact_categories else category.lower() for category in ordered)
        for pattern in clause.name_patterns:
            parts.append("regexp(?, name)")
            params.append(pattern)
        groups.append("(" + " AND ".join(parts) + ")")
    return " OR ".join(groups), params


def place_address(place: place_store.Place) -> str | None:
    address = place.address
    if place.city and (not address or place.city.lower() not in address.lower()):
        address = ", ".join(part for part in (address, place.city) if part)
    return address or None


def place_website(place: place_store.Place) -> str | None:
    own_site = place.websites[0] if place.websites else None
    facebook_page = next((social for social in place.socials if PLATFORM_FACEBOOK in social), None)
    return own_site or facebook_page


class LocalPlaceSource(ABC):
    key: str
    label: str
    tag_categories: TagCategories
    exact_categories: bool = True

    def __init__(self, path: str, min_confidence: float = 0.0):
        self._path = path
        self._min_confidence = min_confidence

    @abstractmethod
    def to_business(self, place: place_store.Place, release: str) -> RawBusiness:
        pass

    def translate_filter(self, osm_filter: dict | None) -> list[Clause]:
        return translate_filter(osm_filter, self.tag_categories)

    def search(self, query: SearchQuery, max_requests: int | None = None) -> SearchResult:
        clauses = self.translate_filter(query.osm_filter)
        if not clauses:
            return SearchResult(businesses=[], requests_made=0)

        where, params = build_where(clauses, self.exact_categories)
        south, west, north, east = query.area.rectangle
        sql = (
            f"SELECT {place_store.PLACE_COLUMNS} FROM places "
            "WHERE latitude BETWEEN ? AND ? AND longitude BETWEEN ? AND ? AND confidence >= ? "
            f"AND (status IS NULL OR status != ?) AND ({where}) ORDER BY confidence DESC, id LIMIT ?"
        )
        arguments = [south, north, west, east, self._min_confidence, place_store.STATUS_PERMANENTLY_CLOSED, *params, RESULT_LIMIT]

        try:
            connection = place_store.connect(self._path)
        except place_store.StoreError as exc:
            raise SourceError(str(exc)) from exc
        try:
            connection.create_function("regexp", 2, _regexp, deterministic=True)
            release = connection.execute("SELECT value FROM meta WHERE key = 'release'").fetchone()[0]
            rows = connection.execute(sql, arguments).fetchall()
        except sqlite3.DatabaseError as exc:
            raise SourceError(f"The {self.label} data file can't be searched ({exc}). Download it again.") from exc
        finally:
            connection.close()

        businesses = [self.to_business(place, release) for place in place_store.rows_to_places(rows)]
        return SearchResult(businesses=businesses, requests_made=0)

    def test_connection(self) -> tuple[bool, str]:
        try:
            info = place_store.read_info(self._path)
        except place_store.StoreError as exc:
            return False, str(exc)
        return True, f"{self.label} {info.release}: {info.places:,} places on this computer"
