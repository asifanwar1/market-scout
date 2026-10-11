from datetime import UTC, datetime, timedelta

import pytest

from app.features.alerts import service
from app.features.alerts.models import Alert
from app.features.alerts.schemas import AlertSettingsUpdate, MarkReadRequest
from app.features.businesses.models import BusinessClassification, ContactPoint, SourceRecord
from app.features.insights.models import BusinessSnapshot
from app.features.runs.models import Run

BASE = "/api/v1/alerts"
LEADS = "/api/v1/businesses"


def moment(minutes=0):
    return datetime.now(UTC) + timedelta(minutes=minutes)


@pytest.fixture()
def admin(admin_user, auth_headers):
    return auth_headers(admin_user)


@pytest.fixture()
def sales(sales_user, auth_headers):
    return auth_headers(sales_user)


@pytest.fixture()
def run(db_session, seeded_profile):
    record = Run(
        profile_id=seeded_profile.id, profile_name=seeded_profile.name, status="completed", source_keys=["osm"],
        started_at=moment(-60), finished_at=moment(-1), stats={},
    )
    db_session.add(record)
    db_session.commit()
    return record


@pytest.fixture()
def found(db_session, seeded_profile, run, make_business):
    def _found(name="Solar Shop", score=90, new=True, **kwargs):
        lead = make_business(name, now=moment(-30) if new else moment(-60 * 24 * 3), **kwargs)
        db_session.query(SourceRecord).filter_by(business_id=lead.id).update({"run_id": run.id})
        db_session.query(BusinessClassification).filter_by(business_id=lead.id, profile_id=seeded_profile.id).update({"score": score})
        db_session.commit()
        return lead

    return _found


def alerts(db_session, kind=None):
    query = db_session.query(Alert)
    if kind:
        query = query.filter_by(kind=kind)
    return query.order_by(Alert.id).all()


def snapshot(db_session, lead, reviews, minutes, run_id=None):
    db_session.add(BusinessSnapshot(business_id=lead.id, run_id=run_id, seen_at=moment(minutes), rating=4.5, review_count=reviews))
    db_session.commit()


def test_settings_have_sensible_defaults_and_are_admin_only(client, admin, sales):
    assert client.get(f"{BASE}/settings", headers=sales).status_code == 403
    assert client.put(f"{BASE}/settings", headers=sales, json={}).status_code == 403
    assert client.get(f"{BASE}/settings").status_code == 401

    body = client.get(f"{BASE}/settings", headers=admin).json()
    assert body == {
        "new_lead_enabled": True, "new_lead_min_score": 70, "growing_enabled": True, "growing_min_new_reviews": 10,
        "growing_min_percent": 20, "reachable_enabled": True, "max_per_run": 50,
    }


def test_settings_change_one_value_at_a_time_and_reject_nonsense(client, admin):
    changed = client.put(f"{BASE}/settings", headers=admin, json={"new_lead_min_score": 55, "growing_enabled": False}).json()

    assert changed["new_lead_min_score"] == 55 and changed["growing_enabled"] is False and changed["max_per_run"] == 50
    assert client.get(f"{BASE}/settings", headers=admin).json() == changed
    for bad in ({"new_lead_min_score": 101}, {"growing_min_new_reviews": 0}, {"max_per_run": 0}, {"growing_min_percent": -1}):
        assert client.put(f"{BASE}/settings", headers=admin, json=bad).status_code == 422


def test_a_new_high_scoring_lead_raises_an_alert_and_a_weaker_one_does_not(db_session, run, found):
    strong = found("Strong Solar", score=85)
    found("Weak Solar", score=40)

    assert service.evaluate_run(db_session, run.id) == 1

    [alert] = alerts(db_session)
    assert alert.kind == "new_lead" and alert.business_id == strong.id and alert.run_id == run.id
    assert "Strong Solar" in alert.message and "score 85" in alert.message and "Lahore" in alert.message
    assert alert.user_id is None


def test_a_lead_that_was_already_known_is_not_a_new_lead(db_session, run, found):
    found("Old Friend", score=95, new=False)

    assert service.evaluate_run(db_session, run.id) == 0


def test_evaluating_a_run_twice_does_not_repeat_alerts(db_session, run, found):
    found("Strong Solar", score=85)

    assert service.evaluate_run(db_session, run.id) == 1
    assert service.evaluate_run(db_session, run.id) == 0
    assert len(alerts(db_session)) == 1


def test_an_alert_about_an_assigned_lead_goes_to_that_person(db_session, run, found, sales_user):
    lead = found("Strong Solar", score=85)
    lead.assigned_to_id = sales_user.id
    db_session.commit()

    service.evaluate_run(db_session, run.id)

    assert alerts(db_session)[0].user_id == sales_user.id


def test_only_the_best_alerts_are_kept_when_a_run_finds_too_many(db_session, run, found):
    for index, score in enumerate((72, 99, 80, 91)):
        found(f"Solar {index}", score=score)
    service.update_settings(db_session, AlertSettingsUpdate(max_per_run=2))

    assert service.evaluate_run(db_session, run.id) == 2

    assert sorted(alert.detail["score"] for alert in alerts(db_session)) == [91, 99]


def test_a_kind_of_alert_can_be_switched_off(db_session, run, found):
    found("Strong Solar", score=85)
    service.update_settings(db_session, AlertSettingsUpdate(new_lead_enabled=False))

    assert service.evaluate_run(db_session, run.id) == 0


def test_leads_on_the_do_not_contact_list_raise_no_alert(client, admin, db_session, run, found):
    lead = found("Strong Solar", score=85)
    client.post(f"{LEADS}/{lead.id}/do-not-contact", headers=admin, json={})

    assert service.evaluate_run(db_session, run.id) == 0


def test_a_run_that_has_not_started_raises_nothing(db_session, run, found):
    found("Strong Solar", score=85)
    run.status = "queued"
    db_session.commit()

    assert service.evaluate_run(db_session, run.id) == 0
    assert service.evaluate_run(db_session, 999999) == 0


def test_a_business_that_gained_many_reviews_since_the_last_run_raises_an_alert(db_session, run, found):
    lead = found("Busy Solar", score=60, new=False)
    snapshot(db_session, lead, 40, -60 * 24 * 2)
    snapshot(db_session, lead, 70, -30, run.id)

    assert service.evaluate_run(db_session, run.id) == 1

    [alert] = alerts(db_session)
    assert alert.kind == "growing" and alert.detail == {"previous": 40, "now": 70} and "gained 30 reviews" in alert.message
    assert alert.dedupe_key == "70"


def test_small_or_slow_growth_is_ignored(db_session, run, found):
    few = found("Few New", score=60, new=False)
    snapshot(db_session, few, 20, -60 * 24 * 2)
    snapshot(db_session, few, 25, -30, run.id)
    slow = found("Slow Climber", score=60, new=False)
    snapshot(db_session, slow, 500, -60 * 24 * 2)
    snapshot(db_session, slow, 530, -30, run.id)

    assert service.evaluate_run(db_session, run.id) == 0


def test_a_business_with_no_earlier_count_has_nothing_to_compare(db_session, run, found):
    lead = found("First Time", score=60, new=False)
    snapshot(db_session, lead, 300, -30, run.id)

    assert service.evaluate_run(db_session, run.id) == 0


def test_growth_alerts_follow_the_thresholds_and_come_again_only_for_a_new_count(db_session, run, found):
    lead = found("Busy Solar", score=60, new=False)
    snapshot(db_session, lead, 40, -60 * 24 * 2)
    snapshot(db_session, lead, 70, -30, run.id)
    service.update_settings(db_session, AlertSettingsUpdate(growing_min_new_reviews=50))
    assert service.evaluate_run(db_session, run.id) == 0

    service.update_settings(db_session, AlertSettingsUpdate(growing_min_new_reviews=10))
    assert service.evaluate_run(db_session, run.id) == 1
    assert service.evaluate_run(db_session, run.id) == 0

    later = Run(profile_id=run.profile_id, profile_name="p", status="completed", source_keys=["osm"], started_at=moment(10), stats={})
    db_session.add(later)
    db_session.commit()
    db_session.query(SourceRecord).filter_by(business_id=lead.id).update({"run_id": later.id})
    snapshot(db_session, lead, 120, 15, later.id)
    assert service.evaluate_run(db_session, later.id) == 1
    assert [alert.dedupe_key for alert in alerts(db_session, "growing")] == ["70", "120"]


def test_a_lead_that_gained_a_phone_during_the_run_is_newly_reachable(db_session, run, found):
    lead = found("Hidden Solar", score=60, new=False)
    db_session.add(ContactPoint(business_id=lead.id, kind="phone", value="+923001234567", source_key="osm", created_at=moment(-20)))
    db_session.commit()

    assert service.evaluate_run(db_session, run.id) == 1

    [alert] = alerts(db_session)
    assert alert.kind == "reachable" and alert.detail == {"gained": ["phone"]} and "Hidden Solar" in alert.message
    assert alert.dedupe_key == "reachable"


def test_a_lead_that_could_already_be_reached_is_not_newly_reachable(db_session, run, found):
    lead = found("Known Solar", score=60, new=False, phones=["03001112233"])
    db_session.query(ContactPoint).filter_by(business_id=lead.id).update({"created_at": moment(-60 * 24 * 3)})
    db_session.add(ContactPoint(business_id=lead.id, kind="email", value="hello@known.example", source_key="enrichment", created_at=moment(-20)))
    db_session.commit()

    assert service.evaluate_run(db_session, run.id) == 0


def test_a_website_alone_does_not_make_a_lead_reachable(db_session, run, found):
    lead = found("Social Solar", score=60, new=False)
    db_session.add(ContactPoint(business_id=lead.id, kind="facebook", value="facebook.com/social", source_key="enrichment", created_at=moment(-20)))
    db_session.commit()

    assert service.evaluate_run(db_session, run.id) == 0


def test_failing_to_work_out_alerts_never_breaks_the_run(db_session, run, monkeypatch):
    def explode(*_args):
        raise RuntimeError("boom")

    monkeypatch.setattr(service, "evaluate_run", explode)

    service.raise_alerts(db_session, run.id)


def test_old_alerts_are_cleared_after_three_months(db_session, run, found):
    lead = found("Old News", score=85)
    stale = Alert(kind="new_lead", business_id=lead.id, dedupe_key="old", message="old", detail={}, created_at=moment(-60 * 24 * (service.RETENTION_DAYS + 1)))
    fresh = Alert(kind="new_lead", business_id=lead.id, dedupe_key="fresh", message="fresh", detail={})
    db_session.add_all([stale, fresh])
    db_session.commit()

    assert service.prune(db_session) == 1
    assert [alert.dedupe_key for alert in alerts(db_session)] == ["fresh"]


def add_alert(db_session, lead, user_id=None, key="k", kind="new_lead"):
    alert = Alert(kind=kind, business_id=lead.id, user_id=user_id, dedupe_key=key, message=f"msg {key}", detail={"score": 80})
    db_session.add(alert)
    db_session.commit()
    return alert


def test_each_person_sees_shared_alerts_and_their_own_but_not_anyone_elses(client, admin, sales, db_session, make_business, sales_user, admin_user):
    lead = make_business("Shared Solar")
    add_alert(db_session, lead, None, "shared")
    add_alert(db_session, lead, sales_user.id, "mine")
    add_alert(db_session, lead, admin_user.id, "admins")

    mine = client.get(f"{BASE}/", headers=sales).json()
    theirs = client.get(f"{BASE}/", headers=admin).json()

    assert [a["message"] for a in mine["data"]] == ["msg mine", "msg shared"] and mine["count"] == 2 and mine["unread"] == 2
    assert [a["message"] for a in theirs["data"]] == ["msg admins", "msg shared"]
    assert mine["data"][0]["business_name"] == "Shared Solar" and mine["data"][0]["city"] == "Lahore"
    assert client.get(f"{BASE}/").status_code == 401


def test_marking_read_is_per_person_and_updates_the_unread_count(client, admin, sales, db_session, make_business):
    lead = make_business("Shared Solar")
    first, second = add_alert(db_session, lead, None, "one"), add_alert(db_session, lead, None, "two")

    assert client.get(f"{BASE}/summary", headers=sales).json() == {"unread": 2}
    after = client.post(f"{BASE}/mark-read", headers=sales, json={"ids": [first.id]}).json()

    assert after == {"unread": 1}
    assert client.get(f"{BASE}/summary", headers=admin).json() == {"unread": 2}
    listed = client.get(f"{BASE}/", headers=sales).json()
    assert {a["id"]: a["is_read"] for a in listed["data"]} == {first.id: True, second.id: False}
    assert [a["id"] for a in client.get(f"{BASE}/", headers=sales, params={"unread_only": True}).json()["data"]] == [second.id]

    assert client.post(f"{BASE}/mark-read", headers=sales, json={"ids": [first.id]}).json() == {"unread": 1}
    assert client.post(f"{BASE}/mark-read", headers=sales, json={"all": True}).json() == {"unread": 0}


def test_nobody_can_mark_someone_elses_alert_read(client, sales, admin, db_session, make_business, admin_user):
    lead = make_business("Private Solar")
    private = add_alert(db_session, lead, admin_user.id, "private")

    assert client.post(f"{BASE}/mark-read", headers=sales, json={"ids": [private.id]}).json() == {"unread": 0}
    assert client.get(f"{BASE}/summary", headers=admin).json() == {"unread": 1}


def test_the_list_can_be_filtered_by_kind_and_paged(client, sales, db_session, make_business):
    lead = make_business("Shared Solar")
    for index in range(3):
        add_alert(db_session, lead, None, f"n{index}")
    add_alert(db_session, lead, None, "g", kind="growing")

    growing = client.get(f"{BASE}/", headers=sales, params={"kind": "growing"}).json()
    page = client.get(f"{BASE}/", headers=sales, params={"limit": 2, "page": 2}).json()

    assert growing["count"] == 1 and growing["unread"] == 4
    assert page["count"] == 4 and len(page["data"]) == 2
    assert client.get(f"{BASE}/", headers=sales, params={"kind": "nope"}).status_code == 422


def test_alerts_about_leads_later_put_on_do_not_contact_disappear(client, admin, sales, db_session, make_business):
    lead = make_business("Shared Solar")
    add_alert(db_session, lead, None, "shared")
    assert client.get(f"{BASE}/summary", headers=sales).json() == {"unread": 1}

    client.post(f"{LEADS}/{lead.id}/do-not-contact", headers=admin, json={})

    assert client.get(f"{BASE}/summary", headers=sales).json() == {"unread": 0}
    assert client.get(f"{BASE}/", headers=sales).json()["data"] == []


def test_mark_read_service_counts_what_it_marked(db_session, make_business, sales_user):
    lead = make_business("Shared Solar")
    add_alert(db_session, lead, None, "a")
    add_alert(db_session, lead, None, "b")

    assert service.mark_read(db_session, sales_user.id, MarkReadRequest(all=True)) == 2
    assert service.mark_read(db_session, sales_user.id, MarkReadRequest(all=True)) == 0
    assert service.mark_read(db_session, sales_user.id, MarkReadRequest(ids=None)) == 0
