from app.features.profiles.models import TermLanguage
from app.features.profiles.schemas import ProfileCreate

PROFILE_NAME = "Solar, Inverters & Batteries"

_SOLAR_NAME = "name~solar|inverter|battery|ups"

_SEGMENTS = [
    {
        "name": "Dealer",
        "slug": "dealer",
        "description": "Sells solar panels, inverters and batteries under authorised brands.",
        "match_rules": {"name_patterns": [r"\bdealer", r"authori[sz]ed"]},
        "sort_order": 1,
    },
    {
        "name": "Importer",
        "slug": "importer",
        "description": "Imports solar equipment in bulk.",
        "match_rules": {"name_patterns": [r"\bimport", r"international", r"\bint'?l\b"]},
        "sort_order": 2,
    },
    {
        "name": "Wholesaler",
        "slug": "wholesaler",
        "description": "Sells to other shops and installers in volume.",
        "match_rules": {"name_patterns": [r"wholesale", r"distribut", r"\btraders?\b"]},
        "sort_order": 3,
    },
    {
        "name": "Retailer",
        "slug": "retailer",
        "description": "Shop selling to end customers.",
        "match_rules": {"name_patterns": [r"\bstore\b", r"\bshop\b", r"\bmart\b", r"\bcent(?:er|re)\b"]},
        "sort_order": 4,
    },
    {
        "name": "Installer",
        "slug": "installer",
        "description": "Designs and installs solar systems.",
        "match_rules": {"name_patterns": [r"install", r"solutions", r"\benergy\b", r"\bsystems?\b"]},
        "sort_order": 5,
    },
    {
        "name": "Contractor",
        "slug": "contractor",
        "description": "Electrical or EPC contractor taking on larger projects.",
        "match_rules": {"name_patterns": [r"contractor", r"\bepc\b", r"engineer", r"construction"]},
        "sort_order": 6,
    },
]

_SEARCH_TERMS = [
    {
        "text": "solar panel dealer",
        "segment_slug": "dealer",
        "osm_filter": {"clauses": [
            ["shop=electrical", _SOLAR_NAME],
            ["shop=hardware", _SOLAR_NAME],
            ["name~solar"],
        ]},
    },
    {
        "text": "inverter and battery dealer",
        "segment_slug": "dealer",
        "osm_filter": {"clauses": [["name~inverter|battery|ups"]]},
    },
    {"text": "solar panel ka dealer", "segment_slug": "dealer", "language": TermLanguage.UR_ROMAN},
    {
        "text": "solar panel importer",
        "segment_slug": "importer",
        "osm_filter": {"clauses": [["name~solar|inverter|energy", "name~import|trading|international"]]},
    },
    {"text": "solar equipment importer", "segment_slug": "importer"},
    {
        "text": "solar wholesaler",
        "segment_slug": "wholesaler",
        "osm_filter": {"clauses": [["shop=wholesale", "name~solar|electric|battery"], ["shop=trade", "name~solar|electric"]]},
    },
    {"text": "solar panel wholesale market", "segment_slug": "wholesaler"},
    {"text": "solar panel thok dealer", "segment_slug": "wholesaler", "language": TermLanguage.UR_ROMAN},
    {
        "text": "solar shop",
        "segment_slug": "retailer",
        "osm_filter": {"clauses": [["shop=electronics", _SOLAR_NAME], ["shop=electrical"]]},
    },
    {
        "text": "battery and UPS shop",
        "segment_slug": "retailer",
        "osm_filter": {"clauses": [["name~battery|ups|inverter"]]},
    },
    {"text": "solar ki dukan", "segment_slug": "retailer", "language": TermLanguage.UR_ROMAN},
    {
        "text": "solar installer",
        "segment_slug": "installer",
        "osm_filter": {"clauses": [["craft=electrician", "name~solar"], ["office=company", "name~solar"]]},
    },
    {"text": "solar system installation company", "segment_slug": "installer"},
    {"text": "solar system lagwana", "segment_slug": "installer", "language": TermLanguage.UR_ROMAN},
    {
        "text": "electrical contractor",
        "segment_slug": "contractor",
        "osm_filter": {"clauses": [["craft=electrician"], ["office=company", "name~electric|contractor|engineering"]]},
    },
    {"text": "solar EPC contractor", "segment_slug": "contractor"},
]


def build_solar_profile() -> ProfileCreate:
    return ProfileCreate(
        name=PROFILE_NAME,
        description=(
            "Dealers, importers, wholesalers, retailers, installers and contractors "
            "for solar panels, inverters and batteries."
        ),
        segments=_SEGMENTS,
        search_terms=_SEARCH_TERMS,
    )
