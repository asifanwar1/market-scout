import pytest

from app.features.pipeline.models import LeadActivity, LeadOutcome, LeadTask

LEADS = "/api/v1/businesses"
PIPELINE = "/api/v1/pipeline"
TODAY = "2026-10-08"


@pytest.fixture()
def lead(make_business):
    return make_business("Al Noor Solar", phones=["0300 4438424"], emails=["info@alnoor.pk"])


@pytest.fixture()
def admin(admin_user, auth_headers):
    return auth_headers(admin_user)


@pytest.fixture()
def sales(sales_user, auth_headers):
    return auth_headers(sales_user)


def patch(client, headers, lead, **body):
    return client.patch(f"{LEADS}/{lead.id}", headers=headers, json=body)


def activities(client, headers, lead, **params):
    return client.get(f"{PIPELINE}/leads/{lead.id}/activities", headers=headers, params=params).json()


def kinds(client, headers, lead):
    return [item["kind"] for item in activities(client, headers, lead)["data"]]


def make_task(client, headers, lead, title="Call back", due="2026-10-10", **extra):
    return client.post(f"{PIPELINE}/leads/{lead.id}/tasks", headers=headers, json={"title": title, "due_on": due, **extra})


def test_the_pipeline_settings_tell_the_screens_which_currency_to_show(client, admin):
    assert client.get(f"{PIPELINE}/config", headers=admin).json() == {"deal_currency": "USD"}


def test_changing_the_status_logs_who_moved_it_from_where_to_where(client, lead, admin, admin_user):
    assert patch(client, admin, lead, lead_status="contacted").status_code == 200

    (entry,) = activities(client, admin, lead)["data"]

    assert entry["kind"] == "status_change" and (entry["from_value"], entry["to_value"]) == ("new", "contacted")
    assert entry["created_by"] == {"id": admin_user.id, "full_name": admin_user.full_name}


def test_saving_the_same_status_or_only_notes_logs_nothing(client, lead, admin):
    patch(client, admin, lead, lead_status="contacted")

    patch(client, admin, lead, lead_status="contacted")
    patch(client, admin, lead, notes="Spoke to the owner")

    assert kinds(client, admin, lead) == ["status_change"]


def test_assigning_and_unassigning_a_lead_is_logged_with_names(client, lead, admin, sales_user):
    patch(client, admin, lead, assigned_to_id=sales_user.id)
    patch(client, admin, lead, assigned_to_id=sales_user.id)
    patch(client, admin, lead, assigned_to_id=None)

    entries = activities(client, admin, lead)["data"]

    assert [(e["kind"], e["from_value"], e["to_value"]) for e in entries] == [
        ("assignment", sales_user.full_name, "Unassigned"),
        ("assignment", "Unassigned", sales_user.full_name),
    ]


def test_a_bulk_update_logs_only_the_leads_that_actually_changed(client, make_business, admin, sales_user):
    fresh, advanced, already = make_business("Fresh Solar"), make_business("Advanced Solar"), make_business("Already Solar")
    patch(client, admin, advanced, lead_status="interested")
    patch(client, admin, already, lead_status="contacted")

    response = client.post(
        f"{LEADS}/bulk-update", headers=admin,
        json={"business_ids": [fresh.id, advanced.id, already.id], "lead_status": "contacted", "assigned_to_id": sales_user.id},
    )

    def status_changes(item):
        return [(e["from_value"], e["to_value"]) for e in activities(client, admin, item)["data"] if e["kind"] == "status_change"]

    assert response.json() == {"updated": 3}
    assert status_changes(fresh) == [("new", "contacted")]
    assert status_changes(advanced) == [("interested", "contacted"), ("new", "interested")]
    assert status_changes(already) == [("new", "contacted")]
    assert all("assignment" in kinds(client, admin, item) for item in (fresh, advanced, already))


def test_a_note_or_call_can_be_logged_by_hand(client, lead, sales, sales_user):
    response = client.post(f"{PIPELINE}/leads/{lead.id}/activities", headers=sales, json={"kind": "call", "summary": "  Spoke to Noor, wants a quote  "})

    assert response.status_code == 201
    body = response.json()
    assert body["kind"] == "call" and body["summary"] == "Spoke to Noor, wants a quote"
    assert body["created_by"]["id"] == sales_user.id


@pytest.mark.parametrize("kind", ["note", "call", "whatsapp", "email", "meeting"])
def test_every_manual_kind_is_accepted(client, lead, admin, kind):
    assert client.post(f"{PIPELINE}/leads/{lead.id}/activities", headers=admin, json={"kind": kind, "summary": "x"}).status_code == 201


@pytest.mark.parametrize(
    "body",
    [{"kind": "status_change", "summary": "x"}, {"kind": "call", "summary": "   "}, {"kind": "call"}, {"summary": "x"}, {"kind": "call", "summary": "x", "extra": 1}],
)
def test_a_manual_entry_cannot_fake_a_system_event_or_be_empty(client, lead, admin, body):
    assert client.post(f"{PIPELINE}/leads/{lead.id}/activities", headers=admin, json=body).status_code == 422


def test_the_timeline_lists_the_newest_first_and_pages(client, lead, admin):
    for number in range(5):
        client.post(f"{PIPELINE}/leads/{lead.id}/activities", headers=admin, json={"kind": "note", "summary": f"note {number}"})

    page = activities(client, admin, lead, limit=2, page=2)

    assert page["count"] == 5 and [item["summary"] for item in page["data"]] == ["note 2", "note 1"]
    assert client.get(f"{PIPELINE}/leads/{lead.id}/activities", headers=admin, params={"limit": 0}).status_code == 422


def test_the_timeline_of_an_unknown_or_blocked_lead_is_not_found(client, lead, admin):
    assert client.get(f"{PIPELINE}/leads/999999/activities", headers=admin).status_code == 404
    client.post(f"{LEADS}/{lead.id}/do-not-contact", headers=admin, json={})

    assert client.get(f"{PIPELINE}/leads/{lead.id}/activities", headers=admin).status_code == 404
    assert client.post(f"{PIPELINE}/leads/{lead.id}/activities", headers=admin, json={"kind": "note", "summary": "x"}).status_code == 404
    assert make_task(client, admin, lead).status_code == 404


def test_a_lead_that_becomes_a_customer_records_the_deal(client, lead, admin, admin_user):
    response = patch(client, admin, lead, lead_status="customer", outcome={"value": 1500.5, "product": "Quote Pro", "note": "Annual plan"})

    outcome = response.json()["outcome"]
    assert response.status_code == 200
    assert (outcome["kind"], outcome["value"], outcome["product"], outcome["note"]) == ("won", 1500.5, "Quote Pro", "Annual plan")
    assert outcome["loss_reason"] is None and outcome["closed_by"]["id"] == admin_user.id and outcome["closed_at"]


def test_a_lost_lead_records_why(client, lead, admin):
    outcome = patch(client, admin, lead, lead_status="not_interested", outcome={"loss_reason": "price", "note": "Found it cheaper"}).json()["outcome"]

    assert (outcome["kind"], outcome["loss_reason"], outcome["note"]) == ("lost", "price", "Found it cheaper")
    assert outcome["value"] is None and outcome["product"] is None


def test_closing_a_lead_without_details_still_counts_as_won_or_lost(client, lead, make_business, admin):
    other = make_business("Other Solar")

    assert patch(client, admin, lead, lead_status="customer").json()["outcome"]["kind"] == "won"
    assert patch(client, admin, other, lead_status="not_interested").json()["outcome"]["loss_reason"] is None


def test_an_open_lead_has_no_outcome(client, lead, admin):
    assert client.get(f"{LEADS}/{lead.id}", headers=admin).json()["outcome"] is None


@pytest.mark.parametrize(
    ("status", "outcome"),
    [
        ("customer", {"loss_reason": "price"}),
        ("not_interested", {"value": 10}),
        ("not_interested", {"product": "Quote Pro"}),
        ("contacted", {"value": 10}),
        ("new", {"loss_reason": "price"}),
    ],
)
def test_details_that_do_not_fit_the_outcome_are_refused_and_nothing_changes(client, lead, admin, status, outcome):
    response = patch(client, admin, lead, lead_status=status, outcome=outcome)

    assert response.status_code == 400
    assert client.get(f"{LEADS}/{lead.id}", headers=admin).json()["lead_status"] == "new"
    assert activities(client, admin, lead)["count"] == 0


@pytest.mark.parametrize(
    "outcome", [{"value": -1}, {"value": "lots"}, {"loss_reason": "boredom"}, {"unknown": 1}, {"product": "x" * 500}, {"note": "x" * 5000}],
)
def test_invalid_outcome_fields_are_rejected(client, lead, admin, outcome):
    assert patch(client, admin, lead, lead_status="customer", outcome=outcome).status_code == 422


def test_outcome_details_can_be_corrected_without_changing_the_status(client, lead, admin):
    patch(client, admin, lead, lead_status="customer", outcome={"value": 100, "product": "Quote Pro"})

    response = patch(client, admin, lead, outcome={"value": 250})

    outcome = response.json()["outcome"]
    assert (outcome["value"], outcome["product"]) == (250, "Quote Pro")
    assert kinds(client, admin, lead) == ["outcome_updated", "status_change"]


def test_clearing_a_field_in_the_outcome_works(client, lead, admin):
    patch(client, admin, lead, lead_status="customer", outcome={"value": 100, "product": "Quote Pro"})

    outcome = patch(client, admin, lead, outcome={"product": "  "}).json()["outcome"]

    assert outcome["product"] is None and outcome["value"] == 100


def test_switching_from_won_to_lost_starts_the_outcome_over(client, lead, admin):
    patch(client, admin, lead, lead_status="customer", outcome={"value": 100, "product": "Quote Pro"})

    outcome = patch(client, admin, lead, lead_status="not_interested", outcome={"loss_reason": "competitor"}).json()["outcome"]

    assert (outcome["kind"], outcome["value"], outcome["product"], outcome["loss_reason"]) == ("lost", None, None, "competitor")


def test_reopening_a_closed_lead_removes_its_outcome_but_keeps_the_history(client, lead, admin, db_session):
    patch(client, admin, lead, lead_status="customer", outcome={"value": 100})

    reopened = patch(client, admin, lead, lead_status="interested").json()

    assert reopened["outcome"] is None and db_session.query(LeadOutcome).count() == 0
    assert kinds(client, admin, lead) == ["status_change", "status_change"]


def test_bulk_closing_gives_each_lead_a_blank_outcome(client, make_business, admin, db_session):
    leads = [make_business("A Solar"), make_business("B Solar")]

    client.post(f"{LEADS}/bulk-update", headers=admin, json={"business_ids": [item.id for item in leads], "lead_status": "not_interested"})

    assert sorted(row.kind for row in db_session.query(LeadOutcome)) == ["lost", "lost"]


def test_a_task_defaults_to_the_person_who_made_it(client, lead, sales, sales_user):
    response = make_task(client, sales, lead, "  Send the quote  ")

    body = response.json()
    assert response.status_code == 201
    assert body["title"] == "Send the quote" and body["due_on"] == "2026-10-10" and body["business_name"] == "Al Noor Solar"
    assert body["assigned_to"]["id"] == sales_user.id and body["completed_at"] is None


def test_a_task_can_be_given_to_someone_else_or_left_unassigned(client, lead, admin, sales_user):
    assert make_task(client, admin, lead, assigned_to_id=sales_user.id).json()["assigned_to"]["id"] == sales_user.id
    assert make_task(client, admin, lead, assigned_to_id=None).json()["assigned_to"] is None
    assert make_task(client, admin, lead, assigned_to_id=999999).status_code == 400


@pytest.mark.parametrize(
    "body",
    [{"title": "x"}, {"due_on": "2026-10-10"}, {"title": "  ", "due_on": "2026-10-10"}, {"title": "x", "due_on": "tomorrow"}, {"title": "x" * 500, "due_on": "2026-10-10"}],
)
def test_a_task_needs_a_title_and_a_due_date(client, lead, admin, body):
    assert client.post(f"{PIPELINE}/leads/{lead.id}/tasks", headers=admin, json=body).status_code == 422


@pytest.fixture()
def tasks(client, lead, admin, sales, admin_user, sales_user):
    return {
        "overdue": make_task(client, admin, lead, "Overdue", "2026-10-07", assigned_to_id=admin_user.id).json(),
        "today": make_task(client, admin, lead, "Today", TODAY, assigned_to_id=sales_user.id).json(),
        "upcoming": make_task(client, admin, lead, "Upcoming", "2026-10-12", assigned_to_id=admin_user.id).json(),
        "later": make_task(client, admin, lead, "Later", "2026-10-20", assigned_to_id=sales_user.id).json(),
    }


def titles(client, headers, **params):
    return [task["title"] for task in client.get(f"{PIPELINE}/tasks", headers=headers, params={"today": TODAY, **params}).json()["data"]]


def test_tasks_are_listed_by_when_they_are_due(client, tasks, admin):
    assert titles(client, admin) == ["Overdue", "Today", "Upcoming", "Later"]
    assert titles(client, admin, scope="overdue") == ["Overdue"]
    assert titles(client, admin, scope="today") == ["Today"]
    assert titles(client, admin, scope="upcoming") == ["Upcoming", "Later"]


def test_only_my_tasks_can_be_shown(client, tasks, sales):
    assert titles(client, sales, mine="true") == ["Today", "Later"]


def test_tasks_can_be_filtered_to_one_lead(client, tasks, make_business, admin):
    other = make_business("Other Solar")
    make_task(client, admin, other, "Other task")

    assert titles(client, admin, business_id=other.id) == ["Other task"]


def test_the_summary_counts_what_needs_attention(client, tasks, admin, sales):
    everyone = client.get(f"{PIPELINE}/tasks/summary", headers=admin, params={"today": TODAY, "mine": "false"}).json()
    mine = client.get(f"{PIPELINE}/tasks/summary", headers=sales, params={"today": TODAY}).json()

    assert everyone == {"overdue": 1, "due_today": 1, "open": 4}
    assert mine == {"overdue": 0, "due_today": 1, "open": 2}


def test_an_empty_summary_is_all_zeros(client, admin):
    assert client.get(f"{PIPELINE}/tasks/summary", headers=admin).json() == {"overdue": 0, "due_today": 0, "open": 0}


def test_completing_a_task_moves_it_to_done_and_logs_it_once(client, tasks, lead, admin):
    task_id = tasks["today"]["id"]

    first = client.patch(f"{PIPELINE}/tasks/{task_id}", headers=admin, json={"done": True})
    client.patch(f"{PIPELINE}/tasks/{task_id}", headers=admin, json={"done": True})

    assert first.json()["completed_at"]
    assert "Today" not in titles(client, admin) and titles(client, admin, scope="done") == ["Today"]
    entries = [e for e in activities(client, admin, lead)["data"] if e["kind"] == "task_completed"]
    assert len(entries) == 1 and entries[0]["summary"] == "Today"


def test_a_completed_task_can_be_reopened(client, tasks, admin):
    task_id = tasks["today"]["id"]
    client.patch(f"{PIPELINE}/tasks/{task_id}", headers=admin, json={"done": True})

    reopened = client.patch(f"{PIPELINE}/tasks/{task_id}", headers=admin, json={"done": False}).json()

    assert reopened["completed_at"] is None and "Today" in titles(client, admin)


def test_a_task_can_be_rescheduled_renamed_and_reassigned(client, tasks, admin, sales_user):
    task_id = tasks["overdue"]["id"]

    body = client.patch(
        f"{PIPELINE}/tasks/{task_id}", headers=admin,
        json={"title": "  Chase payment ", "due_on": "2026-10-30", "assigned_to_id": sales_user.id},
    ).json()

    assert (body["title"], body["due_on"], body["assigned_to"]["id"]) == ("Chase payment", "2026-10-30", sales_user.id)
    assert client.patch(f"{PIPELINE}/tasks/{task_id}", headers=admin, json={"assigned_to_id": None}).json()["assigned_to"] is None


@pytest.mark.parametrize(
    ("body", "status"),
    [({}, 400), ({"title": None}, 400), ({"due_on": None}, 400), ({"done": None}, 400), ({"assigned_to_id": 999999}, 400), ({"title": ""}, 422), ({"extra": 1}, 422)],
)
def test_task_updates_that_make_no_sense_are_refused(client, tasks, admin, body, status):
    assert client.patch(f"{PIPELINE}/tasks/{tasks['today']['id']}", headers=admin, json=body).status_code == status


def test_a_task_can_be_deleted(client, tasks, admin):
    task_id = tasks["today"]["id"]

    assert client.delete(f"{PIPELINE}/tasks/{task_id}", headers=admin).status_code == 204
    assert client.delete(f"{PIPELINE}/tasks/{task_id}", headers=admin).status_code == 404
    assert client.patch(f"{PIPELINE}/tasks/{task_id}", headers=admin, json={"done": True}).status_code == 404


def test_tasks_of_a_do_not_contact_lead_disappear(client, tasks, lead, admin):
    client.post(f"{LEADS}/{lead.id}/do-not-contact", headers=admin, json={})

    assert titles(client, admin) == []
    assert client.get(f"{PIPELINE}/tasks/summary", headers=admin, params={"mine": "false"}).json()["open"] == 0
    assert client.patch(f"{PIPELINE}/tasks/{tasks['today']['id']}", headers=admin, json={"done": True}).status_code == 404


def test_removing_a_lead_removes_its_history_tasks_and_outcome(client, lead, admin, db_session):
    patch(client, admin, lead, lead_status="customer", outcome={"value": 5})
    make_task(client, admin, lead)

    assert client.delete(f"{LEADS}/{lead.id}", headers=admin).status_code == 204
    db_session.expire_all()

    assert db_session.query(LeadActivity).count() == db_session.query(LeadTask).count() == db_session.query(LeadOutcome).count() == 0


def test_an_unknown_task_scope_is_rejected(client, admin):
    assert client.get(f"{PIPELINE}/tasks", headers=admin, params={"scope": "someday"}).status_code == 422
