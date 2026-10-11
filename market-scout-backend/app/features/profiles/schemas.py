import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.constants import CONDITION_OPERATOR_PATTERN, DESCRIPTION_MAX_LENGTH, NAME_MAX_LENGTH, NAME_MIN_LENGTH, SCORE_MAX, SCORE_MIN
from app.core.utils import slugify
from app.features.profiles.models import TermLanguage

CLAUSES_MAX = 10
CONDITIONS_PER_CLAUSE_MAX = 5
NAME_PATTERNS_MAX = 50
PATTERN_MAX_LENGTH = 100
TERM_TEXT_MAX_LENGTH = 150
SEGMENTS_MAX = 30
SEARCH_TERMS_MAX = 300
DEFAULT_WEIGHT_PHONE = 30
DEFAULT_WEIGHT_WHATSAPP = 20
DEFAULT_WEIGHT_WEBSITE = 10
DEFAULT_WEIGHT_EMAIL = 10
DEFAULT_WEIGHT_REVIEWS = 10
DEFAULT_WEIGHT_NAME_MATCH = 20


_SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
_OSM_CONDITION = re.compile(r"^([A-Za-z0-9_:]+)(=|~)(.+)$")
_OSM_SAFE_VALUE = re.compile(r"^[\w\s|.\-&()+*?]+$")


def _validate_osm_condition(condition: str) -> str:
    match = _OSM_CONDITION.match(condition.strip())
    if not match:
        raise ValueError(f"'{condition}' must look like key=value or key~regex")
    _, operator, value = match.groups()
    if not _OSM_SAFE_VALUE.match(value):
        raise ValueError(f"'{condition}' contains characters that are not allowed")
    if operator == CONDITION_OPERATOR_PATTERN:
        _validate_regex(value)
    return condition.strip()


def _validate_regex(pattern: str) -> str:
    try:
        re.compile(pattern)
    except re.error as exc:
        raise ValueError(f"'{pattern}' is not a valid regular expression: {exc}") from exc
    return pattern


class OsmFilter(BaseModel):
    clauses: list[list[str]] = Field(min_length=1, max_length=CLAUSES_MAX)

    @field_validator("clauses")
    @classmethod
    def validate_clauses(cls, clauses: list[list[str]]) -> list[list[str]]:
        for clause in clauses:
            if not 1 <= len(clause) <= CONDITIONS_PER_CLAUSE_MAX:
                raise ValueError(f"each clause needs between 1 and {CONDITIONS_PER_CLAUSE_MAX} conditions")
        return [[_validate_osm_condition(condition) for condition in clause] for clause in clauses]


class MatchRules(BaseModel):
    name_patterns: list[str] = Field(default_factory=list, max_length=NAME_PATTERNS_MAX)

    @field_validator("name_patterns")
    @classmethod
    def validate_name_patterns(cls, patterns: list[str]) -> list[str]:
        cleaned: list[str] = []
        for pattern in patterns:
            pattern = pattern.strip()
            if not pattern or len(pattern) > PATTERN_MAX_LENGTH:
                raise ValueError(f"name patterns must be 1-{PATTERN_MAX_LENGTH} characters")
            cleaned.append(_validate_regex(pattern))
        return cleaned


IDEAL_CUSTOMER_MAX_LENGTH = 2000


class ScoringConfig(BaseModel):
    has_phone: int = Field(default=DEFAULT_WEIGHT_PHONE, ge=SCORE_MIN, le=SCORE_MAX)
    has_whatsapp_likely: int = Field(default=DEFAULT_WEIGHT_WHATSAPP, ge=SCORE_MIN, le=SCORE_MAX)
    has_website: int = Field(default=DEFAULT_WEIGHT_WEBSITE, ge=SCORE_MIN, le=SCORE_MAX)
    has_email: int = Field(default=DEFAULT_WEIGHT_EMAIL, ge=SCORE_MIN, le=SCORE_MAX)
    has_reviews: int = Field(default=DEFAULT_WEIGHT_REVIEWS, ge=SCORE_MIN, le=SCORE_MAX)
    name_matches_segment: int = Field(default=DEFAULT_WEIGHT_NAME_MATCH, ge=SCORE_MIN, le=SCORE_MAX)


class SegmentCreate(BaseModel):
    name: str = Field(min_length=NAME_MIN_LENGTH, max_length=NAME_MAX_LENGTH)
    slug: Optional[str] = Field(default=None, pattern=_SLUG_PATTERN, max_length=NAME_MAX_LENGTH)
    description: Optional[str] = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)
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


class SearchTermCreate(BaseModel):
    text: str = Field(min_length=NAME_MIN_LENGTH, max_length=TERM_TEXT_MAX_LENGTH)
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
    name: str = Field(min_length=NAME_MIN_LENGTH, max_length=NAME_MAX_LENGTH)
    description: Optional[str] = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)
    ideal_customer: Optional[str] = Field(default=None, max_length=IDEAL_CUSTOMER_MAX_LENGTH)
    is_active: bool = True
    scoring_config: ScoringConfig = Field(default_factory=ScoringConfig)


class ProfileCreate(ProfileBase):
    segments: list[SegmentCreate] = Field(default_factory=list, max_length=SEGMENTS_MAX)
    search_terms: list[SearchTermCreate] = Field(default_factory=list, max_length=SEARCH_TERMS_MAX)

    @model_validator(mode="after")
    def validate_nested(self) -> "ProfileCreate":
        _check_segment_slugs_unique(self.segments)
        _check_search_terms(self.search_terms, self.segments)
        return self


class ProfileUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=NAME_MIN_LENGTH, max_length=NAME_MAX_LENGTH)
    description: Optional[str] = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)
    ideal_customer: Optional[str] = Field(default=None, max_length=IDEAL_CUSTOMER_MAX_LENGTH)
    is_active: Optional[bool] = None
    scoring_config: Optional[ScoringConfig] = None
    segments: Optional[list[SegmentUpsert]] = Field(default=None, max_length=SEGMENTS_MAX)
    search_terms: Optional[list[SearchTermUpsert]] = Field(default=None, max_length=SEARCH_TERMS_MAX)

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
