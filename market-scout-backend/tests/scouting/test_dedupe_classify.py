from app.core.scouting.classify import (
    LeadSignals,
    SegmentRule,
    classify,
    score_lead,
)
from app.core.scouting.dedupe import BusinessKeys, haversine_m, is_same_business
from app.core.scouting.normalize import normalize_name

LAHORE = (31.5204, 74.3587)


def keys(name, phones=(), domain=None, coords=None):
    lat, lng = coords or (None, None)
    return BusinessKeys(normalize_name(name), frozenset(phones), domain, lat, lng)


def test_haversine_known_distance():
    assert 1_000_000 < haversine_m(*LAHORE, 24.8607, 67.0011) < 1_060_000
    assert haversine_m(*LAHORE, *LAHORE) == 0


def test_same_website_domain_matches_even_if_names_differ():
    decision = is_same_business(keys("Al Noor Solar", domain="alnoor.pk"), keys("A.N. Energy", domain="alnoor.pk"))
    assert decision.is_match and decision.reason == "website"


def test_shared_phone_matches_when_names_agree():
    a = keys("Al-Noor Solar Traders", phones={"+923001234567"})
    b = keys("Alnoor Solar", phones={"+923001234567", "+924235781769"})
    assert is_same_business(a, b).reason == "phone"


def test_shared_phone_does_not_merge_unrelated_names():
    a = keys("Zahid Battery House", phones={"+924235781769"})
    b = keys("Karachi Mobile Center", phones={"+924235781769"})
    assert not is_same_business(a, b).is_match


def test_nearby_similar_names_match_by_location():
    a = keys("Madina Electric & Electronics", coords=(31.5204, 74.3587))
    b = keys("Madina Electric and Electronics Store", coords=(31.5206, 74.3588))
    assert is_same_business(a, b).reason == "location"


def test_nearby_but_different_or_distant_same_name_do_not_match():
    base = keys("Madina Electric", coords=(31.5204, 74.3587))
    assert not is_same_business(base, keys("Bilal Traders", coords=(31.5205, 74.3587))).is_match
    assert not is_same_business(base, keys("Madina Electric", coords=(31.6204, 74.3587))).is_match


def test_missing_data_never_matches():
    assert not is_same_business(keys("Solar"), keys("Solar")).is_match
    assert not is_same_business(keys(""), keys("", phones={"+923001234567"})).is_match


SEGMENTS = [
    SegmentRule("dealer", (r"\bdealer",)),
    SegmentRule("wholesaler", (r"wholesale", r"\btraders?\b")),
    SegmentRule("retailer", (r"\bshop\b", r"\bstore\b")),
]


def test_name_matching_the_searched_segment_wins():
    result = classify("Noor Wholesale Traders", "wholesaler", SEGMENTS)
    assert (result.segment_slug, result.name_matched) == ("wholesaler", True)


def test_name_evidence_overrides_the_search_segment():
    result = classify("Noor Wholesale Traders", "retailer", SEGMENTS)
    assert (result.segment_slug, result.name_matched) == ("wholesaler", True)


def test_falls_back_to_search_segment_when_name_says_nothing():
    result = classify("Bright Future", "dealer", SEGMENTS)
    assert (result.segment_slug, result.name_matched) == ("dealer", False)
    assert classify("Bright Future", None, SEGMENTS).segment_slug is None


def test_classify_is_case_insensitive_and_bounds_long_names():
    assert classify("AUTHORISED DEALER", None, SEGMENTS).segment_slug == "dealer"
    assert classify("x" * 500 + " dealer", None, SEGMENTS).segment_slug is None


WEIGHTS = {
    "has_phone": 30, "has_whatsapp_likely": 20, "has_website": 10,
    "has_email": 10, "has_reviews": 10, "name_matches_segment": 20,
}


def test_score_sums_present_signals():
    everything = LeadSignals(True, True, True, True, review_count=10)
    assert score_lead(everything, True, WEIGHTS) == 100
    assert score_lead(LeadSignals(True, False, False, False), False, WEIGHTS) == 30
    assert score_lead(LeadSignals(False, False, False, False), False, WEIGHTS) == 0


def test_score_review_bonus_needs_a_few_reviews_and_total_is_capped():
    assert score_lead(LeadSignals(False, False, False, False, review_count=2), False, WEIGHTS) == 0
    assert score_lead(LeadSignals(False, False, False, False, review_count=3), False, WEIGHTS) == 10
    heavy = {**WEIGHTS, "has_phone": 100}
    assert score_lead(LeadSignals(True, True, True, True, 9), True, heavy) == 100
