import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator
from app.core.utils import slugify
from app.features.profiles.models import TermLanguage

_SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
_OSM_CONDITION = re.compile(r"^([A-Za-z0-9_:]+)(=|~)(.+)$")
# Values end up inside an Overpass QL query, so only plain characters are allowed:
# no quotes, backslashes, brackets or semicolons that could break out of the string.
_OSM_SAFE_VALUE = re.compile(r"^[\w\s|.\-&()+*?]+$")


def _validate_osm_condition(condition: str) -> str:
    match = _OSM_CONDITION.match(condition.strip())
    if not match:
        raise ValueError(f"'{condition}' must look like key=value or key~regex")
    _, operator, value = match.groups()
    if not _OSM_SAFE_VALUE.match(value):
        raise ValueError(f"'{condition}' contains characters that are not allowed")
    if operator == "~":
        _validate_regex(value)
    return condition.strip()


def _validate_regex(pattern: str) -> str:
    try:
        re.compile(pattern)
    except re.error as exc:
        raise ValueError(f"'{pattern}' is not a valid regular expression: {exc}")
    return pattern


class OsmFilter(BaseModel):
    """Alternative clauses (OR); each clause is a list of conditions that must all match (AND).

    A condition is ``key=value`` (exact) or ``key~regex`` (case-insensitive), e.g.
    ``[["shop=electrical", "name~solar|inverter"], ["name~solar"]]``.
    """

    clauses: list[list[str]] = Field(min_length=1, max_length=10)

    @field_validator("clauses")
    @classmethod
    def validate_clauses(cls, clauses: list[list[str]]) -> list[list[str]]:
        for clause in clauses:
            if not 1 <= len(clause) <= 5:
                raise ValueError("each clause needs between 1 and 5 conditions")
        return [[_validate_osm_condition(condition) for condition in clause] for clause in clauses]


class MatchRules(BaseModel):
    name_patterns: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("name_patterns")
    @classmethod
    def validate_name_patterns(cls, patterns: list[str]) -> list[str]:
        cleaned: list[str] = []
        for pattern in patterns:
            pattern = pattern.strip()
            if not pattern or len(pattern) > 100:
                raise ValueError("name patterns must be 1-100 characters")
            cleaned.append(_validate_regex(pattern))
        return cleaned


class ScoringConfig(BaseModel):
    """Points added to a lead's score (0-100 overall) when a signal is present."""

    has_phone: int = Field(default=30, ge=0, le=100)
    has_whatsapp_likely: int = Field(default=20, ge=0, le=100)
    has_website: int = Field(default=10, ge=0, le=100)
    has_email: int = Field(default=10, ge=0, le=100)
    has_reviews: int = Field(default=10, ge=0, le=100)
    name_matches_segment: int = Field(default=20, ge=0, le=100)


# ---- segments ---------------------------------------------------------------

class SegmentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    slug: Optional[str] = Field(default=None, pattern=_SLUG_PATTERN, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    match_rules: MatchRules = Field(default_factory=MatchRules)
    sort_order: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def default_slug(self) -> "SegmentCreate":
        if self.slug is None:
            self.slug = slugify(self.name, fallback="segment")
        return self


class SegmentUpsert(SegmentCreate):
    id: Optional[int] = None


class SegmentResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    match_rules: MatchRules
    sort_order: int

    model_config = {"from_attributes": True}


# ---- search terms -----------------------------------------------------------

class SearchTermCreate(BaseModel):
    text: str = Field(min_length=2, max_length=150)
    segment_slug: str = Field(pattern=_SLUG_PATTERN)
    osm_filter: Optional[OsmFilter] = None
    language: TermLanguage = TermLanguage.EN
    is_active: bool = True

    @field_validator("text")
    @classmethod
    def strip_text(cls, v: str) -> str:
        return v.strip()


class SearchTermUpsert(SearchTermCreate):
    id: Optional[int] = None


class SearchTermResponse(BaseModel):
    id: int
    text: str
    segment_id: int
    segment_slug: str
    osm_filter: Optional[OsmFilter] = None
    language: TermLanguage
    is_active: bool

    model_config = {"from_attributes": True}


# ---- profiles ---------------------------------------------------------------

def _check_segment_slugs_unique(segments: list[SegmentCreate]) -> None:
    slugs = [segment.slug for segment in segments]
    duplicates = sorted({slug for slug in slugs if slugs.count(slug) > 1})
    if duplicates:
        raise ValueError(f"Duplicate segment slugs: {', '.join(duplicates)}")


def _check_search_terms(search_terms: list[SearchTermCreate], segments: list[SegmentCreate] | None) -> None:
    seen: set[tuple[str, str, str]] = set()
    for term in search_terms:
        key = (term.segment_slug, term.text.lower(), term.language.value)
        if key in seen:
            raise ValueError(f"Duplicate search term '{term.text}' in segment '{term.segment_slug}'")
        seen.add(key)

    if segments is None:
        return
    known_slugs = {segment.slug for segment in segments}
    for term in search_terms:
        if term.segment_slug not in known_slugs:
            raise ValueError(f"Search term '{term.text}' refers to unknown segment '{term.segment_slug}'")


class ProfileBase(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    is_active: bool = True
    scoring_config: ScoringConfig = Field(default_factory=ScoringConfig)


class ProfileCreate(ProfileBase):
    segments: list[SegmentCreate] = Field(default_factory=list, max_length=30)
    search_terms: list[SearchTermCreate] = Field(default_factory=list, max_length=300)

    @model_validator(mode="after")
    def validate_nested(self) -> "ProfileCreate":
        _check_segment_slugs_unique(self.segments)
        _check_search_terms(self.search_terms, self.segments)
        return self


class ProfileUpdate(BaseModel):
    """PUT semantics for the nested lists: when ``segments`` / ``search_terms`` is sent it is
    the complete desired list -- items with an ``id`` are updated, items without one are
    created, and existing items that are missing are deleted. Omit a list to leave it alone."""

    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    is_active: Optional[bool] = None
    scoring_config: Optional[ScoringConfig] = None
    segments: Optional[list[SegmentUpsert]] = Field(default=None, max_length=30)
    search_terms: Optional[list[SearchTermUpsert]] = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def validate_nested(self) -> "ProfileUpdate":
        if self.segments is not None:
            _check_segment_slugs_unique(self.segments)
        if self.search_terms is not None:
            _check_search_terms(self.search_terms, self.segments)
        return self


class ProfileResponse(ProfileBase):
    id: int
    slug: str
    segments: list[SegmentResponse]
    search_terms: list[SearchTermResponse]
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ProfileListItem(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    is_active: bool
    segment_count: int
    term_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ProfileListResponse(BaseModel):
    data: list[ProfileListItem]
    count: int
