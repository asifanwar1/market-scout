from app.features.geographies.models import Geography
from app.features.profiles.models import Profile, ProfileSearchTerm
from scripts.seed import seed_geographies, seed_solar_profile
from scripts.seed_data.pakistan import REGIONS


def test_seed_geographies_builds_the_pakistan_hierarchy(db_session):
    created = seed_geographies(db_session)

    assert created["provinces"] == len(REGIONS)
    assert created["cities"] == sum(len(cities) for cities in REGIONS.values())

    pakistan = db_session.query(Geography).filter_by(slug="pakistan").one()
    regions = {g.name for g in pakistan.children}
    assert {"Punjab", "Sindh", "Khyber Pakhtunkhwa", "Balochistan", "Islamabad Capital Territory"} == regions

    lahore = db_session.query(Geography).filter_by(slug="lahore").one()
    assert lahore.parent.name == "Punjab"
    assert lahore.level == "city"
    assert None not in (lahore.latitude, lahore.longitude, lahore.radius_km)


def test_every_seeded_city_has_a_search_area_inside_pakistan(db_session):
    seed_geographies(db_session)
    cities = db_session.query(Geography).filter_by(level="city").all()

    assert len(cities) >= 30
    for city in cities:
        assert 23 <= city.latitude <= 37, city.name
        assert 60 <= city.longitude <= 78, city.name
        assert 0 < city.radius_km <= 30, city.name


def test_seed_is_idempotent_and_never_overwrites_edits(db_session):
    seed_geographies(db_session)
    lahore = db_session.query(Geography).filter_by(slug="lahore").one()
    lahore.radius_km = 5
    db_session.commit()

    again = seed_geographies(db_session)

    assert again == {"provinces": 0, "cities": 0}
    assert db_session.query(Geography).filter_by(slug="lahore").one().radius_km == 5


def test_seed_solar_profile_is_complete_and_valid(db_session):
    assert seed_solar_profile(db_session) is True

    profile = db_session.query(Profile).filter_by(slug="solar-inverters-batteries").one()
    assert [s.slug for s in profile.segments] == [
        "dealer", "importer", "wholesaler", "retailer", "installer", "contractor",
    ]
    # Every segment is searched for, in both English and Roman Urdu overall.
    assert {t.segment.slug for t in profile.search_terms} == {s.slug for s in profile.segments}
    assert {"en", "ur-roman"} <= {t.language for t in profile.search_terms}
    # OpenStreetMap needs a filter; Roman-Urdu terms are Places-only.
    assert any(t.osm_filter for t in profile.search_terms)
    assert all(t.osm_filter is None for t in profile.search_terms if t.language == "ur-roman")


def test_seed_solar_profile_is_idempotent(db_session):
    assert seed_solar_profile(db_session) is True
    terms_before = db_session.query(ProfileSearchTerm).count()

    assert seed_solar_profile(db_session) is False
    assert db_session.query(Profile).count() == 1
    assert db_session.query(ProfileSearchTerm).count() == terms_before


# Rough bounding boxes (south, north, west, east): wide enough for the real borders, tight enough
# that a typo'd coordinate (a swapped latitude/longitude, a dropped digit) lands outside its province.
PROVINCE_BOXES = {
    "Punjab": (27.7, 34.1, 69.3, 75.5),
    "Sindh": (23.6, 28.6, 66.6, 71.2),
    "Khyber Pakhtunkhwa": (31.0, 36.0, 69.2, 74.2),
    "Balochistan": (24.8, 32.3, 60.8, 70.4),
    "Islamabad Capital Territory": (33.4, 33.9, 72.8, 73.4),
}


def test_every_seeded_city_lies_inside_its_own_province():
    for province, cities in REGIONS.items():
        south, north, west, east = PROVINCE_BOXES[province]
        for name, latitude, longitude, _radius in cities:
            assert south <= latitude <= north and west <= longitude <= east, f"{name} ({latitude}, {longitude}) is not in {province}"


def test_city_names_are_unique_so_every_city_gets_its_own_slug():
    names = [name.lower() for cities in REGIONS.values() for name, *_ in cities]
    assert len(names) == len(set(names))


def test_the_list_covers_big_and_small_places_in_every_province():
    sizes = {province: len(cities) for province, cities in REGIONS.items()}
    assert sizes["Punjab"] >= 50 and sizes["Sindh"] >= 30 and sizes["Khyber Pakhtunkhwa"] >= 30 and sizes["Balochistan"] >= 30
    small_towns = [name for cities in REGIONS.values() for name, _la, _lo, radius in cities if radius <= 5]
    assert len(small_towns) >= 60
