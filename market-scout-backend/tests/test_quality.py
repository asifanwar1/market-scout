from datetime import UTC, date, datetime, timedelta

import pytest

from app.core.scouting.enrichment.website import SiteProbe
from app.core.scouting.verify import EmailCheck
from app.features.businesses.models import Business, BusinessClassification, ContactPoint, SourceRecord
from app.features.compliance.models import DoNotContact
from app.features.jobs.models import Job
from app.features.pipeline.models import LeadActivity, LeadOutcome, LeadTask
from app.features.profiles.schemas import ScoringConfig
from app.features.quality import duplicates, service
from app.features.quality.models import DuplicateCandidate, QualityTask
from app.features.quality.schemas import CheckRequest, QualitySettingsUpdate
from app.features.runs.models import Run

BASE = "/api/v1/quality"
LEADS = "/api/v1/businesses"


@pytest.fixture()
def admin(admin_user, auth_headers):
    return auth_headers(admin_user)


@pytest.fixture()
def sales(sales_user, auth_headers):
    return auth_headers(sales_user)


class FakeMail:
    def __init__(self, verdicts=None):
        self.verdicts = verdicts or {}
        self.asked = []

    def check(self, email):
        self.asked.append(email)
        return self.verdicts.get(email.rpartition("@")[2], EmailCheck(True, "ok"))


class FakeSites:
    def __init__(self, verdicts=None):
        self.verdicts = verdicts or {}
        self.asked = []

    def probe(self, url):
        self.asked.append(url)
        return self.verdicts.get(url, SiteProbe(True, "The website answers"))


def check_leads(db_session, leads, mail=None, sites=None, refresh=False, user_id=None):
    task = service.start_checks(db_session, CheckRequest(business_ids=[lead.id for lead in leads], refresh=refresh), user_id or 1)
    service.run_task(db_session, task.id, mail_factory=lambda: mail or FakeMail(), enricher_factory=lambda: sites or FakeSites())
    db_session.refresh(task)
    return task


def contact(db_session, lead, kind):
    return db_session.query(ContactPoint).filter_by(business_id=lead.id, kind=kind).one()


def score_of(db_session, lead, profile):
    return db_session.query(BusinessClassification.score).filter_by(business_id=lead.id, profile_id=profile.id).scalar()


def test_a_working_email_and_website_are_marked_ok(db_session, make_business, admin_user):
    lead = make_business("Solar Shop", emails=["info@shop.pk"], website="https://shop.pk")

    task = check_leads(db_session, [lead], user_id=admin_user.id)

    assert task.status == "completed" and task.done == 1 and task.counts["emails_ok"] == 1 and task.counts["websites_ok"] == 1
    email = contact(db_session, lead, "email")
    assert email.check_status == "ok" and email.checked_at is not None
    db_session.refresh(lead)
    assert lead.website_status == "ok" and lead.website_check_note


def test_an_email_that_cannot_receive_mail_is_marked_bad_and_stops_counting_towards_the_score(db_session, make_business, seeded_profile, admin_user):
    lead = make_business("Solar Shop", phones=["03001234567"], emails=["info@gone.pk"])
    before = score_of(db_session, lead, seeded_profile)
    mail = FakeMail({"gone.pk": EmailCheck(False, "The email domain does not exist")})

    task = check_leads(db_session, [lead], mail=mail, user_id=admin_user.id)

    assert task.counts["emails_bad"] == 1 and task.counts["rescored"] == 1
    email = contact(db_session, lead, "email")
    assert email.check_status == "bad" and email.check_note == "The email domain does not exist"
    assert score_of(db_session, lead, seeded_profile) == before - 10


def test_a_dead_website_stops_counting_and_a_revived_one_counts_again(db_session, make_business, seeded_profile, admin_user):
    lead = make_business("Solar Shop", phones=["03001234567"], website="https://shop.pk")
    before = score_of(db_session, lead, seeded_profile)

    check_leads(db_session, [lead], sites=FakeSites({"https://shop.pk": SiteProbe(False, "The website returned HTTP 404")}), user_id=admin_user.id)
    db_session.refresh(lead)
    assert lead.website_status == "dead" and score_of(db_session, lead, seeded_profile) == before - 10

    check_leads(db_session, [lead], refresh=True, user_id=admin_user.id)
    db_session.refresh(lead)
    assert lead.website_status == "ok" and score_of(db_session, lead, seeded_profile) == before


def test_a_lookup_that_could_not_finish_changes_nothing(db_session, make_business, admin_user):
    lead = make_business("Solar Shop", emails=["info@slow.pk"], website="https://shop.pk")
    mail = FakeMail({"slow.pk": EmailCheck(None, "unknown")})
    sites = FakeSites({"https://shop.pk": SiteProbe(None, "timed out")})

    task = check_leads(db_session, [lead], mail=mail, sites=sites, user_id=admin_user.id)

    assert task.counts["emails_unknown"] == 1 and task.counts["websites_unknown"] == 1
    assert contact(db_session, lead, "email").check_status is None
    db_session.refresh(lead)
    assert lead.website_status is None and lead.website_checked_at is None


def test_recent_results_are_not_checked_again_unless_asked(db_session, make_business, admin_user):
    lead = make_business("Solar Shop", emails=["info@shop.pk"], website="https://shop.pk")
    mail, sites = FakeMail(), FakeSites()
    check_leads(db_session, [lead], mail=mail, sites=sites, user_id=admin_user.id)

    check_leads(db_session, [lead], mail=mail, sites=sites, user_id=admin_user.id)
    assert mail.asked == ["info@shop.pk"] and sites.asked == ["https://shop.pk"]

    check_leads(db_session, [lead], mail=mail, sites=sites, refresh=True, user_id=admin_user.id)
    assert len(mail.asked) == 2 and len(sites.asked) == 2


def test_results_older_than_a_month_are_checked_again(db_session, make_business, admin_user):
    lead = make_business("Solar Shop", emails=["info@shop.pk"])
    mail = FakeMail()
    check_leads(db_session, [lead], mail=mail, user_id=admin_user.id)
    contact(db_session, lead, "email").checked_at = datetime.now(UTC) - timedelta(days=service.FRESH_DAYS + 1)
    db_session.commit()

    check_leads(db_session, [lead], mail=mail, user_id=admin_user.id)

    assert len(mail.asked) == 2


def test_a_number_listed_for_many_businesses_is_flagged_and_unflagged_when_it_is_not(db_session, make_business, admin_user):
    shared = "+923005556666"
    leads = [make_business(name, phones=[f"0300111111{n}"]) for n, name in enumerate(("Alpha Traders", "Zeta Hardware", "Quick Tyres"))]
    db_session.add_all(ContactPoint(business_id=lead.id, kind="phone", value=shared, source_key="osm") for lead in leads)
    db_session.commit()

    task = check_leads(db_session, leads, user_id=admin_user.id)

    assert task.counts["phones_shared"] == 3
    phone = db_session.query(ContactPoint).filter_by(business_id=leads[0].id, value=shared).one()
    assert phone.check_status == "warning" and "3 businesses" in phone.check_note

    db_session.query(ContactPoint).filter(
        ContactPoint.business_id.in_([leads[1].id, leads[2].id]), ContactPoint.value == shared
    ).delete(synchronize_session=False)
    db_session.commit()
    check_leads(db_session, [leads[0]], refresh=True, user_id=admin_user.id)
    assert db_session.query(ContactPoint).filter_by(business_id=leads[0].id, value=shared).one().check_status is None


def test_leads_with_nothing_to_check_are_counted_as_skipped(db_session, make_business, admin_user):
    lead = make_business("Bare Shop")

    task = check_leads(db_session, [lead], user_id=admin_user.id)

    assert task.status == "completed" and task.counts["skipped"] == 1 and task.counts["leads"] == 1


def test_anyone_signed_in_can_start_checks_and_follow_them(client, sales, db_session, make_business):
    lead = make_business("Solar Shop", emails=["info@shop.pk"])

    response = client.post(f"{BASE}/checks", headers=sales, json={"business_ids": [lead.id]})

    assert response.status_code == 201, response.text
    task = response.json()
    assert task["status"] == "queued" and task["kind"] == "contact_check" and task["total"] == 1
    assert db_session.query(Job).filter_by(kind="quality", ref_id=task["id"], status="queued").count() == 1
    assert client.get(f"{BASE}/tasks/{task['id']}", headers=sales).json()["id"] == task["id"]
    assert client.get(f"{BASE}/tasks/999999", headers=sales).status_code == 404
    assert client.post(f"{BASE}/checks", json={"business_ids": [lead.id]}).status_code == 401


def test_checks_skip_do_not_contact_leads_and_need_at_least_one_lead(client, admin, db_session, make_business):
    lead = make_business("Solar Shop", emails=["info@shop.pk"])
    client.post(f"{LEADS}/{lead.id}/do-not-contact", headers=admin, json={})

    assert client.post(f"{BASE}/checks", headers=admin, json={"business_ids": [lead.id]}).status_code == 404
    assert client.post(f"{BASE}/checks", headers=admin, json={"business_ids": []}).status_code == 422
    assert client.post(f"{BASE}/checks", headers=admin, json={"business_ids": list(range(1, 502))}).status_code == 422


def test_an_interrupted_check_carries_on_after_the_leads_already_done(db_session, make_business, admin_user):
    leads = [make_business(f"Shop {n}", emails=[f"info@shop{n}.pk"]) for n in (1, 2, 3)]
    task = service.start_checks(db_session, CheckRequest(business_ids=[lead.id for lead in leads]), admin_user.id)
    stored = db_session.get(QualityTask, task.id)
    stored.status, stored.done = "running", 2
    db_session.commit()

    assert service.recover_task(db_session, task.id, True) is True
    mail = FakeMail()
    service.run_task(db_session, task.id, mail_factory=lambda: mail, enricher_factory=lambda: FakeSites())

    assert mail.asked == ["info@shop3.pk"] and db_session.get(QualityTask, task.id).done == 3


def test_a_check_out_of_tries_fails_and_other_states_are_left_alone(db_session, make_business, admin_user):
    lead = make_business("Shop", emails=["info@shop.pk"])
    task = service.start_checks(db_session, CheckRequest(business_ids=[lead.id]), admin_user.id)
    assert service.recover_task(db_session, task.id, True) is False
    db_session.get(QualityTask, task.id).status = "running"
    db_session.commit()

    assert service.recover_task(db_session, task.id, False) is False

    stored = db_session.get(QualityTask, task.id)
    assert stored.status == "failed" and "restart" in stored.error


def test_checks_after_a_run_are_queued_only_when_switched_on(db_session, seeded_profile, make_business):
    run = Run(profile_id=seeded_profile.id, profile_name="p", status="completed", source_keys=["osm"], started_at=datetime.now(UTC), stats={})
    db_session.add(run)
    db_session.commit()
    lead = make_business("Solar Shop", emails=["info@shop.pk"])
    db_session.query(SourceRecord).filter_by(business_id=lead.id).update({"run_id": run.id})
    db_session.commit()

    service.queue_checks_after_run(db_session, run.id)
    assert db_session.query(QualityTask).count() == 0

    service.update_settings(db_session, QualitySettingsUpdate(check_after_runs=True))
    service.queue_checks_after_run(db_session, run.id)
    [task] = db_session.query(QualityTask).all()
    assert task.business_ids == [lead.id] and task.created_by_id is None


def test_settings_are_admin_only_and_validated(client, admin, sales):
    assert client.get(f"{BASE}/settings", headers=sales).status_code == 403
    assert client.get(f"{BASE}/settings", headers=admin).json() == {"check_after_runs": False, "max_checks_per_run": 200}

    saved = client.put(f"{BASE}/settings", headers=admin, json={"check_after_runs": True}).json()

    assert saved == {"check_after_runs": True, "max_checks_per_run": 200}
    assert client.put(f"{BASE}/settings", headers=admin, json={"max_checks_per_run": 0}).status_code == 422


def pair(db_session, a, b, **fields):
    first, second = sorted((a.id, b.id))
    values = {"reason": "phone", "similarity": 20, "confidence": "possible"}
    values.update(fields)
    candidate = DuplicateCandidate(business_a_id=first, business_b_id=second, **values)
    db_session.add(candidate)
    db_session.commit()
    return candidate


def test_a_new_lead_that_nearly_matches_an_old_one_is_queued_for_review_once(db_session, make_business):
    first = make_business("Al Noor Solar", phones=["03001234567"])
    second = make_business("Zeta Hardware Store", phones=["03001234567"])

    [candidate] = db_session.query(DuplicateCandidate).all()

    assert (candidate.business_a_id, candidate.business_b_id) == (first.id, second.id)
    assert candidate.reason == "phone" and candidate.confidence == "possible" and candidate.status == "pending"


def test_a_clear_match_is_merged_automatically_and_never_asks(db_session, make_business):
    make_business("Al Noor Solar", phones=["03001234567"])
    make_business("Al Noor Solar Shop", phones=["03001234567"])

    assert db_session.query(Business).count() == 1 and db_session.query(DuplicateCandidate).count() == 0


def test_the_scan_finds_pairs_already_stored_and_skips_ones_already_decided(db_session, make_business):
    first = make_business("Al Noor Solar", phones=["03001234567"])
    second = make_business("Zeta Hardware Store", phones=["03001234567"])
    third = make_business("Noor Solar Systems")
    db_session.add(ContactPoint(business_id=third.id, kind="phone", value="+923001234567", source_key="osm"))
    db_session.commit()
    db_session.query(DuplicateCandidate).delete()
    db_session.commit()

    summary = duplicates.scan(db_session)

    assert summary["businesses"] == 3 and summary["pairs_found"] == 3
    found = {(c.business_a_id, c.business_b_id): c for c in db_session.query(DuplicateCandidate)}
    assert found[(first.id, third.id)].confidence == "likely" and found[(first.id, second.id)].confidence == "possible"

    found[(first.id, second.id)].status = "dismissed"
    db_session.commit()
    assert duplicates.scan(db_session)["pairs_found"] == 0
    assert db_session.query(DuplicateCandidate).count() == 3


def test_the_scan_runs_as_a_job(client, admin, db_session, make_business):
    make_business("Al Noor Solar", phones=["03001234567"])
    make_business("Zeta Hardware Store", phones=["03001234567"])
    db_session.query(DuplicateCandidate).delete()
    db_session.commit()

    started = client.post(f"{BASE}/duplicates/scan", headers=admin)
    assert started.status_code == 201 and started.json()["kind"] == "duplicate_scan"
    service.run_task(db_session, started.json()["id"])

    done = client.get(f"{BASE}/tasks/{started.json()['id']}", headers=admin).json()
    assert done["status"] == "completed" and done["counts"]["pairs_found"] == 1
    assert client.get(f"{BASE}/duplicates", headers=admin).json()["count"] == 1


def test_the_review_list_shows_both_sides_with_likely_pairs_first(client, admin, sales, db_session, make_business):
    a = make_business("Al Noor Solar", phones=["03001234567"], emails=["a@noor.pk"], website="https://noor.pk")
    b = make_business("Zeta Hardware Store", phones=["03001234567"])
    c = make_business("Quick Tyres", phones=["03009998888"])
    db_session.query(DuplicateCandidate).delete()
    db_session.commit()
    pair(db_session, a, b, similarity=30)
    pair(db_session, b, c, similarity=70, reason="location")
    likely = pair(db_session, a, c, similarity=100, confidence="likely", reason="website")

    listed = client.get(f"{BASE}/duplicates", headers=admin).json()

    assert listed["count"] == 3 and listed["data"][0]["id"] == likely.id and listed["data"][0]["confidence"] == "likely"
    side = listed["data"][0]["a"]
    assert side["name"] == "Al Noor Solar" and side["emails"] == ["a@noor.pk"] and side["website"] == "https://noor.pk"
    assert side["phones"] == ["+923001234567"] and side["city"] == "Lahore" and side["score"] is not None
    assert [item["similarity"] for item in listed["data"][1:]] == [70, 30]
    assert len(client.get(f"{BASE}/duplicates", headers=admin, params={"limit": 2}).json()["data"]) == 2
    assert client.get(f"{BASE}/duplicates", headers=sales).status_code == 403
    assert client.get(f"{BASE}/duplicates", headers=admin, params={"status": "bogus"}).status_code == 422


def test_saying_two_leads_are_different_removes_the_pair_from_review(client, admin, db_session, make_business):
    a, b = make_business("Al Noor Solar", phones=["03001234567"]), make_business("Zeta Hardware Store", phones=["03001234567"])
    candidate = db_session.query(DuplicateCandidate).one()

    assert client.post(f"{BASE}/duplicates/{candidate.id}/dismiss", headers=admin).status_code == 204

    assert client.get(f"{BASE}/duplicates", headers=admin).json()["count"] == 0
    assert client.get(f"{BASE}/duplicates", headers=admin, params={"status": "dismissed"}).json()["count"] == 1
    assert client.post(f"{BASE}/duplicates/{candidate.id}/dismiss", headers=admin).status_code == 409
    assert client.post(f"{BASE}/duplicates/999999/dismiss", headers=admin).status_code == 404
    assert db_session.query(Business).filter(Business.id.in_([a.id, b.id])).count() == 2


def test_merging_brings_everything_across_and_keeps_the_do_not_contact_flag(client, admin, db_session, make_business, admin_user, sales_user):
    keep = make_business("Al Noor Solar", phones=["03001111111"], emails=["a@noor.pk"])
    gone = make_business("Noor Solar Systems", phones=["03002222222"], emails=["a@noor.pk", "b@noor.pk"], website="https://noor.pk", address="Mall Road")
    gone.lead_status, gone.assigned_to_id, gone.notes = "interested", sales_user.id, "Wants a quote"
    keep.notes = "Called twice"
    db_session.add_all(
        [
            LeadActivity(business_id=gone.id, kind="note", summary="Spoke to the owner"),
            LeadTask(business_id=gone.id, title="Send quote", due_on=date.today()),
            LeadOutcome(business_id=gone.id, kind="lost", closed_at=datetime.now(UTC), loss_reason="price"),
            DoNotContact(business_id=gone.id, reason="Asked to stop"),
        ]
    )
    db_session.commit()
    candidate_id, keep_id, gone_id = pair(db_session, keep, gone).id, keep.id, gone.id

    response = client.post(f"{BASE}/duplicates/{candidate_id}/merge", headers=admin, json={"keep_id": keep_id})

    assert response.status_code == 200, response.text
    assert response.json() == {"kept_id": keep_id, "removed_id": gone_id}
    db_session.expire_all()
    assert db_session.get(Business, gone_id) is None
    merged = db_session.get(Business, keep_id)
    assert sorted(c.value for c in merged.contact_points if c.kind == "email") == ["a@noor.pk", "b@noor.pk"]
    assert sorted(c.value for c in merged.contact_points if c.kind == "phone") == ["+923001111111", "+923002222222"]
    assert merged.website == "https://noor.pk" and merged.address == "Mall Road" and merged.assigned_to_id == sales_user.id
    assert merged.notes == "Called twice\n\nWants a quote" and merged.lead_status == "interested"
    assert db_session.query(LeadOutcome).filter_by(business_id=keep_id, kind="lost").count() == 1
    assert db_session.query(LeadTask).filter_by(business_id=keep_id).count() == 1
    assert db_session.query(DoNotContact).filter_by(business_id=keep_id).count() == 1
    kinds = [a.kind for a in db_session.query(LeadActivity).filter_by(business_id=keep_id)]
    assert "note" in kinds and "merged" in kinds
    assert client.get(f"{LEADS}/{gone_id}", headers=admin).status_code == 404
    assert client.get(f"{LEADS}/{keep_id}", headers=admin).status_code == 404


def test_merging_keeps_the_better_of_two_scores_and_does_not_double_up_records(client, admin, db_session, make_business, seeded_profile):
    keep = make_business("Al Noor Solar", phones=["03001111111"])
    gone = make_business("Noor Solar Systems", phones=["03002222222"], emails=["a@noor.pk"])
    candidate_id, keep_id, gone_id = pair(db_session, keep, gone).id, keep.id, gone.id

    client.post(f"{BASE}/duplicates/{candidate_id}/merge", headers=admin, json={"keep_id": gone_id})

    db_session.expire_all()
    assert db_session.get(Business, keep_id) is None
    rows = db_session.query(BusinessClassification).filter_by(business_id=gone_id).all()
    assert len(rows) == 1
    assert rows[0].score >= 30 + 10


def test_a_merge_needs_a_pending_pair_and_one_of_its_own_leads(client, admin, sales, db_session, make_business):
    a, b = make_business("Al Noor Solar", phones=["03001234567"]), make_business("Zeta Hardware Store", phones=["03001234567"])
    other = make_business("Quick Tyres")
    candidate_id, a_id, b_id, other_id = db_session.query(DuplicateCandidate).one().id, a.id, b.id, other.id

    assert client.post(f"{BASE}/duplicates/{candidate_id}/merge", headers=admin, json={"keep_id": other_id}).status_code == 400
    assert client.post(f"{BASE}/duplicates/{candidate_id}/merge", headers=sales, json={"keep_id": a_id}).status_code == 403
    assert client.post(f"{BASE}/duplicates/999999/merge", headers=admin, json={"keep_id": a_id}).status_code == 404
    assert client.post(f"{BASE}/duplicates/{candidate_id}/merge", headers=admin, json={"keep_id": a_id}).status_code == 200
    assert client.post(f"{BASE}/duplicates/{candidate_id}/merge", headers=admin, json={"keep_id": a_id}).status_code == 404
    db_session.expire_all()
    assert db_session.get(Business, b_id) is None


def close_deals(db_session, make_business, with_email_wins, with_email_losses, without_wins, without_losses):
    counter = iter(range(1, 1000))

    def make(has_email, won):
        n = next(counter)
        lead = make_business(f"Shop {n}", phones=[f"0300{n:07d}"], emails=[f"info@shop{n}.pk"] if has_email else [])
        db_session.add(LeadOutcome(business_id=lead.id, kind="won" if won else "lost", closed_at=datetime.now(UTC)))
        return lead

    leads = (
        [make(True, True) for _ in range(with_email_wins)]
        + [make(True, False) for _ in range(with_email_losses)]
        + [make(False, True) for _ in range(without_wins)]
        + [make(False, False) for _ in range(without_losses)]
    )
    db_session.commit()
    return leads


def trait(report, key):
    return next(item for item in report["traits"] if item["key"] == key)


def test_scoring_asks_for_more_closed_deals_before_suggesting_anything(client, admin, seeded_profile, db_session, make_business):
    close_deals(db_session, make_business, 5, 2, 1, 4)

    report = client.get(f"{BASE}/scoring", headers=admin, params={"profile_id": seeded_profile.id}).json()

    assert report["closed"] == 12 and report["enough_data"] is False and report["can_apply"] is False
    assert all(item["suggested_weight"] == item["current_weight"] for item in report["traits"])
    assert client.post(f"{BASE}/scoring/apply", headers=admin, json={"profile_id": seeded_profile.id}).status_code == 400


def test_scoring_finds_the_trait_that_goes_with_winning_and_suggests_more_weight_for_it(client, admin, seeded_profile, db_session, make_business):
    close_deals(db_session, make_business, 16, 4, 4, 16)

    report = client.get(f"{BASE}/scoring", headers=admin, params={"profile_id": seeded_profile.id}).json()

    assert report["closed"] == 40 and report["won"] == 20 and report["lost"] == 20 and report["enough_data"] is True
    email = trait(report, "has_email")
    assert (email["with_count"], email["with_wins"], email["without_count"], email["without_wins"]) == (20, 16, 20, 4)
    assert email["win_rate_with"] == 80.0 and email["win_rate_without"] == 20.0 and email["difference"] == 60.0
    assert email["significant"] is True and email["suggested_weight"] == email["current_weight"] + 25
    phone = trait(report, "has_phone")
    assert phone["without_count"] == 0 and phone["significant"] is False and phone["suggested_weight"] == phone["current_weight"]
    assert report["can_apply"] is True and report["can_revert"] is False


def test_a_small_difference_in_a_small_group_is_not_treated_as_a_pattern(client, admin, seeded_profile, db_session, make_business):
    close_deals(db_session, make_business, 8, 8, 7, 9)

    email = trait(client.get(f"{BASE}/scoring", headers=admin, params={"profile_id": seeded_profile.id}).json(), "has_email")

    assert email["significant"] is False and email["suggested_weight"] == email["current_weight"]


def test_a_trait_that_goes_with_losing_loses_weight_but_never_below_zero(client, admin, seeded_profile, db_session, make_business):
    close_deals(db_session, make_business, 3, 17, 17, 3)
    seeded_profile.scoring_config = {**(seeded_profile.scoring_config or {}), "has_email": 5}
    db_session.commit()

    email = trait(client.get(f"{BASE}/scoring", headers=admin, params={"profile_id": seeded_profile.id}).json(), "has_email")

    assert email["difference"] < 0 and email["significant"] is True and email["suggested_weight"] == 0


def test_applying_changes_the_weights_rescores_the_leads_and_can_be_undone(client, admin, seeded_profile, db_session, make_business):
    leads = close_deals(db_session, make_business, 16, 4, 4, 16)
    emailed, plain = leads[0], leads[-1]
    before = {lead.id: score_of(db_session, lead, seeded_profile) for lead in (emailed, plain)}
    old_weight = trait(client.get(f"{BASE}/scoring", headers=admin, params={"profile_id": seeded_profile.id}).json(), "has_email")["current_weight"]

    applied = client.post(f"{BASE}/scoring/apply", headers=admin, json={"profile_id": seeded_profile.id})

    assert applied.status_code == 200, applied.text
    assert applied.json()["weights"]["has_email"] == old_weight + 25 and applied.json()["rescored"] >= 40
    db_session.expire_all()
    assert score_of(db_session, emailed, seeded_profile) == min(100, before[emailed.id] + 25)
    assert score_of(db_session, plain, seeded_profile) == before[plain.id]
    after = client.get(f"{BASE}/scoring", headers=admin, params={"profile_id": seeded_profile.id}).json()
    assert after["can_revert"] is True and trait(after, "has_email")["current_weight"] == old_weight + 25

    reverted = client.post(f"{BASE}/scoring/revert", headers=admin, json={"profile_id": seeded_profile.id})

    assert reverted.status_code == 200 and reverted.json()["weights"]["has_email"] == old_weight
    db_session.expire_all()
    assert score_of(db_session, emailed, seeded_profile) == before[emailed.id]
    assert client.post(f"{BASE}/scoring/revert", headers=admin, json={"profile_id": seeded_profile.id}).status_code == 400


def test_scoring_is_admin_only_and_needs_a_real_profile(client, admin, sales, seeded_profile):
    params = {"profile_id": seeded_profile.id}

    assert client.get(f"{BASE}/scoring", headers=sales, params=params).status_code == 403
    assert client.post(f"{BASE}/scoring/apply", headers=sales, json=params).status_code == 403
    assert client.post(f"{BASE}/scoring/revert", headers=sales, json=params).status_code == 403
    assert client.get(f"{BASE}/scoring", headers=admin, params={"profile_id": 99999}).status_code == 404
    assert client.get(f"{BASE}/scoring", headers=admin).status_code == 422


def test_changing_the_weights_by_hand_rescores_existing_leads(client, admin, seeded_profile, db_session, make_business):
    lead = make_business("Solar Shop", phones=["03001234567"], emails=["info@shop.pk"])
    before = score_of(db_session, lead, seeded_profile)
    weights = {**(seeded_profile.scoring_config or {})}
    email_weight = {**ScoringConfig().model_dump(), **weights}["has_email"]

    response = client.put(
        f"/api/v1/profiles/{seeded_profile.id}", headers=admin, json={"scoring_config": {**weights, "has_email": 0}}
    )

    assert response.status_code == 200, response.text
    db_session.expire_all()
    assert score_of(db_session, lead, seeded_profile) == before - email_weight
