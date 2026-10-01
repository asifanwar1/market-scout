from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.utils import slugify
from app.features.geographies import service as geographies_service
from app.features.geographies.models import Geography, GeographyLevel
from app.features.geographies.schemas import GeographyCreate
from app.features.profiles import service as profiles_service
from scripts.seed_data.pakistan import COUNTRY, REGIONS
from scripts.seed_data.solar_profile import PROFILE_NAME, build_solar_profile


def _get_or_create_geography(db: Session, slug: str, payload: GeographyCreate) -> tuple[Geography, bool]:
    existing = geographies_service.get_geography_by_slug(db, slug)
    if existing:
        return existing, False
    return geographies_service.create_geography(db, payload), True


def seed_geographies(db: Session) -> dict[str, int]:
    created = {"provinces": 0, "cities": 0}

    country, _ = _get_or_create_geography(
        db, slugify(COUNTRY), GeographyCreate(name=COUNTRY, level=GeographyLevel.COUNTRY)
    )

    for province_name, cities in REGIONS.items():
        province, province_created = _get_or_create_geography(
            db,
            slugify(province_name),
            GeographyCreate(name=province_name, level=GeographyLevel.PROVINCE, parent_id=country.id),
        )
        created["provinces"] += province_created

        for city_name, latitude, longitude, radius_km in cities:
            _, city_created = _get_or_create_geography(
                db,
                slugify(city_name),
                GeographyCreate(
                    name=city_name,
                    level=GeographyLevel.CITY,
                    parent_id=province.id,
                    latitude=latitude,
                    longitude=longitude,
                    radius_km=radius_km,
                ),
            )
            created["cities"] += city_created
    return created


def seed_solar_profile(db: Session) -> bool:
    if profiles_service.get_profile_by_slug(db, slugify(PROFILE_NAME)):
        return False
    profiles_service.create_profile(db, build_solar_profile())
    return True


def main() -> None:
    db = SessionLocal()
    try:
        geographies = seed_geographies(db)
        print(f"Geographies: {geographies['provinces']} new provinces/regions, {geographies['cities']} new cities.")
        print("Solar profile: created." if seed_solar_profile(db) else "Solar profile: already exists, left unchanged.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
