from decimal import Decimal

import pytest

from app.core.scouting import place_store
from app.core.scouting.sources.foursquare import FoursquareSource
from app.core.scouting.types import SearchArea, SearchQuery
from scripts import download_foursquare

LAHORE = SearchArea(latitude=31.5204, longitude=74.3587, radius_km=20, name="Lahore")
ELECTRONICS = {"clauses": [["shop=electronics"]]}

ROW_FIELDS = (
    "id", "name", "labels", "date_closed", "tel", "website", "email", "facebook_id", "instagram", "address", "locality",
    "latitude", "longitude",
)
ROW_VALUES = (
    "fsq-1", " Noor Solar ", ["Retail > Electronics Store"], None, " 0300 1234567 ", " https://noor.pk ", "info@noor.pk",
    "12345", "@noorsolar", "12 Mall Road", "Lahore", 31.52, 74.36,
)

CREATE_PLACES = """
CREATE TABLE places AS SELECT * FROM (VALUES
    ('p1', 'Noor Electronics', ['Retail > Electronics Store'], NULL, '03001234567', 'https://noor.pk', NULL, NULL, NULL,
     '1 Mall Road', 'Lahore', 'PK', 31.52, 74.36),
    ('p2', 'Karachi Electronics', ['Retail > Electronics Store'], NULL, '03111234567', NULL, NULL, NULL, NULL,
     NULL, 'Karachi', 'PK', 24.86, 67.0),
    ('p3', 'Delhi Electronics', ['Retail > Electronics Store'], NULL, '999', NULL, NULL, NULL, NULL,
     NULL, 'Delhi', 'IN', 28.6, 77.2),
    ('p4', 'Closed Electronics', ['Retail > Electronics Store'], DATE '2024-05-01', '03221234567', NULL, NULL, NULL, NULL,
     NULL, 'Lahore', 'PK', 31.53, 74.37)
) AS t(fsq_place_id, name, fsq_category_labels, date_closed, tel, website, email, facebook_id, instagram, address, locality,
       country, latitude, longitude)
"""

CREATE_FOREIGN_PLACE = """
COPY (
    SELECT 'x' AS fsq_place_id, 'Far Shop' AS name, ['Retail'] AS fsq_category_labels, NULL::DATE AS date_closed,
           '1' AS tel, NULL AS website, NULL AS email, NULL AS facebook_id, NULL AS instagram, NULL AS address,
           'Paris' AS locality, 'FR' AS country, 48.8 AS latitude, 2.3 AS longitude
) TO '{path}' (FORMAT PARQUET)
"""


def row(**changes):
    values = dict(zip(ROW_FIELDS, ROW_VALUES, strict=True))
    values.update(changes)
    return tuple(values[name] for name in ROW_FIELDS)


def test_a_row_becomes_a_place_with_trimmed_contacts_and_social_urls():
    result = download_foursquare.to_place(row())

    assert result["id"] == "fsq-1" and result["name"] == "Noor Solar"
    assert result["categories"] == ["Retail > Electronics Store"]
    assert result["phones"] == ["0300 1234567"] and result["websites"] == ["https://noor.pk"] and result["emails"] == ["info@noor.pk"]
    assert result["socials"] == ["https://www.facebook.com/12345", "https://www.instagram.com/noorsolar"]
    assert result["city"] == "Lahore" and result["status"] is None and result["dataset"] == "foursquare"


def test_decimal_coordinates_become_floats_the_store_can_hold():
    result = download_foursquare.to_place(row(latitude=Decimal("31.520000"), longitude=Decimal("74.360000")))

    assert result["latitude"] == 31.52 and isinstance(result["latitude"], float)
    assert result["longitude"] == 74.36 and isinstance(result["longitude"], float)


def test_a_closed_place_is_marked_permanently_closed():
    assert download_foursquare.to_place(row(date_closed="2025-01-01"))["status"] == place_store.STATUS_PERMANENTLY_CLOSED


def test_blank_contacts_become_empty_lists():
    result = download_foursquare.to_place(row(tel="  ", website=None, email="", facebook_id=None, instagram=None, labels=None))

    assert result["phones"] == [] and result["websites"] == [] and result["emails"] == [] and result["socials"] == []
    assert result["categories"] == []


@pytest.mark.parametrize("changes", [{"name": None}, {"id": None}, {"latitude": None}, {"longitude": None}])
def test_a_row_without_a_name_id_or_position_is_dropped(changes):
    assert download_foursquare.to_place(row(**changes)) is None


@pytest.fixture()
def duckdb_module():
    return pytest.importorskip("duckdb")


@pytest.fixture()
def parquet_file(tmp_path, duckdb_module):
    path = tmp_path / "places.parquet"
    connection = duckdb_module.connect()
    connection.execute(CREATE_PLACES)
    connection.execute(f"COPY places TO '{path.as_posix()}' (FORMAT PARQUET)")
    connection.close()
    return path


def test_building_the_store_keeps_only_pakistans_places_and_the_source_can_search_it(parquet_file, tmp_path):
    target = tmp_path / "foursquare.sqlite"

    count = download_foursquare.build_store([str(parquet_file)], "2026-09-30", str(target))
    result = FoursquareSource(str(target)).search(SearchQuery(text="x", area=LAHORE, osm_filter=ELECTRONICS))

    assert count == 3
    assert place_store.read_info(target).release == "2026-09-30"
    assert [business.external_id for business in result.businesses] == ["p1"]
    assert result.businesses[0].phones == ["03001234567"] and result.businesses[0].website == "https://noor.pk"


def test_files_with_no_places_in_pakistan_leave_the_existing_copy_alone(tmp_path, duckdb_module):
    target = tmp_path / "foursquare.sqlite"
    place_store.write_store(target, [download_foursquare.to_place(row())], release="old")
    foreign = tmp_path / "foreign.parquet"
    connection = duckdb_module.connect()
    connection.execute(CREATE_FOREIGN_PLACE.format(path=foreign.as_posix()))
    connection.close()

    with pytest.raises(place_store.StoreError):
        download_foursquare.build_store([str(foreign)], "new", str(target))

    assert place_store.read_info(target).release == "old"
