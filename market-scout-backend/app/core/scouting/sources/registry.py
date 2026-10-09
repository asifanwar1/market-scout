from app.core.scouting.sources import foursquare, google_places, here, osm, overture, tomtom
from app.core.scouting.sources.base import KIND_ENRICHMENT, Source, SourceBuildContext, SourceInfo

ENRICHMENT_KEY = "website_enrichment"

ENRICHMENT_INFO = SourceInfo(
    key=ENRICHMENT_KEY,
    name="Website contact enrichment",
    description="Reads each business's own website for email, WhatsApp and social pages.",
    kind=KIND_ENRICHMENT,
    requires_api_key=False,
    default_enabled=True,
)

CATALOG: tuple[SourceInfo, ...] = (
    osm.INFO,
    overture.INFO,
    foursquare.INFO,
    google_places.INFO,
    here.INFO,
    tomtom.INFO,
    ENRICHMENT_INFO,
)

_BY_KEY = {info.key: info for info in CATALOG}


def get_source_info(key: str) -> SourceInfo | None:
    return _BY_KEY.get(key)


IMPORT_PREFIX = "import:"


def is_import_key(key: str) -> bool:
    return key.startswith(IMPORT_PREFIX)


def source_label(key: str) -> str:
    info = get_source_info(key)
    if info is not None:
        return info.name
    return key[len(IMPORT_PREFIX):] if is_import_key(key) else key


def build_source(key: str, context: SourceBuildContext) -> Source:
    info = get_source_info(key)
    if info is None or info.build is None:
        raise ValueError(f"Unknown discovery source: {key}")
    return info.build(context)
