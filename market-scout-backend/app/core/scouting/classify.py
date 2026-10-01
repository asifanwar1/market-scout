import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from app.core.constants import SCORE_MAX

_MAX_NAME_LENGTH = 200
_MIN_REVIEWS_FOR_BONUS = 3


@dataclass(frozen=True)
class SegmentRule:
    slug: str
    name_patterns: tuple[str, ...] = ()


@dataclass(frozen=True)
class LeadSignals:
    has_phone: bool
    has_whatsapp_likely: bool
    has_website: bool
    has_email: bool
    review_count: int | None = None


@dataclass(frozen=True)
class Classification:
    segment_slug: str | None
    name_matched: bool


def classify(name: str, hint_slug: str | None, segments: Sequence[SegmentRule]) -> Classification:
    matched = [segment.slug for segment in segments if _name_matches(name, segment)]
    if hint_slug in matched:
        return Classification(hint_slug, True)
    if matched:
        return Classification(matched[0], True)
    return Classification(hint_slug, False)


def _name_matches(name: str, segment: SegmentRule) -> bool:
    text = name[:_MAX_NAME_LENGTH]
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in segment.name_patterns)


def score_lead(signals: LeadSignals, name_matched: bool, weights: Mapping[str, int]) -> int:
    total = 0
    if signals.has_phone:
        total += weights.get("has_phone", 0)
    if signals.has_whatsapp_likely:
        total += weights.get("has_whatsapp_likely", 0)
    if signals.has_website:
        total += weights.get("has_website", 0)
    if signals.has_email:
        total += weights.get("has_email", 0)
    if (signals.review_count or 0) >= _MIN_REVIEWS_FOR_BONUS:
        total += weights.get("has_reviews", 0)
    if name_matched:
        total += weights.get("name_matches_segment", 0)
    return min(SCORE_MAX, total)
