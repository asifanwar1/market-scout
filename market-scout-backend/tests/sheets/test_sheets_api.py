from contextlib import contextmanager

import pytest

from app.config import settings
from app.features.exports.service import LEAD_HEADERS
from app.features.sheets import service as sheets_service
from app.features.sheets.models import AppSetting
from tests.sheets.conftest import CLIENT_EMAIL, SPREADSHEET_ID

BASE = "/api/v1/sheets"
LEADS = "/api/v1/businesses"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit#gid=0"
NAME = LEAD_HEADERS.index("Name")


@pytest.fixture(autouse=True)
def _clean_module_state():
    sheets_service._pending_timer = None
    yield
    sheets_service._pending_timer = None
    if sheets_service._sync_lock.locked():
        sheets_service._sync_lock.release()


@pytest.fixture()
def fake(monkeypatch, db_session, make_client, fake_google):
    """Sheets calls go to the in-memory Google; background work runs inline on the test's session."""
    monkeypatch.setattr(sheets_service, "_build_client", make_client)
    monkeypatch.setattr(sheets_service, "_launch", lambda target: target())

    @contextmanager
    def session(write=False):
        yield db_session

    monkeypatch.setattr(sheets_service, "_session", session)
    return fake_google


@pytest.fixture()
def admin(admin_user, auth_headers):
    return auth_headers(admin_user)


@pytest.fixture()
def connected(client, admin, fake, service_account_json):
    response = client.put(f"{BASE}/", headers=admin, json={"credentials_json": service_account_json, "spreadsheet": SHEET_URL})
    assert response.status_code == 200, response.text
    return fake


@pytest.fixture()
def leads(make_business):
    return {
        "noor": make_business("Al Noor Solar Dealer", phones=["0300 4438424"], emails=["info@alnoor.pk"], website="https://alnoor.pk"),
        "bilal": make_business("Bilal Wholesale Traders", hint="wholesaler", phones=["0301 1112223"]),
        "quetta": make_business("Quetta Solar Works", city="quetta", hint="installer", emails=["hello@quettasolar.pk"]),
    }


def sheet_names(fake) -> list[str]:
    return [row[NAME] for row in fake.table(SPREADSHEET_ID, "Leads")[1:]]


# ---- access ---------------------------------------------------------------------------------------

def test_only_admins_can_use_the_sheets_settings(client, sales_user, auth_headers):
    sales = auth_headers(sales_user)
    assert client.get(f"{BASE}/").status_code == 401
    for call in (
        lambda: client.get(f"{BASE}/", headers=sales),
        lambda: client.put(f"{BASE}/", headers=sales, json={"auto_sync": False}),
        lambda: client.post(f"{BASE}/test", headers=sales),
        lambda: client.post(f"{BASE}/sync", headers=sales),
    ):
        assert call().status_code == 403


# ---- settings -----------------------------------------------------------------------------------------

def test_starts_unconfigured(client, admin):
    body = client.get(f"{BASE}/", headers=admin).json()
    assert body["has_credentials"] is False and body["is_configured"] is False
    assert body["spreadsheet_id"] is None and body["worksheet_title"] == "Leads"
    assert body["auto_sync"] is True and body["is_syncing"] is False
    assert body["last_synced_at"] is None and body["last_sync_ok"] is None


def test_saving_the_key_shows_the_address_to_share_with_but_never_the_key(client, admin, service_account_json):
    response = client.put(f"{BASE}/", headers=admin, json={"credentials_json": service_account_json})

    body = response.json()
    assert body["has_credentials"] is True and body["credentials_source"] == "saved"
    assert body["service_account_email"] == CLIENT_EMAIL
    assert "PRIVATE KEY" not in response.text
    assert body["is_configured"] is False  # still needs the sheet


def test_the_key_is_stored_encrypted(client, admin, service_account_json, db_session):
    client.put(f"{BASE}/", headers=admin, json={"credentials_json": service_account_json})

    stored = db_session.get(AppSetting, "sheets_credentials").value["encrypted"]
    assert "PRIVATE KEY" not in stored and CLIENT_EMAIL not in stored


def test_a_bad_key_is_rejected_and_saves_nothing(client, admin):
    response = client.put(
        f"{BASE}/", headers=admin, json={"credentials_json": '{"type": "authorized_user"}', "spreadsheet": SHEET_URL}
    )
    assert response.status_code == 400 and "not a service-account key" in response.json()["detail"]

    body = client.get(f"{BASE}/", headers=admin).json()
    assert body["has_credentials"] is False and body["spreadsheet_id"] is None  # the sheet wasn't half-saved either


@pytest.mark.parametrize(
    "value", [SHEET_URL, f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}", SPREADSHEET_ID, f"  {SPREADSHEET_ID}  "]
)
def test_accepts_the_sheets_link_or_bare_id(client, admin, value):
    body = client.put(f"{BASE}/", headers=admin, json={"spreadsheet": value}).json()
    assert body["spreadsheet_id"] == SPREADSHEET_ID
    assert body["spreadsheet_url"] == f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}"


@pytest.mark.parametrize("value", ["hello", "https://example.com/page", "12345", "../../etc/passwd"])
def test_rejects_things_that_are_not_a_sheet(client, admin, value):
    assert client.put(f"{BASE}/", headers=admin, json={"spreadsheet": value}).status_code == 400


def test_an_empty_link_disconnects_the_sheet(client, admin):
    client.put(f"{BASE}/", headers=admin, json={"spreadsheet": SPREADSHEET_ID})
    body = client.put(f"{BASE}/", headers=admin, json={"spreadsheet": ""}).json()
    assert body["spreadsheet_id"] is None


def test_auto_sync_can_be_switched_off_and_on(client, admin):
    assert client.put(f"{BASE}/", headers=admin, json={"auto_sync": False}).json()["auto_sync"] is False
    assert client.put(f"{BASE}/", headers=admin, json={"auto_sync": True}).json()["auto_sync"] is True


def test_the_saved_key_can_be_removed(client, admin, service_account_json):
    client.put(f"{BASE}/", headers=admin, json={"credentials_json": service_account_json})
    body = client.put(f"{BASE}/", headers=admin, json={"clear_credentials": True}).json()
    assert body["has_credentials"] is False and body["service_account_email"] is None


def test_a_key_from_the_environment_is_used_when_none_is_saved(client, admin, service_account_json, monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_SERVICE_ACCOUNT_JSON", service_account_json)
    body = client.get(f"{BASE}/", headers=admin).json()
    assert body["has_credentials"] is True and body["credentials_source"] == "environment"


def test_a_broken_environment_key_is_ignored_not_fatal(client, admin, monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_SERVICE_ACCOUNT_JSON", "{oops")
    body = client.get(f"{BASE}/", headers=admin).json()
    assert body["has_credentials"] is False


def test_a_saved_key_that_can_no_longer_be_decrypted_asks_to_be_entered_again(client, admin, db_session):
    db_session.add(AppSetting(key="sheets_credentials", value={"encrypted": "not-a-valid-token"}))
    db_session.commit()
    body = client.get(f"{BASE}/", headers=admin).json()
    assert body["has_credentials"] is False and body["credentials_needs_reentry"] is True


def test_switching_to_a_different_sheet_forgets_the_old_outcome(client, admin, connected, leads):
    client.post(f"{BASE}/sync", headers=admin)
    assert client.get(f"{BASE}/", headers=admin).json()["last_sync_ok"] is True

    body = client.put(f"{BASE}/", headers=admin, json={"spreadsheet": "1AnotherSheetIdentifier0000000000000000"}).json()
    assert body["last_sync_ok"] is None and body["last_synced_at"] is None and body["last_row_count"] is None


# ---- testing the connection ------------------------------------------------------------------------

def test_test_connection_needs_the_key_and_the_sheet_first(client, admin, service_account_json):
    assert client.post(f"{BASE}/test", headers=admin).status_code == 400
    client.put(f"{BASE}/", headers=admin, json={"credentials_json": service_account_json})
    response = client.post(f"{BASE}/test", headers=admin)
    assert response.status_code == 400 and "link of the Google Sheet" in response.json()["detail"]


def test_test_connection_succeeds_and_remembers_the_title(client, admin, connected):
    result = client.post(f"{BASE}/test", headers=admin).json()
    assert result == {"ok": True, "message": 'Connected. Found the spreadsheet "Sales leads".'}
    assert client.get(f"{BASE}/", headers=admin).json()["spreadsheet_title"] == "Sales leads"


def test_test_connection_tells_you_to_share_the_sheet(client, admin, connected):
    connected.forbidden.add(SPREADSHEET_ID)
    result = client.post(f"{BASE}/test", headers=admin).json()
    assert result["ok"] is False and CLIENT_EMAIL in result["message"]


# ---- syncing ------------------------------------------------------------------------------------------------

def test_sync_needs_a_configured_sheet(client, admin):
    assert client.post(f"{BASE}/sync", headers=admin).status_code == 400


def test_sync_writes_every_lead_and_records_the_outcome(client, admin, connected, leads):
    response = client.post(f"{BASE}/sync", headers=admin)
    assert response.status_code == 202

    body = client.get(f"{BASE}/", headers=admin).json()
    assert body["last_sync_ok"] is True and body["last_error"] is None
    assert body["last_row_count"] == 3 and body["last_synced_at"] is not None
    assert body["is_syncing"] is False

    table = connected.table(SPREADSHEET_ID, "Leads")
    assert table[0] == LEAD_HEADERS
    assert sorted(sheet_names(connected)) == ["Al Noor Solar Dealer", "Bilal Wholesale Traders", "Quetta Solar Works"]


def test_the_sheet_is_the_same_data_as_the_csv_export(client, admin, connected, leads):
    client.post(f"{BASE}/sync", headers=admin)
    csv_rows = client.get("/api/v1/exports/leads.csv", headers=admin).content.decode("utf-8-sig").splitlines()
    assert len(csv_rows) - 1 == len(connected.table(SPREADSHEET_ID, "Leads")) - 1


def test_running_it_twice_gives_the_same_sheet(client, admin, connected, leads):
    client.post(f"{BASE}/sync", headers=admin)
    first = connected.table(SPREADSHEET_ID, "Leads")
    client.post(f"{BASE}/sync", headers=admin)
    assert connected.table(SPREADSHEET_ID, "Leads") == first


def test_highest_scoring_leads_come_first(client, admin, connected, leads):
    client.post(f"{BASE}/sync", headers=admin)
    scores = [row[LEAD_HEADERS.index("Score")] for row in connected.table(SPREADSHEET_ID, "Leads")[1:]]
    assert scores == sorted(scores, reverse=True)


def test_someone_on_do_not_contact_never_reaches_the_sheet(client, admin, connected, leads):
    client.post(f"{LEADS}/{leads['noor'].id}/do-not-contact", headers=admin, json={})
    client.post("/api/v1/compliance/do-not-contact", headers=admin, json={"phone": "0301 1112223"})

    client.post(f"{BASE}/sync", headers=admin)

    assert sheet_names(connected) == ["Quetta Solar Works"]
    flat = " ".join(str(cell) for row in connected.table(SPREADSHEET_ID, "Leads") for cell in row)
    assert "+923004438424" not in flat and "info@alnoor.pk" not in flat and "+923011112223" not in flat


def test_a_lead_blocked_after_a_sync_disappears_on_the_next(client, admin, connected, leads):
    client.post(f"{BASE}/sync", headers=admin)
    assert "Al Noor Solar Dealer" in sheet_names(connected)

    client.post(f"{LEADS}/{leads['noor'].id}/do-not-contact", headers=admin, json={})
    client.post(f"{BASE}/sync", headers=admin)

    assert "Al Noor Solar Dealer" not in sheet_names(connected)
    assert len(connected.table(SPREADSHEET_ID, "Leads")) == 3  # header + the other two, no stale row left


def test_a_failed_sync_records_why_and_the_next_good_one_clears_it(client, admin, connected, leads):
    connected.forbidden.add(SPREADSHEET_ID)
    assert client.post(f"{BASE}/sync", headers=admin).status_code == 202

    failed = client.get(f"{BASE}/", headers=admin).json()
    assert failed["last_sync_ok"] is False and CLIENT_EMAIL in failed["last_error"]
    assert failed["last_synced_at"] is None

    connected.forbidden.clear()
    client.post(f"{BASE}/sync", headers=admin)
    fixed = client.get(f"{BASE}/", headers=admin).json()
    assert fixed["last_sync_ok"] is True and fixed["last_error"] is None


def test_an_unexpected_crash_is_recorded_without_leaking_details(client, admin, connected, leads, monkeypatch):
    def boom(*_args, **_kwargs):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(sheets_service.exports_service, "iter_lead_rows", boom)
    client.post(f"{BASE}/sync", headers=admin)

    body = client.get(f"{BASE}/", headers=admin).json()
    assert body["last_sync_ok"] is False
    assert "secret internal detail" not in (body["last_error"] or "")
    assert "server log" in body["last_error"]


def test_only_one_sync_runs_at_a_time(client, admin, connected):
    assert sheets_service._sync_lock.acquire(blocking=False)
    try:
        assert client.get(f"{BASE}/", headers=admin).json()["is_syncing"] is True
        response = client.post(f"{BASE}/sync", headers=admin)
        assert response.status_code == 409 and "already running" in response.json()["detail"]
    finally:
        sheets_service._sync_lock.release()


def test_the_lock_is_released_even_if_starting_the_sync_fails(client, admin, connected, monkeypatch):
    def cannot_start(_target):
        raise RuntimeError("no threads left")

    monkeypatch.setattr(sheets_service, "_launch", cannot_start)
    with pytest.raises(RuntimeError):
        client.post(f"{BASE}/sync", headers=admin)
    assert sheets_service._sync_lock.locked() is False


def test_refuses_a_worksheet_that_already_holds_other_data(client, admin, connected, leads):
    theirs = [["Customer", "Owes"], ["Ali", 500]]
    connected.add_spreadsheet(SPREADSHEET_ID, worksheets={"Leads": theirs})

    client.post(f"{BASE}/sync", headers=admin)

    assert connected.table(SPREADSHEET_ID, "Leads") == theirs
    assert "already exists" in client.get(f"{BASE}/", headers=admin).json()["last_error"]


# ---- keeping it live (automatic refresh) ------------------------------------------------------------

def test_an_unchanged_sheet_is_not_rewritten_by_the_automatic_refresh(client, admin, connected, leads, db_session):
    client.post(f"{BASE}/sync", headers=admin)
    calls_after_first = len(connected.calls)

    sheets_service.sync_now(db_session, force=False)

    assert len(connected.calls) == calls_after_first  # not even a request to Google


def test_a_manual_sync_always_rewrites_even_if_nothing_changed(client, admin, connected, leads):
    client.post(f"{BASE}/sync", headers=admin)
    calls_after_first = len(connected.calls)
    client.post(f"{BASE}/sync", headers=admin)
    assert len(connected.calls) > calls_after_first  # e.g. someone emptied the sheet by hand and wants it back


def test_the_automatic_refresh_picks_up_edits_made_in_the_app(client, admin, connected, leads, db_session):
    client.post(f"{BASE}/sync", headers=admin)
    client.patch(f"{LEADS}/{leads['noor'].id}", headers=admin, json={"lead_status": "quoted", "notes": "Sent quote #14"})

    sheets_service.sync_now(db_session, force=False)

    noor = next(row for row in connected.table(SPREADSHEET_ID, "Leads")[1:] if row[NAME] == "Al Noor Solar Dealer")
    assert noor[LEAD_HEADERS.index("Status")] == "Quoted"
    assert noor[LEAD_HEADERS.index("Notes")] == "Sent quote #14"


def test_do_not_contact_reaches_the_sheet_through_the_automatic_refresh(client, admin, connected, leads, db_session):
    client.post(f"{BASE}/sync", headers=admin)
    client.post(f"{LEADS}/{leads['bilal'].id}/do-not-contact", headers=admin, json={})

    sheets_service._auto_sync()

    assert "Bilal Wholesale Traders" not in sheet_names(connected)


def test_automatic_refresh_does_nothing_when_switched_off(client, admin, connected, leads):
    client.put(f"{BASE}/", headers=admin, json={"auto_sync": False})
    connected.calls.clear()

    sheets_service._auto_sync()

    assert connected.calls == []


def test_automatic_refresh_does_nothing_without_a_sheet(client, admin, fake):
    sheets_service._auto_sync()
    assert fake.calls == []


def test_a_burst_of_changes_schedules_one_refresh(monkeypatch):
    scheduled = []
    monkeypatch.setattr(settings, "SHEETS_AUTO_SYNC_DELAY_SECONDS", 20.0)
    monkeypatch.setattr(sheets_service, "_schedule", lambda delay, target: scheduled.append((delay, target)) or object())

    for _ in range(5):
        sheets_service.notify_changed()

    assert len(scheduled) == 1 and scheduled[0][0] == 20.0


def test_a_change_after_the_refresh_starts_schedules_the_next_one(monkeypatch, client, admin, fake):
    scheduled = []
    monkeypatch.setattr(settings, "SHEETS_AUTO_SYNC_DELAY_SECONDS", 20.0)
    monkeypatch.setattr(sheets_service, "_schedule", lambda delay, target: scheduled.append(target) or object())

    sheets_service.notify_changed()
    scheduled[0]()          # the timer fires
    sheets_service.notify_changed()

    assert len(scheduled) == 2


def test_a_negative_delay_turns_the_automatic_refresh_off(monkeypatch):
    scheduled = []
    monkeypatch.setattr(settings, "SHEETS_AUTO_SYNC_DELAY_SECONDS", -1.0)
    monkeypatch.setattr(sheets_service, "_schedule", lambda *args: scheduled.append(args))
    sheets_service.notify_changed()
    assert scheduled == []


def test_notify_never_raises_even_if_scheduling_fails(monkeypatch):
    def broken(*_args):
        raise RuntimeError("can't start new thread")

    monkeypatch.setattr(settings, "SHEETS_AUTO_SYNC_DELAY_SECONDS", 20.0)
    monkeypatch.setattr(sheets_service, "_schedule", broken)
    sheets_service.notify_changed()  # must not propagate into a request or a run


@pytest.fixture()
def notified(monkeypatch):
    calls = []
    monkeypatch.setattr(sheets_service, "notify_changed", lambda: calls.append(1))
    return calls


def test_every_change_to_a_lead_asks_for_a_refresh(client, admin, leads, notified):
    client.patch(f"{LEADS}/{leads['noor'].id}", headers=admin, json={"notes": "x"})
    client.post(f"{LEADS}/bulk-update", headers=admin, json={"business_ids": [leads["noor"].id], "lead_status": "contacted"})
    assert len(notified) == 2


def test_every_do_not_contact_change_asks_for_a_refresh(client, admin, leads, notified):
    client.post(f"{LEADS}/{leads['noor'].id}/do-not-contact", headers=admin, json={})
    entry = client.post("/api/v1/compliance/do-not-contact", headers=admin, json={"phone": "0301 1112223"}).json()
    client.delete(f"/api/v1/compliance/do-not-contact/{entry['id']}", headers=admin)
    assert len(notified) == 3


def test_a_failed_edit_does_not_ask_for_a_refresh(client, admin, notified):
    assert client.patch(f"{LEADS}/99999", headers=admin, json={"notes": "x"}).status_code == 404
    assert notified == []


def test_a_finished_run_asks_for_a_refresh(monkeypatch, notified):
    from app.features.runs import service as runs_service

    monkeypatch.setattr(runs_service, "execute_run", lambda db, run_id: None)
    runs_service.run_in_new_session(1)
    assert len(notified) == 1
