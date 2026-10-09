from app.core.scouting import place_store
from app.core.scouting.sources import local_places
from app.core.scouting.sources.base import (
    KIND_DISCOVERY,
    DatasetSpec,
    SourceBuildContext,
    SourceInfo,
)
from app.core.scouting.types import RawBusiness

SOURCE_KEY = "foursquare"

_ELECTRICAL_AND_ENERGY = frozenset(
    {"electronics store", "electrical", "electrician", "lighting", "appliance", "solar", "energy", "utility"}
)
_HARDWARE = frozenset({"hardware", "home improvement", "building material", "building supply"})
_WHOLESALE = frozenset({"wholesale", "distributor", "importer", "import and export", "import/export"})
_CONTRACTORS = frozenset({"contractor", "construction", "engineer", "electrician", "solar"})

TAG_CATEGORIES: dict[str, frozenset[str] | None] = {
    "shop=electrical": _ELECTRICAL_AND_ENERGY,
    "shop=electronics": frozenset({"electronics store", "appliance", "audio visual"}),
    "shop=hardware": _HARDWARE,
    "shop=doityourself": _HARDWARE,
    "shop=trade": _WHOLESALE | _HARDWARE,
    "shop=wholesale": _WHOLESALE,
    "shop=lighting": frozenset({"lighting"}),
    "shop=appliance": frozenset({"appliance"}),
    "shop=computer": frozenset({"computer", "electronics store"}),
    "craft=electrician": frozenset({"electrician"}),
    "craft=hvac": frozenset({"hvac", "heating", "air conditioning"}),
    "craft=builder": frozenset({"contractor", "construction", "builder"}),
    "office=company": None,
    "office=energy_supplier": frozenset({"energy", "utility", "power"}),
    "office=engineer": frozenset({"engineer"}),
    "office=construction_company": frozenset({"contractor", "construction"}),
    "office=contractor": _CONTRACTORS,
}


def translate_filter(osm_filter: dict | None) -> list[local_places.Clause]:
    return local_places.translate_filter(osm_filter, TAG_CATEGORIES)


def supports(osm_filter: dict | None) -> bool:
    return bool(translate_filter(osm_filter))


def place_to_business(place: place_store.Place, release: str) -> RawBusiness:
    return RawBusiness(
        source_key=SOURCE_KEY,
        external_id=place.id,
        name=place.name,
        address=local_places.place_address(place),
        latitude=place.latitude,
        longitude=place.longitude,
        phones=place.phones,
        emails=place.emails,
        website=local_places.place_website(place),
        categories=place.categories,
        raw={"dataset": place.dataset, "release": release, "socials": place.socials},
    )


class FoursquareSource(local_places.LocalPlaceSource):
    key = SOURCE_KEY
    label = "Foursquare"
    tag_categories = TAG_CATEGORIES
    exact_categories = False

    def to_business(self, place: place_store.Place, release: str) -> RawBusiness:
        return place_to_business(place, release)


def build(context: SourceBuildContext) -> FoursquareSource:
    return FoursquareSource(context.settings.FOURSQUARE_DB_PATH)


INFO = SourceInfo(
    key=SOURCE_KEY,
    name="Foursquare Places",
    description="Free open dataset of businesses with phones and websites, kept on this computer. Searches are instant.",
    kind=KIND_DISCOVERY,
    requires_api_key=False,
    default_enabled=True,
    dataset=DatasetSpec(path=lambda settings: settings.FOURSQUARE_DB_PATH, download_command="python -m scripts.download_foursquare"),
    supports_filter=supports,
    build=build,
)
