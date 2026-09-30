import pytest

from app.core.scouting.types import RawBusiness, SearchResult
from app.features.businesses.ingest import IngestContext, ingest_business
from app.features.businesses.models import Business, ContactPoint, SourceRecord
from app.features.compliance.models import DoNotContact
from app.features.runs import service as runs_service
from app.features.runs.schemas import RunCreate

DNC = "/api/v1/compliance/do-not-contact"
LEADS = "/api/v1/businesses"


@pytest.fixture()
def noor(make_business):
    return make_business(
        "Al Noor Solar", phones=["0300 4438424", "042 3577 1769"], emails=["info@alnoor.pk"], website="https://alnoor.pk",
    )


def block(client, headers, business, **body):
    return client.post(f"{LEADS}/{business.id}/do-not-contact", headers=headers, json=body)


# ---- blocking a business ---------------------------------------------------------------------

def test_anyone_can_record_a_stop_request_for_a_business(client, noor, sales_user, auth_headers, db_session):
    response = block(client, auth_headers(sales_user), noor, reason="Owner asked us to stop calling")

    assert response.status_code == 201
    entry = response.json()
    assert (entry["kind"], entry["value"], entry["business_id"]) == ("business", "Al Noor Solar", noor.id)
    assert entry["reason"] == "Owner asked us to stop calling" and entry["added_by_id"] == sales_user.id
    # Its phones and email are blocked along with it, so a re-scrape can't bring it back.
    assert entry["identifiers"] == ["+923004438424", "+924235771769", "info@alnoor.pk"]
    assert db_session.query(DoNotContact).count() == 4        # the business + 2 phones + 1 email


def test_blocking_twice_is_harmless_and_unknown_business_is_404(client, noor, sales_user, auth_headers, db_session):
    headers = auth_headers(sales_user)
    first = block(client, headers, noor).json()
    second = block(client, headers, noor)

    assert second.status_code == 201 and second.json()["id"] == first["id"]
    assert db_session.query(DoNotContact).count() == 4
    assert client.post(f"{LEADS}/9999/do-not-contact", headers=headers, json={}).status_code == 404


# ---- blocking a phone / email ----------------------------------------------------------------------

def test_block_a_phone_number_as_written_locally(client, sales_user, auth_headers):
    headers = auth_headers(sales_user)
    response = client.post(DNC, headers=headers, json={"phone": "0300-4438424", "reason": "Wrong number"})

    assert response.status_code == 201
    assert (response.json()["kind"], response.json()["value"]) == ("phone", "+923004438424")
    same_again = client.post(DNC, headers=headers, json={"phone": "+92 300 4438424"})
    assert same_again.json()["id"] == response.json()["id"]                 # normalised, so it's the same entry


def test_block_an_email_case_insensitively(client, sales_user, auth_headers):
    headers = auth_headers(sales_user)
    first = client.post(DNC, headers=headers, json={"email": "Info@AlNoor.PK"}).json()
    assert (first["kind"], first["value"]) == ("email", "info@alnoor.pk")
    assert client.post(DNC, headers=headers, json={"email": "info@alnoor.pk"}).json()["id"] == first["id"]


@pytest.mark.parametrize(
    "body, status",
    [
        ({"phone": "not a phone"}, 400),
        ({"phone": "0300 4438424, 0301 1112223"}, 400),       # one number at a time
        ({"email": "not-an-email"}, 422),
        ({"email": "logo@2x.png"}, 400),
        ({}, 422),
        ({"phone": "0300 4438424", "email": "a@b.pk"}, 422),
    ],
)
def test_block_validation(client, sales_user, auth_headers, body, status):
    assert client.post(DNC, headers=auth_headers(sales_user), json=body).status_code == status


# ---- the list ------------------------------------------------------------------------------------------

def test_list_shows_one_line_per_block_not_the_backing_rows(client, noor, make_business, sales_user, auth_headers):
    headers = auth_headers(sales_user)
    block(client, headers, noor, reason="stop")
    client.post(DNC, headers=headers, json={"phone": "0333 7654321"})
    client.post(DNC, headers=headers, json={"email": "spam@example.pk"})

    listing = client.get(DNC, headers=headers).json()

    assert listing["count"] == 3
    by_kind = {entry["kind"]: entry for entry in listing["data"]}
    assert by_kind["business"]["value"] == "Al Noor Solar" and len(by_kind["business"]["identifiers"]) == 3
    assert by_kind["phone"]["value"] == "+923337654321" and by_kind["phone"]["identifiers"] == []
    assert by_kind["email"]["value"] == "spam@example.pk"
    assert [entry["id"] for entry in listing["data"]] == sorted((e["id"] for e in listing["data"]), reverse=True)   # newest first


def test_list_search_and_pagination(client, noor, sales_user, auth_headers):
    headers = auth_headers(sales_user)
    block(client, headers, noor)
    client.post(DNC, headers=headers, json={"phone": "0333 7654321"})
    client.post(DNC, headers=headers, json={"email": "spam@example.pk"})

    assert [e["kind"] for e in client.get(f"{DNC}?search=noor", headers=headers).json()["data"]] == ["business"]
    assert [e["kind"] for e in client.get(f"{DNC}?search=7654321", headers=headers).json()["data"]] == ["phone"]
    assert [e["kind"] for e in client.get(f"{DNC}?search=spam", headers=headers).json()["data"]] == ["email"]
    page = client.get(f"{DNC}?limit=2&page=2", headers=headers).json()
    assert page["count"] == 3 and len(page["data"]) == 1


# ---- lifting a block ------------------------------------------------------------------------------------------

def test_only_an_admin_can_lift_a_block(client, noor, sales_user, admin_user, auth_headers):
    entry = block(client, auth_headers(sales_user), noor).json()

    assert client.delete(f"{DNC}/{entry['id']}", headers=auth_headers(sales_user)).status_code == 403
    assert client.delete(f"{DNC}/{entry['id']}").status_code == 401
    assert client.delete(f"{DNC}/{entry['id']}", headers=auth_headers(admin_user)).status_code == 204
    assert client.delete(f"{DNC}/{entry['id']}", headers=auth_headers(admin_user)).status_code == 404


def test_lifting_a_business_block_restores_it_completely(client, noor, sales_user, admin_user, auth_headers, db_session):
    entry = block(client, auth_headers(sales_user), noor).json()
    assert client.get(f"{LEADS}/{noor.id}", headers=auth_headers(sales_user)).status_code == 404

    client.delete(f"{DNC}/{entry['id']}", headers=auth_headers(admin_user))

    assert db_session.query(DoNotContact).count() == 0                     # the identifier rows went too
    assert client.get(f"{LEADS}/{noor.id}", headers=auth_headers(sales_user)).status_code == 200


def test_deleting_a_backing_identifier_row_lifts_the_whole_block(client, noor, sales_user, admin_user, auth_headers, db_session):
    block(client, auth_headers(sales_user), noor)
    phone_row = db_session.query(DoNotContact).filter(DoNotContact.phone == "+923004438424").one()

    assert client.delete(f"{DNC}/{phone_row.id}", headers=auth_headers(admin_user)).status_code == 204
    assert db_session.query(DoNotContact).count() == 0


def test_lifting_a_standalone_phone_block_only_affects_that_number(client, make_business, sales_user, admin_user, auth_headers):
    a = make_business("Alpha", phones=["0300 1111111"])
    b = make_business("Beta", phones=["0300 2222222"])
    headers = auth_headers(sales_user)
    first = client.post(DNC, headers=headers, json={"phone": "0300 1111111"}).json()
    client.post(DNC, headers=headers, json={"phone": "0300 2222222"})
    assert client.get(f"{LEADS}/", headers=headers).json()["count"] == 0

    client.delete(f"{DNC}/{first['id']}", headers=auth_headers(admin_user))
    assert [i["id"] for i in client.get(f"{LEADS}/", headers=headers).json()["data"]] == [a.id]
    assert b.id not in [i["id"] for i in client.get(f"{LEADS}/", headers=headers).json()["data"]]


def test_requires_authentication(client):
    assert client.get(DNC).status_code == 401
    assert client.post(DNC, json={"phone": "0300 4438424"}).status_code == 401


# ---- a re-scrape can't bring a blocked business back ---------------------------------------------------------------------

def context_for(seeded_profile, db_session, city="lahore"):
    from datetime import datetime, timezone
    from app.features.geographies.models import Geography
    from app.features.runs.service import _profile_scoring

    return IngestContext(
        run_id=None,
        geography_id=db_session.query(Geography).filter_by(slug=city).one().id,
        hint_segment_slug="dealer",
        now=datetime.now(timezone.utc),
        profile=_profile_scoring(seeded_profile),
    )


def raw(external_id="osm/1", name="Al Noor Solar", **overrides):
    data = dict(source_key="osm", external_id=external_id, name=name, latitude=31.5, longitude=74.3, phones=[], emails=[])
    data.update(overrides)
    return RawBusiness(**data)


def test_the_same_record_seen_again_is_refused_and_left_untouched(client, noor, sales_user, auth_headers, db_session, seeded_profile):
    block(client, auth_headers(sales_user), noor)
    contacts_before = db_session.query(ContactPoint).filter_by(business_id=noor.id).count()

    outcome = ingest_business(
        db_session,
        raw("osm/1", phones=["0311 9998887"], emails=["new@alnoor.pk"], website="https://new-site.pk"),
        context_for(seeded_profile, db_session),
    )
    db_session.commit()

    assert outcome.blocked is True and outcome.business is None and outcome.created is False
    db_session.refresh(noor)
    assert db_session.query(ContactPoint).filter_by(business_id=noor.id).count() == contacts_before   # no new contact stored
    assert noor.website == "https://alnoor.pk"


def test_a_new_record_with_a_blocked_phone_or_email_is_never_stored(client, sales_user, auth_headers, db_session, seeded_profile):
    headers = auth_headers(sales_user)
    client.post(DNC, headers=headers, json={"phone": "0300 4438424"})
    client.post(DNC, headers=headers, json={"email": "stop@shop.pk"})
    ctx = context_for(seeded_profile, db_session)

    by_phone = ingest_business(db_session, raw("osm/10", "Rebranded Shop", phones=["+92 300 4438424"]), ctx)
    by_email = ingest_business(db_session, raw("osm/11", "Another Name", latitude=32.0, emails=["Stop@Shop.pk"]), ctx)
    fine = ingest_business(db_session, raw("osm/12", "Innocent Shop", latitude=32.5, phones=["0301 1112223"]), ctx)
    db_session.commit()

    assert by_phone.blocked and by_email.blocked and not fine.blocked
    assert [b.name for b in db_session.query(Business)] == ["Innocent Shop"]
    assert db_session.query(SourceRecord).count() == 1


def test_a_business_found_through_a_different_source_is_still_recognised_as_blocked(client, noor, sales_user, auth_headers, db_session, seeded_profile):
    block(client, auth_headers(sales_user), noor)
    # Google Places lists the same shop with the same phone: matched to the blocked business, so refused.
    outcome = ingest_business(
        db_session,
        raw("ChIJ-1", "Al-Noor Solar", source_key="google_places", phones=["+92 300 4438424"], latitude=40.0, longitude=70.0),
        context_for(seeded_profile, db_session),
    )
    assert outcome.blocked
    assert db_session.query(SourceRecord).filter_by(source_key="google_places").count() == 0


def test_lifting_the_block_lets_the_business_be_updated_again(client, noor, sales_user, admin_user, auth_headers, db_session, seeded_profile):
    entry = block(client, auth_headers(sales_user), noor).json()
    client.delete(f"{DNC}/{entry['id']}", headers=auth_headers(admin_user))

    outcome = ingest_business(db_session, raw("osm/1", emails=["sales@alnoor.pk"]), context_for(seeded_profile, db_session))
    assert not outcome.blocked and outcome.business.id == noor.id
    assert db_session.query(ContactPoint).filter_by(business_id=noor.id, value="sales@alnoor.pk").count() == 1


class FakeSource:
    key = "osm"

    def __init__(self, businesses):
        self.businesses = businesses

    def search(self, query, max_requests=None):
        return SearchResult(list(self.businesses), requests_made=1)


def test_a_run_counts_refused_records_and_stores_none_of_them(client, noor, admin_user, sales_user, auth_headers, db_session, seeded_profile):
    block(client, auth_headers(sales_user), noor)
    from app.features.geographies.models import Geography

    lahore = db_session.query(Geography).filter_by(slug="lahore").one()
    run = runs_service.create_run(
        db_session,
        RunCreate(profile_id=seeded_profile.id, geography_ids=[lahore.id], source_keys=["osm"], segment_slugs=["dealer"], enrich_websites=False),
        created_by_id=admin_user.id,
    )
    source = FakeSource([raw("osm/1", phones=["0311 9998887"]), raw("osm/50", "Fresh Shop", latitude=32.0, phones=["0301 1112223"])])

    finished = runs_service.execute_run(db_session, run.id, source_builder=lambda db, keys: {"osm": source})

    stats = finished.stats["osm"]
    n_tasks = finished.tasks_done
    assert finished.status == "completed"
    assert stats["blocked"] == n_tasks                    # the blocked record, once per search
    assert stats["found"] == n_tasks and stats["new"] == 1     # only the fresh shop counts, and is stored once
    assert sorted(b.name for b in db_session.query(Business)) == ["Al Noor Solar", "Fresh Shop"]
    assert db_session.query(ContactPoint).filter_by(value="+923119998887").count() == 0
