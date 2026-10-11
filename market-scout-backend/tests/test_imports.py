import csv
import io
import json
from pathlib import Path

import pytest
from openpyxl import Workbook

from app.core.config import settings
from app.features.businesses.models import Business, BusinessClassification, ContactPoint, SourceRecord
from app.features.geographies.models import Geography
from app.features.imports import service
from app.features.imports.models import Import, ImportStatus
from app.features.jobs.models import Job
from app.features.profiles.models import ProfileSegment

BASE = "/api/v1/imports"
LABEL = "AEDB test list"

COLUMNS = ["Company", "Phone", "Mobile", "Email", "City", "Address"]
ROWS = [
    ["Axovolt Pvt Ltd", "042-35342996", "0305-4009082", "axovolt3@gmail.com", "Lahore", "Office 9, Bahria Town, Lahore."],
    ["Inverex Power Solution", "021-32750760", "0321-2099988", "info@aptinverex.com; zstraders@yahoo.com", "", "Regal Chowk, Saddar, Karachi."],
    ["Pak Evergreen Energy", "051-4444758", "", "", "", "Sector I-9/3, Islamabad."],
    ["Remote Solar", "", "0300 5555555", "", "Atlantis", "Somewhere with no known city"],
    ["No Contact Co", "", "", "", "Lahore", "Mall Road, Lahore"],
    ["", "", "0300 1111111", "", "Lahore", ""],
]


def csv_bytes(rows=ROWS, columns=COLUMNS) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(columns)
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def mapping(**overrides) -> dict:
    base = {"name": "Company", "phones": ["Phone", "Mobile"], "emails": ["Email"], "city": "City", "address": "Address"}
    return {**base, **overrides}


@pytest.fixture()
def admin(admin_user, auth_headers):
    return auth_headers(admin_user)


@pytest.fixture()
def options(seeded_profile, db_session):
    quetta = db_session.query(Geography).filter_by(slug="quetta").one()

    def _options(**overrides) -> dict:
        base = {
            "label": LABEL, "profile_id": seeded_profile.id, "segment_slug": "installer",
            "default_geography_id": quetta.id, "require_contact": True, "mapping": mapping(),
        }
        return {**base, **overrides}

    return _options


def upload(client, headers, options: dict, content: bytes | None = None, filename: str = "list.csv"):
    return client.post(
        f"{BASE}/", headers=headers,
        files={"file": (filename, content if content is not None else csv_bytes(), "text/csv")},
        data={"options": json.dumps(options)},
    )


def run_import(client, db_session, headers, options: dict, **kwargs) -> Import:
    response = upload(client, headers, options, **kwargs)
    assert response.status_code == 201, response.text
    service.execute_import(db_session, response.json()["id"])
    return db_session.get(Import, response.json()["id"])


def test_preview_shows_the_columns_a_sample_and_a_first_guess(client, admin):
    response = client.post(f"{BASE}/preview", headers=admin, files={"file": ("list.csv", csv_bytes(), "text/csv")})

    body = response.json()
    assert response.status_code == 200
    assert body["columns"] == COLUMNS and body["row_count"] == len(ROWS)
    assert body["sample"][0]["Company"] == "Axovolt Pvt Ltd"
    assert body["suggested_mapping"]["name"] == "Company"
    assert set(body["suggested_mapping"]["phones"]) == {"Phone", "Mobile"}
    assert body["suggested_mapping"]["emails"] == ["Email"]


def test_preview_stores_nothing(client, admin, db_session):
    client.post(f"{BASE}/preview", headers=admin, files={"file": ("list.csv", csv_bytes(), "text/csv")})
    assert db_session.query(Import).count() == 0 and db_session.query(Business).count() == 0


@pytest.mark.parametrize(
    "filename, content, message",
    [
        ("list.pdf", b"x", "Upload a .csv or .xlsx"),
        ("list.xls", b"x", "Old .xls"),
        ("list.csv", b"", "empty"),
        ("list.csv", b"Company,Phone\n", "no data rows"),
        ("list.xlsx", b"not a zip", "valid .xlsx"),
    ],
)
def test_preview_explains_a_file_it_cannot_read(client, admin, filename, content, message):
    response = client.post(f"{BASE}/preview", headers=admin, files={"file": (filename, content, "application/octet-stream")})
    assert response.status_code == 400 and message in response.json()["detail"]


def test_a_file_over_the_size_limit_is_refused(client, admin, monkeypatch):
    monkeypatch.setattr(settings, "IMPORT_MAX_MB", 1)
    big = ("Company,Phone\n" + "A Shop,0300 1234567\n" * 80_000).encode()
    assert len(big) > 1024 * 1024
    response = client.post(f"{BASE}/preview", headers=admin, files={"file": ("list.csv", big, "text/csv")})
    assert response.status_code == 400 and "larger than 1 MB" in response.json()["detail"]


def test_an_excel_file_can_be_uploaded(client, admin, options, db_session):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(COLUMNS)
    sheet.append(["Axovolt Pvt Ltd", "042-35342996", 3054009082, "axovolt3@gmail.com", "Lahore", ""])
    buffer = io.BytesIO()
    workbook.save(buffer)

    record = run_import(client, db_session, admin, options(), content=buffer.getvalue(), filename="list.xlsx")

    assert record.status == ImportStatus.COMPLETED.value and record.stats["new"] == 1
    phones = {c.value for c in db_session.query(ContactPoint).filter_by(kind="phone")}
    assert "+923054009082" in phones


def test_creating_an_import_cleans_the_rows_and_queues_it(client, admin, options, db_session):
    response = upload(client, admin, options())

    body = response.json()
    assert response.status_code == 201
    assert body["status"] == "queued" and body["source_key"] == f"import:{LABEL}"
    assert body["rows_total"] == 6 and body["rows_to_import"] == 4
    assert body["skipped"] == {"no_contact": 1, "no_name": 1}
    assert body["stats"]["no_city"] == 0
    assert body["profile_name"] and body["default_geography_name"] == "Quetta"
    assert db_session.query(Business).count() == 0
    assert (Path(settings.IMPORTS_DIR) / f"{body['id']}.jsonl").exists()


def test_running_an_import_stores_businesses_with_their_source_city_and_type(client, admin, options, db_session):
    record = run_import(client, db_session, admin, options())

    assert record.status == ImportStatus.COMPLETED.value and record.error is None
    assert (record.rows_done, record.rows_to_import) == (4, 4) and record.progress_percent == 100
    assert record.stats["found"] == 4 and record.stats["new"] == 4 and record.stats["merged"] == 0
    assert record.stats["with_phone"] == 4 and record.stats["with_email"] == 2
    assert record.finished_at is not None
    assert not (Path(settings.IMPORTS_DIR) / f"{record.id}.jsonl").exists()

    businesses = {b.name: b for b in db_session.query(Business)}
    assert set(businesses) == {"Axovolt Pvt Ltd", "Inverex Power Solution", "Pak Evergreen Energy", "Remote Solar"}
    cities = {name: b.geography.name for name, b in businesses.items()}
    assert cities == {
        "Axovolt Pvt Ltd": "Lahore",
        "Inverex Power Solution": "Karachi",
        "Pak Evergreen Energy": "Islamabad",
        "Remote Solar": "Quetta",
    }

    key = f"import:{LABEL}"
    assert {r.source_key for r in db_session.query(SourceRecord)} == {key}
    assert {c.source_key for c in db_session.query(ContactPoint)} == {key}
    raw = db_session.query(SourceRecord).join(Business).filter(Business.name == "Axovolt Pvt Ltd").one()
    assert raw.raw_payload["Company"] == "Axovolt Pvt Ltd" and raw.run_id is None

    segments = dict(
        db_session.query(Business.name, ProfileSegment.slug)
        .join(BusinessClassification, BusinessClassification.business_id == Business.id)
        .join(ProfileSegment, ProfileSegment.id == BusinessClassification.segment_id)
    )
    assert set(segments.values()) == {"installer"}


def test_phones_and_emails_are_normalised(client, admin, options, db_session):
    run_import(client, db_session, admin, options())

    inverex = db_session.query(Business).filter_by(name="Inverex Power Solution").one()
    contacts = {(c.kind, c.value) for c in inverex.contact_points}
    assert ("phone", "+922132750760") in contacts and ("phone", "+923212099988") in contacts
    assert ("email", "info@aptinverex.com") in contacts and ("email", "zstraders@yahoo.com") in contacts
    mobile = next(c for c in inverex.contact_points if c.value == "+923212099988")
    assert mobile.is_mobile and mobile.whatsapp_likely


def test_importing_the_same_list_again_adds_nothing_new(client, admin, options, db_session):
    run_import(client, db_session, admin, options())
    again = run_import(client, db_session, admin, options())

    assert again.stats["new"] == 0 and again.stats["merged"] == 4
    assert db_session.query(Business).count() == 4
    assert db_session.query(SourceRecord).count() == 4


def test_a_newer_version_of_the_list_recognises_the_same_companies_in_a_different_order(client, admin, options, db_session):
    run_import(client, db_session, admin, options())
    reshuffled = csv_bytes(list(reversed(ROWS)) + [["Brand New Solar", "042-35771769", "", "", "Lahore", ""]])

    again = run_import(client, db_session, admin, options(), content=reshuffled)

    assert again.stats["new"] == 1 and again.stats["merged"] == 4
    assert db_session.query(Business).count() == 5


def test_a_company_already_found_by_a_search_is_merged_not_duplicated(client, admin, options, db_session, make_business):
    existing = make_business("Axovolt Pvt Ltd", city="lahore", phones=["042 35342996"], source="osm")

    record = run_import(client, db_session, admin, options())

    assert record.stats["merged"] == 1 and record.stats["new"] == 3
    assert db_session.query(Business).count() == 4
    sources = {r.source_key for r in db_session.query(SourceRecord).filter_by(business_id=existing.id)}
    assert sources == {"osm", f"import:{LABEL}"}


def test_someone_on_do_not_contact_is_refused(client, admin, options, db_session):
    client.post("/api/v1/compliance/do-not-contact", headers=admin, json={"phone": "0305-4009082"})

    record = run_import(client, db_session, admin, options())

    assert record.stats["blocked"] == 1 and record.stats["new"] == 3
    assert db_session.query(Business).filter_by(name="Axovolt Pvt Ltd").count() == 0


def test_rows_with_no_contact_can_be_kept_when_asked(client, admin, options, db_session):
    record = run_import(client, db_session, admin, options(require_contact=False))
    assert record.rows_to_import == 5 and record.skipped == {"no_name": 1}
    assert db_session.query(Business).filter_by(name="No Contact Co").count() == 1


def test_without_a_default_city_unplaced_rows_are_counted(client, admin, options, db_session):
    response = upload(client, admin, options(default_geography_id=None))
    assert response.json()["stats"]["no_city"] == 1
    service.execute_import(db_session, response.json()["id"])
    assert db_session.query(Business).filter_by(name="Remote Solar").one().geography_id is None


def test_a_list_with_coordinates_places_businesses_on_the_map(client, admin, options, db_session):
    rows = [["Axovolt Pvt Ltd", "042-35342996", "", "", "Lahore", "", "31.5204", "74.3587"]]
    content = csv_bytes(rows, COLUMNS + ["Lat", "Lon"])
    run_import(client, db_session, admin, options(mapping=mapping(latitude="Lat", longitude="Lon")), content=content)
    business = db_session.query(Business).one()
    assert (business.latitude, business.longitude) == (31.5204, 74.3587)


@pytest.mark.parametrize(
    "change, fragment",
    [
        ({"mapping": mapping(name="Nope")}, "aren't in the file: Nope"),
        ({"mapping": mapping(phones=["Phone", "Nope", "Also nope"])}, "Also nope, Nope"),
        ({"mapping": mapping(latitude="City")}, "both latitude and longitude"),
        ({"mapping": {"name": "Company"}}, "at least one phone, email or website"),
        ({"profile_id": 99999}, "profile doesn't exist"),
        ({"segment_slug": "astronaut"}, "isn't part of the chosen profile"),
        ({"label": "x"}, "label"),
        ({"label": ""}, "label"),
    ],
)
def test_a_bad_request_is_explained_and_stores_nothing(client, admin, options, db_session, change, fragment):
    response = upload(client, admin, options(**change))
    assert response.status_code == 400, response.text
    assert fragment in response.json()["detail"]
    assert db_session.query(Import).count() == 0


def test_the_default_city_must_be_a_city(client, admin, options, db_session):
    punjab = db_session.query(Geography).filter_by(slug="punjab").one()
    response = upload(client, admin, options(default_geography_id=punjab.id))
    assert response.status_code == 400 and "must be one of the cities" in response.json()["detail"]


def test_options_that_are_not_json_are_a_plain_400(client, admin):
    response = client.post(f"{BASE}/", headers=admin, files={"file": ("list.csv", csv_bytes(), "text/csv")}, data={"options": "not json"})
    assert response.status_code == 400


def test_a_file_where_no_row_can_be_imported_says_why(client, admin, options):
    content = csv_bytes([["", "", "0300 1111111", "", "", ""], ["No Contact Co", "", "", "", "", ""]])
    response = upload(client, admin, options(), content=content)
    assert response.status_code == 400
    assert "None of the 2 rows" in response.json()["detail"] and "no name" in response.json()["detail"]


def test_a_queued_import_can_be_cancelled(client, admin, options, db_session):
    created = upload(client, admin, options()).json()

    response = client.post(f"{BASE}/{created['id']}/cancel", headers=admin)

    assert response.json()["status"] == "cancelled"
    assert not (Path(settings.IMPORTS_DIR) / f"{created['id']}.jsonl").exists()
    service.execute_import(db_session, created["id"])
    assert db_session.query(Business).count() == 0


def test_a_running_import_stops_between_batches_and_keeps_what_it_stored(client, admin, options, db_session, monkeypatch):
    monkeypatch.setattr(service, "BATCH_SIZE", 2)
    original = service._store_batch

    def store_then_ask_to_cancel(db, record, batch, scoring, totals):
        original(db, record, batch, scoring, totals)
        record.status = ImportStatus.CANCELLING.value
        db.commit()

    monkeypatch.setattr(service, "_store_batch", store_then_ask_to_cancel)

    record = run_import(client, db_session, admin, options())

    assert record.status == ImportStatus.CANCELLED.value
    assert record.rows_done == 2 < record.rows_to_import
    assert db_session.query(Business).count() == 2


def test_a_finished_import_cannot_be_cancelled(client, admin, options, db_session):
    record = run_import(client, db_session, admin, options())
    assert client.post(f"{BASE}/{record.id}/cancel", headers=admin).status_code == 400


def test_an_interrupted_import_picks_up_after_the_rows_already_stored(client, admin, options, db_session):
    created = upload(client, admin, options()).json()
    record = db_session.get(Import, created["id"])
    record.status, record.rows_done = ImportStatus.RUNNING.value, 1
    db_session.commit()

    assert service.recover_import(db_session, record.id, True) is True
    assert db_session.get(Import, record.id).status == "queued"

    service.execute_import(db_session, record.id)

    finished = db_session.get(Import, record.id)
    assert finished.status == "completed" and finished.rows_done == finished.rows_to_import
    assert db_session.query(Business).count() == finished.rows_to_import - 1


def test_an_interrupted_import_out_of_tries_is_marked_failed_and_its_rows_removed(client, admin, options, db_session):
    created = upload(client, admin, options()).json()
    record = db_session.get(Import, created["id"])
    record.status = ImportStatus.RUNNING.value
    db_session.commit()

    assert service.recover_import(db_session, record.id, False) is False

    db_session.refresh(record)
    assert record.status == "failed" and "Import the file again" in record.error
    assert not (Path(settings.IMPORTS_DIR) / f"{record.id}.jsonl").exists()


def test_an_import_being_cancelled_when_interrupted_ends_cancelled(client, admin, options, db_session):
    created = upload(client, admin, options()).json()
    record = db_session.get(Import, created["id"])
    record.status = ImportStatus.CANCELLING.value
    db_session.commit()

    assert service.recover_import(db_session, record.id, True) is False

    db_session.refresh(record)
    assert record.status == "cancelled"


def test_uploading_queues_a_job_with_the_import(client, admin, options, db_session):
    created = upload(client, admin, options()).json()

    assert db_session.query(Job).filter_by(kind="import", ref_id=created["id"], status="queued").count() == 1


def test_an_import_whose_rows_went_missing_fails_with_a_clear_message(client, admin, options, db_session):
    created = upload(client, admin, options()).json()
    (Path(settings.IMPORTS_DIR) / f"{created['id']}.jsonl").unlink()

    service.execute_import(db_session, created["id"])

    record = db_session.get(Import, created["id"])
    assert record.status == "failed" and "Upload the file again" in record.error


def test_an_import_whose_profile_was_deleted_fails_with_a_clear_message(client, admin, options, db_session, seeded_profile):
    created = upload(client, admin, options()).json()
    db_session.delete(seeded_profile)
    db_session.commit()

    service.execute_import(db_session, created["id"])

    assert "profile for this import no longer exists" in db_session.get(Import, created["id"]).error


def test_the_history_lists_newest_first_and_a_single_import_can_be_read(client, admin, options, db_session):
    first = run_import(client, db_session, admin, options(label="First list"))
    second = run_import(client, db_session, admin, options(label="Second list"))

    listed = client.get(f"{BASE}/", headers=admin).json()
    assert listed["count"] == 2 and [i["label"] for i in listed["data"]] == ["Second list", "First list"]
    assert client.get(f"{BASE}/{first.id}", headers=admin).json()["label"] == "First list"
    assert client.get(f"{BASE}/{second.id}", headers=admin).json()["stats"]["found"] == 4
    assert client.get(f"{BASE}/99999", headers=admin).status_code == 404
    assert len(client.get(f"{BASE}/?limit=1", headers=admin).json()["data"]) == 1


def test_a_lead_says_which_list_it_came_from(client, admin, options, db_session):
    run_import(client, db_session, admin, options())
    lead = db_session.query(Business).filter_by(name="Axovolt Pvt Ltd").one()

    detail = client.get(f"/api/v1/businesses/{lead.id}", headers=admin).json()
    assert [s["source_key"] for s in detail["sources"]] == [f"import:{LABEL}"]

    listed = client.get("/api/v1/businesses/?source=import:" + LABEL, headers=admin).json()
    assert listed["count"] == 4


def test_the_csv_export_names_the_list_in_found_by(client, admin, options, db_session):
    run_import(client, db_session, admin, options())
    text = client.get("/api/v1/exports/leads.csv", headers=admin).content.decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(text)))
    assert {row["Found by"] for row in rows} == {LABEL}


def test_insights_compare_an_imported_list_with_the_other_sources(client, admin, options, db_session, make_business):
    make_business("Axovolt Pvt Ltd", city="lahore", phones=["042 35342996"], source="osm")
    run_import(client, db_session, admin, options())

    rows = {row["key"]: row for row in client.get("/api/v1/insights/sources", headers=admin).json()["data"]}

    imported = rows[f"import:{LABEL}"]
    assert imported["name"] == LABEL and imported["kind"] == "import" and imported["is_paid"] is False
    assert imported["found"] == 4 and imported["exclusive"] == 3
    assert imported["with_phone"] == 4 and imported["with_email"] == 2 and imported["with_whatsapp"] >= 3
    assert imported["estimated_cost_usd"] is None
    assert rows["osm"]["found"] == 1


def test_two_lists_are_two_sources_and_one_label_is_one_source(client, admin, options, db_session):
    run_import(client, db_session, admin, options(label="List A"))
    run_import(client, db_session, admin, options(label="List B", mapping=mapping()),
               content=csv_bytes([["Other Solar", "042-35771769", "", "", "Lahore", ""]]))
    keys = {row["key"] for row in client.get("/api/v1/insights/sources", headers=admin).json()["data"]}
    assert {"import:List A", "import:List B"} <= keys


AGENT_ROWS = [
    ["Royal Energy Pakistan", "0330-5845448", "", "", "Karachi", ""],
    ["Safa Industry", "0330-5845448", "", "", "Karachi", ""],
    ["AFM Energy (Private) Limited", "0330-5845448", "", "", "Karachi", ""],
    ["Salim Winding Works (Private) Limited", "021-32566309", "", "", "Karachi", ""],
    ["Salim Winding Works", "021-32566309", "", "", "Karachi", ""],
]


def test_an_agents_number_on_many_unrelated_companies_does_not_merge_them(client, admin, options, db_session):
    record = run_import(client, db_session, admin, options(), content=csv_bytes(AGENT_ROWS))

    names = sorted(b.name for b in db_session.query(Business))
    assert names == ["AFM Energy (Private) Limited", "Royal Energy Pakistan", "Safa Industry", "Salim Winding Works (Private) Limited"]
    assert record.stats["shared_phones"] == 1 and record.stats["new"] == 4 and record.stats["merged"] == 1
    for company in ("Royal Energy Pakistan", "Safa Industry", "AFM Energy (Private) Limited"):
        lead = db_session.query(Business).filter_by(name=company).one()
        assert {c.value for c in lead.contact_points if c.kind == "phone"} == {"+923305845448"}


def test_a_number_on_only_two_different_companies_is_still_trusted_to_match(client, admin, options, db_session):
    rows = [["Al Noor Solar", "0300 4438424", "", "", "Lahore", ""], ["Al Noor Solar Dealers", "0300 4438424", "", "", "Lahore", ""]]
    record = run_import(client, db_session, admin, options(), content=csv_bytes(rows))
    assert record.stats["shared_phones"] == 0 and db_session.query(Business).count() == 1


def test_a_blocked_agent_number_still_blocks_every_company_that_lists_it(client, admin, options, db_session):
    client.post("/api/v1/compliance/do-not-contact", headers=admin, json={"phone": "0330-5845448"})

    record = run_import(client, db_session, admin, options(), content=csv_bytes(AGENT_ROWS))

    assert record.stats["blocked"] == 3
    assert sorted(b.name for b in db_session.query(Business)) == ["Salim Winding Works (Private) Limited"]


def test_the_import_details_report_how_many_numbers_were_shared(client, admin, options, db_session):
    record = run_import(client, db_session, admin, options(), content=csv_bytes(AGENT_ROWS))
    assert client.get(f"{BASE}/{record.id}", headers=admin).json()["stats"]["shared_phones"] == 1


NAME_ONLY_COLUMNS = ["Company", "City", "Address"]
NAME_ONLY_ROWS = [
    ["Kashif Traders", "Lahore", "Johar Town, Lahore"],
    ["Malik Traders", "Lahore", "Model Town, Lahore"],
    ["Totally Unknown Co", "Lahore", "Gulberg, Lahore"],
    ["Kashif Traders", "Karachi", "Saddar, Karachi"],
]


@pytest.fixture()
def overture_places(tmp_path, monkeypatch):
    from app.core.scouting import place_store

    path = tmp_path / "overture.sqlite"
    monkeypatch.setattr(settings, "OVERTURE_DB_PATH", str(path))

    def place(identifier, name, latitude=31.52, longitude=74.36, **extra):
        return {
            "id": identifier, "name": name, "categories": ["electronics_store"], "confidence": 0.8,
            "latitude": latitude, "longitude": longitude, "phones": ["+923004309775"], "websites": ["https://kashif.pk"], **extra,
        }

    place_store.write_store(
        path,
        [
            place("gers-kashif", "Kashif Traders"),
            place("gers-malik-1", "Malik Traders", phones=["+923001000001"], websites=[]),
            place("gers-malik-2", "Malik Traders", latitude=31.55, phones=["+923001000002"], websites=[]),
        ],
        release="2026-09-23.1",
    )
    return path


def name_only(**overrides) -> dict:
    return {"mapping": {"name": "Company", "city": "City", "address": "Address"}, **overrides}


def name_only_import(client, db_session, admin, options, **overrides):
    return run_import(
        client, db_session, admin, options(lookup_contacts=True, **name_only(**overrides)),
        content=csv_bytes(NAME_ONLY_ROWS, NAME_ONLY_COLUMNS),
    )


def test_a_name_only_list_gets_phones_from_overture_where_the_match_is_certain(client, admin, options, db_session, overture_places):
    record = name_only_import(client, db_session, admin, options)

    assert record.status == "completed" and record.stats["looked_up"] == 1
    assert record.rows_to_import == 1 and record.skipped == {"no_contact": 3}
    kashif = db_session.query(Business).filter_by(name="Kashif Traders").one()
    assert {c.value for c in kashif.contact_points if c.kind == "phone"} == {"+923004309775"}
    assert kashif.website == "https://kashif.pk"
    assert kashif.geography.slug == "lahore"
    assert (record.stats["new"], record.stats["merged"], record.stats["with_phone"]) == (1, 0, 1)


def test_the_phone_is_credited_to_overture_and_the_lead_names_both_sources(client, admin, options, db_session, overture_places):
    name_only_import(client, db_session, admin, options)

    kashif = db_session.query(Business).filter_by(name="Kashif Traders").one()
    assert {c.source_key for c in kashif.contact_points} == {"overture"}
    assert {r.source_key for r in kashif.source_records} == {f"import:{LABEL}", "overture"}
    assert db_session.query(Business).count() == 1


def test_rows_without_a_match_can_still_be_kept_as_name_only_leads(client, admin, options, db_session, overture_places):
    record = name_only_import(client, db_session, admin, options, require_contact=False)

    assert record.rows_to_import == 4 and record.stats["looked_up"] == 1
    assert db_session.query(Business).count() == 4
    assert db_session.query(Business).filter_by(name="Malik Traders").one().contact_points == []


def test_rows_that_already_have_a_phone_are_not_looked_up(client, admin, options, db_session, overture_places):
    rows = [["Kashif Traders", "Lahore", "Johar Town, Lahore", "0300-1112223"]]
    record = run_import(
        client, db_session, admin,
        options(lookup_contacts=True, mapping=name_only(mapping={"name": "Company", "city": "City", "phones": ["Phone"]})["mapping"]),
        content=csv_bytes(rows, [*NAME_ONLY_COLUMNS, "Phone"]),
    )

    assert record.stats["looked_up"] == 0
    kashif = db_session.query(Business).filter_by(name="Kashif Traders").one()
    assert {c.value for c in kashif.contact_points} == {"+923001112223"} and kashif.website is None


def test_a_phone_that_is_on_do_not_contact_blocks_the_row_even_when_it_came_from_overture(client, admin, options, db_session, overture_places):
    client.post("/api/v1/compliance/do-not-contact", headers=admin, json={"phone": "0300-4309775"})

    record = name_only_import(client, db_session, admin, options)

    assert record.stats["blocked"] == 1 and record.stats["new"] == 0
    assert db_session.query(Business).count() == 0


def test_the_same_list_twice_adds_nothing_more(client, admin, options, db_session, overture_places):
    name_only_import(client, db_session, admin, options)
    record = name_only_import(client, db_session, admin, options)

    assert db_session.query(Business).count() == 1
    assert record.stats["new"] == 0 and record.stats["merged"] == 1


def test_a_second_list_naming_the_same_business_finds_it_already_known(client, admin, options, db_session, overture_places):
    name_only_import(client, db_session, admin, options)
    first = db_session.query(Business).count()
    record = name_only_import(client, db_session, admin, options, label=LABEL + " again")

    assert db_session.query(Business).count() == first and record.stats["new"] == 0 and record.stats["merged"] == 1


def test_the_lookup_needs_the_overture_data_and_says_so(client, admin, options, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "OVERTURE_DB_PATH", str(tmp_path / "missing.sqlite"))

    response = upload(client, admin, options(lookup_contacts=True, **name_only()), content=csv_bytes(NAME_ONLY_ROWS, NAME_ONLY_COLUMNS))

    assert response.status_code == 400 and "Overture" in response.json()["detail"] and "downloaded" in response.json()["detail"]
    assert db_session.query(Import).count() == 0


def test_a_name_only_file_is_refused_without_the_lookup_but_accepted_with_it(client, admin, options, overture_places):
    content = csv_bytes(NAME_ONLY_ROWS, NAME_ONLY_COLUMNS)

    refused = upload(client, admin, options(**name_only()), content=content)
    accepted = upload(client, admin, options(lookup_contacts=True, **name_only()), content=content)

    assert refused.status_code == 400 and "Overture" in refused.json()["detail"]
    assert accepted.status_code == 201 and accepted.json()["lookup_contacts"] is True and accepted.json()["stats"]["looked_up"] == 1


def test_without_the_lookup_nothing_is_changed(client, admin, options, db_session, overture_places):
    response = upload(client, admin, options())

    assert response.json()["lookup_contacts"] is False and response.json()["stats"]["looked_up"] == 0
