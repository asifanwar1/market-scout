from app.core.scouting import place_store
from app.core.scouting.sources import local_places
from app.core.scouting.sources.base import (
    KIND_DISCOVERY,
    DatasetSpec,
    SourceBuildContext,
    SourceInfo,
)
from app.core.scouting.types import RawBusiness

SOURCE_KEY = "overture"

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
        raw={"confidence": place.confidence, "dataset": place.dataset, "release": release, "socials": place.socials},
    )


class OvertureSource(local_places.LocalPlaceSource):
    key = SOURCE_KEY
    label = "Overture"
    tag_categories = TAG_CATEGORIES

    def to_business(self, place: place_store.Place, release: str) -> RawBusiness:
        return place_to_business(place, release)


def build(context: SourceBuildContext) -> OvertureSource:
    return OvertureSource(context.settings.OVERTURE_DB_PATH, min_confidence=context.settings.OVERTURE_MIN_CONFIDENCE)


INFO = SourceInfo(
    key=SOURCE_KEY,
    name="Overture Maps",
    description="Free open dataset with many more Pakistani businesses and phone numbers than OpenStreetMap. Searches are instant.",
    kind=KIND_DISCOVERY,
    requires_api_key=False,
    default_enabled=True,
    dataset=DatasetSpec(path=lambda settings: settings.OVERTURE_DB_PATH, download_command="python -m scripts.download_overture"),
    supports_filter=supports,
    build=build,
)
