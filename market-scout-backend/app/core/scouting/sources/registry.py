"""The catalogue of data sources the app knows about, and how to construct one.

Adding a source = a new class implementing ``Source`` plus one entry here.
"""
from dataclasses import dataclass

from app.core.scouting.sources import google_places, osm
from app.core.scouting.sources.base import Source

KIND_DISCOVERY = "discovery"
KIND_ENRICHMENT = "enrichment"

ENRICHMENT_KEY = "website_enrichment"


@dataclass(frozen=True)
class SourceInfo:
    key: str
    name: str
    description: str
    kind: str
    requires_api_key: bool
    default_enabled: bool
    # Billable per request; runs count these against their request cap.
    is_paid: bool = False


CATALOG: tuple[SourceInfo, ...] = (
    SourceInfo(
        key=osm.SOURCE_KEY,
        name="OpenStreetMap",
        description="Free community map data. No key needed, but phone numbers are patchy in Pakistan.",
        kind=KIND_DISCOVERY,
        requires_api_key=False,
        default_enabled=True,
    ),
    SourceInfo(
        key=google_places.SOURCE_KEY,
        name="Google Places API",
        description="Best coverage of phone numbers and websites. Needs an API key and is billed per request.",
        kind=KIND_DISCOVERY,
        requires_api_key=True,
        default_enabled=False,
        is_paid=True,
    ),
    SourceInfo(
        key=ENRICHMENT_KEY,
        name="Website contact enrichment",
        description="Reads each business's own website for email, WhatsApp and social pages.",
        kind=KIND_ENRICHMENT,
        requires_api_key=False,
        default_enabled=True,
    ),
)

_BY_KEY = {info.key: info for info in CATALOG}


def get_source_info(key: str) -> SourceInfo | None:
    return _BY_KEY.get(key)


def build_source(
    key: str,
    *,
    api_key: str | None,
    user_agent: str,
    overpass_url: str,
    overpass_min_interval_s: float,
) -> Source:
    if key == osm.SOURCE_KEY:
        return osm.OsmSource(overpass_url, user_agent, min_interval_s=overpass_min_interval_s)
    if key == google_places.SOURCE_KEY:
        if not api_key:
            raise ValueError("Google Places needs an API key")
        return google_places.GooglePlacesSource(api_key)
    raise ValueError(f"Unknown discovery source: {key}")
