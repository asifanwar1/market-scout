import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app.core.config import settings
from app.core.crypto import decrypt_secret
from app.core.scouting.enrichment.website import EnrichmentError
from app.features.alerts import service as alerts_service
from app.features.businesses.models import BusinessClassification, SourceRecord
from app.features.jobs import service as jobs_service
from app.features.jobs.models import Job, JobKind
from app.features.runs.models import Run
from app.features.webhooks import delivery, service
from app.features.webhooks.delivery import SendResult
from app.features.webhooks.models import Webhook, WebhookDelivery

BASE = "/api/v1/webhooks"
LEADS = "/api/v1/businesses"
URL = "https://hooks.example.com/in"
PUBLIC_ADDRESS = "93.184.216.34"
ALL_EVENTS = ["lead.created", "lead.status_changed", "alert.raised", "message.sent"]


@pytest.fixture(autouse=True)
def public_dns(monkeypatch):
    monkeypatch.setattr(service, "resolve_host", lambda host: [PUBLIC_ADDRESS])


@pytest.fixture()
def admin(admin_user, auth_headers):
    return auth_headers(admin_user)


@pytest.fixture()
def sales(sales_user, auth_headers):
    return auth_headers(sales_user)


class Receiver:
    def __init__(self, *results):
        self.results = list(results) or [SendResult(200, None)]
        self.calls = []

    def __call__(self, url, headers, body):
        self.calls.append((url, headers, body))
        return self.results.pop(0) if len(self.results) > 1 else self.results[0]


OK = SendResult(200, None)
BROKEN = SendResult(500, "HTTP 500")


def aware(value):
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def make_hook(client, admin, events=None, url=URL, name="Billing app"):
    return client.post(f"{BASE}/", headers=admin, json={"name": name, "url": url, "events": ALL_EVENTS if events is None else events})


def deliveries(db_session, event=None):
    query = db_session.query(WebhookDelivery)
    if event:
        query = query.filter_by(event=event)
    return query.order_by(WebhookDelivery.id).all()


def run_attempt(db_session, delivery_id, receiver=None, now=None):
    return delivery.attempt(db_session, delivery_id, sender=receiver or Receiver(), now=now)


def test_the_config_lists_the_events_and_limits(client, admin):
    config = client.get(f"{BASE}/config", headers=admin).json()

    assert [event["key"] for event in config["events"]] == ALL_EVENTS
    assert config["max_attempts"] == 5 and config["disable_after_failures"] == 15 and config["allow_private_urls"] is False


def test_a_new_webhook_shows_its_secret_once(client, admin, db_session):
    created = make_hook(client, admin)

    assert created.status_code == 201
    data = created.json()
    assert data["secret"].startswith("whsec_") and data["is_active"] is True and data["events"] == ALL_EVENTS
    assert data["secret_hint"] == f"…{data['secret'][-4:]}"
    listed = client.get(f"{BASE}/", headers=admin).json()
    assert listed["count"] == 1 and "secret" not in listed["data"][0]
    stored = db_session.query(Webhook).one()
    assert stored.secret != data["secret"] and decrypt_secret(stored.secret) == data["secret"]


def test_a_webhook_needs_a_name_and_at_least_one_real_event(client, admin):
    assert client.post(f"{BASE}/", headers=admin, json={"name": " ", "url": URL, "events": ["lead.created"]}).status_code == 422
    assert make_hook(client, admin, events=[]).status_code == 422
    assert make_hook(client, admin, events=["ping"]).status_code == 422
    assert make_hook(client, admin, events=["lead.exploded"]).status_code == 422
    assert client.post(f"{BASE}/", headers=admin, json={"name": "Okay", "url": URL, "events": ["lead.created"], "x": 1}).status_code == 422
    assert make_hook(client, admin, events=["lead.created", "lead.created"]).json()["events"] == ["lead.created"]


@pytest.mark.parametrize("url", [
    "http://hooks.example.com/in", "ftp://hooks.example.com/in", "https://", "not a url", "https://user:pw@hooks.example.com/in",
    "https://127.0.0.1/in", "https://10.0.0.5/in", "https://169.254.169.254/latest", "https://[::1]/in",
])
def test_unsafe_or_malformed_addresses_are_refused(client, admin, url):
    assert make_hook(client, admin, url=url).status_code == 400


def test_a_name_that_points_at_a_private_address_is_refused(client, admin, monkeypatch):
    monkeypatch.setattr(service, "resolve_host", lambda host: ["192.168.1.20"])

    response = make_hook(client, admin)

    assert response.status_code == 400 and "not a public address" in response.json()["detail"]


def test_a_name_that_cannot_be_found_is_refused(client, admin, monkeypatch):
    def missing(host):
        raise EnrichmentError("nope")

    monkeypatch.setattr(service, "resolve_host", missing)

    response = make_hook(client, admin)

    assert response.status_code == 400 and "Could not find" in response.json()["detail"]


def test_private_addresses_can_be_allowed_for_local_testing(client, admin, monkeypatch):
    monkeypatch.setattr(settings, "WEBHOOKS_ALLOW_PRIVATE_URLS", True)

    assert make_hook(client, admin, url="http://127.0.0.1:9000/hook").status_code == 201
    assert make_hook(client, admin, url="ftp://127.0.0.1/hook", name="Other").status_code == 400
    assert client.get(f"{BASE}/config", headers=admin).json()["allow_private_urls"] is True


def test_a_webhook_can_be_renamed_repointed_and_given_other_events(client, admin):
    hook = make_hook(client, admin).json()

    changed = client.patch(
        f"{BASE}/{hook['id']}", headers=admin,
        json={"name": "Renamed", "url": "https://other.example.com/in", "events": ["message.sent"]},
    )

    assert changed.status_code == 200
    assert (changed.json()["name"], changed.json()["url"], changed.json()["events"]) == ("Renamed", "https://other.example.com/in", ["message.sent"])
    assert client.patch(f"{BASE}/{hook['id']}", headers=admin, json={}).status_code == 400
    assert client.patch(f"{BASE}/{hook['id']}", headers=admin, json={"url": "http://insecure.example.com"}).status_code == 400
    assert client.patch(f"{BASE}/999", headers=admin, json={"name": "Nope"}).status_code == 404


def test_turning_a_webhook_back_on_clears_its_failure_count(client, admin, db_session):
    hook = make_hook(client, admin).json()
    row = db_session.get(Webhook, hook["id"])
    row.is_active, row.consecutive_failures, row.last_error = False, 15, "Turned off after 15 failed attempts in a row"
    db_session.commit()

    revived = client.patch(f"{BASE}/{hook['id']}", headers=admin, json={"is_active": True}).json()

    assert revived["is_active"] is True and revived["consecutive_failures"] == 0 and revived["last_error"] is None


def test_the_secret_can_be_replaced(client, admin, db_session):
    hook = make_hook(client, admin).json()

    rotated = client.post(f"{BASE}/{hook['id']}/rotate-secret", headers=admin).json()

    assert rotated["secret"] != hook["secret"] and decrypt_secret(db_session.get(Webhook, hook["id"]).secret) == rotated["secret"]
    assert client.post(f"{BASE}/999/rotate-secret", headers=admin).status_code == 404


def test_deleting_a_webhook_removes_its_deliveries(client, admin, db_session, make_business):
    hook = make_hook(client, admin).json()
    make_business("Al Noor Solar", phones=["0300 4438424"])
    assert len(deliveries(db_session)) == 1

    assert client.delete(f"{BASE}/{hook['id']}", headers=admin).status_code == 204

    assert db_session.query(WebhookDelivery).count() == 0 and client.delete(f"{BASE}/{hook['id']}", headers=admin).status_code == 404


def test_a_new_lead_is_announced_with_a_job_to_send_it(client, admin, db_session, make_business):
    make_hook(client, admin)

    lead = make_business("Al Noor Solar", phones=["0300 4438424"], emails=["info@alnoor.pk"], website="https://alnoor.pk")

    (queued,) = deliveries(db_session, "lead.created")
    assert queued.status == "queued" and queued.attempts == 0
    snapshot = queued.payload["lead"]
    assert snapshot["id"] == lead.id and snapshot["name"] == "Al Noor Solar" and snapshot["city"] == "Lahore"
    assert snapshot["phones"] == ["+923004438424"] and snapshot["emails"] == ["info@alnoor.pk"] and snapshot["status"] == "new"
    assert isinstance(snapshot["score"], int)
    job = db_session.query(Job).filter_by(kind=JobKind.WEBHOOK.value).one()
    assert job.ref_id == queued.id and job.status == "queued"


def test_a_lead_that_already_existed_is_not_announced_again(client, admin, db_session, make_business):
    make_hook(client, admin)
    make_business("Al Noor Solar", phones=["0300 4438424"])

    make_business("Al Noor Solar", phones=["0300 4438424"])

    assert len(deliveries(db_session, "lead.created")) == 1


def test_only_subscribed_active_webhooks_are_told(client, admin, db_session, make_business):
    make_hook(client, admin, events=["message.sent"], name="Messages only")
    off = make_hook(client, admin, events=["lead.created"], name="Switched off").json()
    client.patch(f"{BASE}/{off['id']}", headers=admin, json={"is_active": False})
    on = make_hook(client, admin, events=["lead.created"], name="Leads").json()

    make_business("Al Noor Solar", phones=["0300 4438424"])

    assert [d.webhook_id for d in deliveries(db_session)] == [on["id"]]


def test_two_webhooks_each_get_their_own_delivery(client, admin, db_session, make_business):
    make_hook(client, admin, name="One")
    make_hook(client, admin, name="Two")

    make_business("Al Noor Solar", phones=["0300 4438424"])

    assert len(deliveries(db_session)) == 2 and db_session.query(Job).filter_by(kind="webhook").count() == 2


def test_a_status_change_is_announced_with_before_and_after(client, admin, db_session, make_business):
    lead = make_business("Al Noor Solar", phones=["0300 4438424"])
    make_hook(client, admin, events=["lead.status_changed"])

    client.patch(f"{LEADS}/{lead.id}", headers=admin, json={"lead_status": "interested"})
    client.patch(f"{LEADS}/{lead.id}", headers=admin, json={"lead_status": "interested"})
    client.patch(f"{LEADS}/{lead.id}", headers=admin, json={"notes": "Only a note"})

    (event,) = deliveries(db_session, "lead.status_changed")
    assert (event.payload["from_status"], event.payload["to_status"]) == ("new", "interested")
    assert event.payload["lead"]["status"] == "interested" and event.payload["outcome"] is None


def test_winning_a_deal_includes_its_value_and_product(client, admin, db_session, make_business):
    lead = make_business("Al Noor Solar", phones=["0300 4438424"])
    make_hook(client, admin, events=["lead.status_changed"])

    client.patch(f"{LEADS}/{lead.id}", headers=admin, json={"lead_status": "customer", "outcome": {"value": 2500, "product": "Billing"}})

    (event,) = deliveries(db_session, "lead.status_changed")
    assert event.payload["to_status"] == "customer"
    assert event.payload["outcome"] == {"kind": "won", "value": 2500.0, "product": "Billing", "loss_reason": None}


def test_losing_a_deal_includes_the_reason(client, admin, db_session, make_business):
    lead = make_business("Al Noor Solar", phones=["0300 4438424"])
    make_hook(client, admin, events=["lead.status_changed"])

    client.patch(f"{LEADS}/{lead.id}", headers=admin, json={"lead_status": "not_interested", "outcome": {"loss_reason": "price"}})

    (event,) = deliveries(db_session, "lead.status_changed")
    assert event.payload["outcome"]["kind"] == "lost" and event.payload["outcome"]["loss_reason"] == "price"


def test_a_bulk_status_change_announces_each_lead_that_moved(client, admin, db_session, make_business):
    first = make_business("First Solar", phones=["0300 1111111"])
    second = make_business("Second Solar", phones=["0300 2222222"])
    already = make_business("Already Solar", phones=["0300 3333333"])
    client.patch(f"{LEADS}/{already.id}", headers=admin, json={"lead_status": "contacted"})
    make_hook(client, admin, events=["lead.status_changed"])

    client.post(f"{LEADS}/bulk-update", headers=admin, json={"business_ids": [first.id, second.id, already.id], "lead_status": "contacted"})

    assert sorted(d.payload["lead"]["id"] for d in deliveries(db_session)) == sorted([first.id, second.id])


@pytest.fixture()
def run(db_session, seeded_profile):
    record = Run(
        profile_id=seeded_profile.id, profile_name=seeded_profile.name, status="completed", source_keys=["osm"],
        started_at=datetime.now(UTC) - timedelta(minutes=60), finished_at=datetime.now(UTC) - timedelta(minutes=1), stats={},
    )
    db_session.add(record)
    db_session.commit()
    return record


def test_an_alert_is_announced_with_the_lead(client, admin, db_session, seeded_profile, run, make_business):
    lead = make_business("Al Noor Solar", phones=["0300 4438424"], now=datetime.now(UTC) - timedelta(minutes=30))
    db_session.query(SourceRecord).filter_by(business_id=lead.id).update({"run_id": run.id})
    db_session.query(BusinessClassification).filter_by(business_id=lead.id, profile_id=seeded_profile.id).update({"score": 90})
    db_session.commit()
    make_hook(client, admin, events=["alert.raised"])

    alerts_service.evaluate_run(db_session, run.id)

    (event,) = deliveries(db_session, "alert.raised")
    assert event.payload["alert"]["kind"] == "new_lead" and "Al Noor Solar" in event.payload["alert"]["message"]
    assert event.payload["lead"]["id"] == lead.id and event.payload["lead"]["score"] == 90


def test_a_confirmed_message_is_announced(client, admin, db_session, make_business):
    lead = make_business("Al Noor Solar", phones=["0300 4438424"])
    phone_id = next(c["id"] for c in client.get(f"{LEADS}/{lead.id}", headers=admin).json()["contacts"] if c["kind"] == "phone")
    make_hook(client, admin, events=["message.sent"])
    prepared = client.post(
        "/api/v1/outreach/messages", headers=admin,
        json={"business_id": lead.id, "contact_id": phone_id, "channel": "whatsapp", "body": "Salam {business_name}"},
    ).json()

    assert deliveries(db_session) == []
    client.post(f"/api/v1/outreach/messages/{prepared['id']}/decision", headers=admin, json={"sent": False})
    assert deliveries(db_session) == []
    again = client.post(
        "/api/v1/outreach/messages", headers=admin,
        json={"business_id": lead.id, "contact_id": phone_id, "channel": "whatsapp", "body": "Salam {business_name}"},
    ).json()
    client.post(f"/api/v1/outreach/messages/{again['id']}/decision", headers=admin, json={"sent": True})

    (event,) = deliveries(db_session, "message.sent")
    assert event.payload["message"]["body"] == "Salam Al Noor Solar" and event.payload["message"]["channel"] == "whatsapp"
    assert event.payload["message"]["to"] == "+923004438424" and event.payload["sent_by"] == "Admin User"
    assert event.payload["lead"]["id"] == lead.id


def test_the_test_button_queues_a_ping_even_for_a_switched_off_webhook(client, admin, db_session):
    hook = make_hook(client, admin).json()
    client.patch(f"{BASE}/{hook['id']}", headers=admin, json={"is_active": False})

    response = client.post(f"{BASE}/{hook['id']}/test", headers=admin)

    assert response.status_code == 202 and response.json()["event"] == "ping" and response.json()["status"] == "queued"
    assert db_session.query(Job).filter_by(kind="webhook").count() == 1
    assert client.post(f"{BASE}/999/test", headers=admin).status_code == 404


def test_a_delivery_is_signed_and_marks_the_webhook_healthy(client, admin, db_session, make_business):
    hook = make_hook(client, admin).json()
    lead = make_business("Al Noor Solar", phones=["0300 4438424"])
    (queued,) = deliveries(db_session)
    receiver = Receiver(OK)

    run_attempt(db_session, queued.id, receiver)

    url, headers, body = receiver.calls[0]
    assert url == URL and headers["X-MarketScout-Event"] == "lead.created" and headers["X-MarketScout-Delivery"] == str(queued.id)
    assert headers["Content-Type"] == "application/json"
    timestamp, digest = (part.split("=", 1)[1] for part in headers["X-MarketScout-Signature"].split(","))
    expected = hmac.new(hook["secret"].encode(), f"{timestamp}.".encode() + body, hashlib.sha256).hexdigest()
    assert digest == expected
    envelope = json.loads(body)
    assert envelope["id"] == queued.id and envelope["event"] == "lead.created" and envelope["data"]["lead"]["id"] == lead.id
    db_session.refresh(queued)
    assert queued.status == "delivered" and queued.attempts == 1 and queued.response_status == 200 and queued.delivered_at is not None
    row = db_session.get(Webhook, hook["id"])
    assert row.consecutive_failures == 0 and row.last_status_code == 200 and row.last_error is None and row.last_delivery_at is not None


def test_the_body_is_the_same_every_time_it_is_sent(client, admin, db_session, make_business):
    make_hook(client, admin)
    make_business("Al Noor Solar", phones=["0300 4438424"])
    (queued,) = deliveries(db_session)

    assert delivery.build_body(queued) == delivery.build_body(queued)


def test_a_failed_attempt_is_retried_later_with_growing_waits(client, admin, db_session, make_business):
    make_hook(client, admin)
    make_business("Al Noor Solar", phones=["0300 4438424"])
    (queued,) = deliveries(db_session)
    waits = []

    for _ in range(4):
        before = datetime.now(UTC)
        run_attempt(db_session, queued.id, Receiver(BROKEN))
        db_session.refresh(queued)
        assert queued.status == "queued" and queued.error == "HTTP 500" and queued.response_status == 500
        waits.append(round((aware(queued.next_attempt_at) - before).total_seconds() / 10) * 10)

    assert waits == [30, 120, 600, 3600] and queued.attempts == 4


def test_after_the_last_attempt_the_delivery_gives_up(client, admin, db_session, make_business):
    hook = make_hook(client, admin).json()
    make_business("Al Noor Solar", phones=["0300 4438424"])
    (queued,) = deliveries(db_session)

    for _ in range(5):
        run_attempt(db_session, queued.id, Receiver(BROKEN))

    db_session.refresh(queued)
    assert queued.status == "failed" and queued.attempts == 5 and queued.error == "HTTP 500"
    row = db_session.get(Webhook, hook["id"])
    assert row.consecutive_failures == 5 and row.is_active is True and row.last_error == "HTTP 500"
    run_attempt(db_session, queued.id, Receiver(OK))
    db_session.refresh(queued)
    assert queued.status == "failed" and queued.attempts == 5


def test_a_success_after_failures_resets_the_count(client, admin, db_session, make_business):
    hook = make_hook(client, admin).json()
    make_business("Al Noor Solar", phones=["0300 4438424"])
    (queued,) = deliveries(db_session)

    run_attempt(db_session, queued.id, Receiver(BROKEN))
    run_attempt(db_session, queued.id, Receiver(OK))

    db_session.refresh(queued)
    assert queued.status == "delivered" and queued.attempts == 2 and queued.error is None
    assert db_session.get(Webhook, hook["id"]).consecutive_failures == 0


def test_a_request_that_never_got_an_answer_is_a_failure(client, admin, db_session, make_business):
    make_hook(client, admin)
    make_business("Al Noor Solar", phones=["0300 4438424"])
    (queued,) = deliveries(db_session)

    run_attempt(db_session, queued.id, Receiver(SendResult(None, "The request failed (ConnectTimeout)")))

    db_session.refresh(queued)
    assert queued.status == "queued" and queued.response_status is None and "ConnectTimeout" in queued.error


def test_a_webhook_that_keeps_failing_switches_itself_off(client, admin, db_session, make_business):
    hook = make_hook(client, admin).json()
    for index in range(3):
        make_business(f"Shop {index}", phones=[f"030{index} 1112223"])
    for queued in deliveries(db_session):
        for _ in range(5):
            run_attempt(db_session, queued.id, Receiver(BROKEN))

    row = db_session.get(Webhook, hook["id"])
    assert row.is_active is False and row.consecutive_failures == 15 and "Turned off after 15" in row.last_error


def test_a_waiting_delivery_for_a_switched_off_webhook_is_dropped_unsent(client, admin, db_session, make_business):
    hook = make_hook(client, admin).json()
    make_business("Al Noor Solar", phones=["0300 4438424"])
    client.patch(f"{BASE}/{hook['id']}", headers=admin, json={"is_active": False})
    (queued,) = deliveries(db_session)
    receiver = Receiver(OK)

    run_attempt(db_session, queued.id, receiver)

    db_session.refresh(queued)
    assert receiver.calls == [] and queued.status == "failed" and queued.error == "The webhook was turned off"


def test_a_test_ping_gets_one_try_and_does_not_count_against_the_webhook(client, admin, db_session):
    hook = make_hook(client, admin).json()
    ping_id = client.post(f"{BASE}/{hook['id']}/test", headers=admin).json()["id"]

    run_attempt(db_session, ping_id, Receiver(BROKEN))

    ping = db_session.get(WebhookDelivery, ping_id)
    assert ping.status == "failed" and ping.attempts == 1
    row = db_session.get(Webhook, hook["id"])
    assert row.consecutive_failures == 0 and row.last_error == "HTTP 500" and row.last_status_code == 500


def test_a_ping_that_works_is_delivered_with_a_plain_message(client, admin, db_session):
    hook = make_hook(client, admin).json()
    ping_id = client.post(f"{BASE}/{hook['id']}/test", headers=admin).json()["id"]
    receiver = Receiver(OK)

    run_attempt(db_session, ping_id, receiver)

    assert db_session.get(WebhookDelivery, ping_id).status == "delivered"
    assert json.loads(receiver.calls[0][2])["data"] == {"message": "This is a test from Market Scout"}


def test_only_a_failed_delivery_can_be_sent_again(client, admin, db_session, make_business):
    make_hook(client, admin)
    make_business("Al Noor Solar", phones=["0300 4438424"])
    (queued,) = deliveries(db_session)

    assert client.post(f"{BASE}/deliveries/{queued.id}/retry", headers=admin).status_code == 400
    for _ in range(5):
        run_attempt(db_session, queued.id, Receiver(BROKEN))
    retried = client.post(f"{BASE}/deliveries/{queued.id}/retry", headers=admin)

    assert retried.status_code == 202 and retried.json()["status"] == "queued" and retried.json()["attempts"] == 0
    assert retried.json()["error"] is None
    run_attempt(db_session, queued.id, Receiver(OK))
    db_session.refresh(queued)
    assert queued.status == "delivered"
    assert client.post(f"{BASE}/deliveries/999/retry", headers=admin).status_code == 404


def test_the_delivery_list_is_newest_first_and_paged(client, admin, db_session, make_business):
    hook = make_hook(client, admin).json()
    for index in range(3):
        make_business(f"Shop {index}", phones=[f"030{index} 1112223"])
    run_attempt(db_session, deliveries(db_session)[0].id, Receiver(OK))

    page = client.get(f"{BASE}/{hook['id']}/deliveries", headers=admin, params={"limit": 2}).json()
    rest = client.get(f"{BASE}/{hook['id']}/deliveries", headers=admin, params={"limit": 2, "page": 2}).json()

    assert page["count"] == 3 and len(page["data"]) == 2 and len(rest["data"]) == 1
    assert [d["id"] for d in page["data"]] == sorted((d["id"] for d in page["data"]), reverse=True)
    assert rest["data"][0]["status"] == "delivered" and rest["data"][0]["next_attempt_at"] is None
    assert client.get(f"{BASE}/999/deliveries", headers=admin).status_code == 404


def test_waiting_retries_come_back_by_themselves_once_due(client, admin, db_session, make_business):
    make_hook(client, admin)
    make_business("Al Noor Solar", phones=["0300 4438424"])
    (queued,) = deliveries(db_session)
    db_session.query(Job).delete()
    run_attempt(db_session, queued.id, Receiver(BROKEN))
    handlers = {JobKind.WEBHOOK: delivery.JOB_HANDLER}

    assert delivery.JOB_HANDLER.queued_ids(db_session) == []
    assert jobs_service.adopt_orphans(db_session, handlers) == 0

    queued.next_attempt_at = datetime.now(UTC) - timedelta(seconds=1)
    db_session.commit()

    assert delivery.JOB_HANDLER.queued_ids(db_session) == [queued.id]
    assert jobs_service.adopt_orphans(db_session, handlers) == 1
    assert db_session.query(Job).filter_by(kind="webhook", ref_id=queued.id, status="queued").count() == 1


def test_an_interrupted_attempt_is_tried_again_or_given_up(client, admin, db_session, make_business):
    make_hook(client, admin)
    make_business("First Solar", phones=["0300 1111111"])
    make_business("Second Solar", phones=["0300 2222222"])
    first, second = deliveries(db_session)
    first.status = second.status = "running"
    db_session.commit()

    assert delivery.JOB_HANDLER.running_ids(db_session) == [first.id, second.id]
    assert delivery.recover_delivery(db_session, first.id, True) is True
    assert delivery.recover_delivery(db_session, second.id, False) is False

    db_session.refresh(first)
    db_session.refresh(second)
    assert first.status == "queued" and second.status == "failed" and "Interrupted" in second.error
    assert delivery.recover_delivery(db_session, first.id, True) is False


def test_the_real_sender_posts_json_and_does_not_follow_redirects(monkeypatch):
    seen = {}

    def fake_post(url, content, headers, timeout, follow_redirects):
        seen.update(url=url, content=content, headers=headers, timeout=timeout, follow_redirects=follow_redirects)
        return httpx.Response(204)

    monkeypatch.setattr(httpx, "post", fake_post)

    result = delivery.send_request(URL, {"X-Test": "1"}, b"{}")

    assert result == SendResult(204, None)
    assert seen["follow_redirects"] is False and seen["timeout"] == 10.0 and seen["content"] == b"{}"


def test_the_real_sender_reports_errors_without_leaking_details(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: httpx.Response(301, headers={"Location": "https://elsewhere"}))
    assert delivery.send_request(URL, {}, b"{}") == SendResult(301, "HTTP 301")

    monkeypatch.setattr(httpx, "post", lambda *a, **k: httpx.Response(503))
    assert delivery.send_request(URL, {}, b"{}") == SendResult(503, "HTTP 503")

    def timeout(*args, **kwargs):
        raise httpx.ConnectTimeout("took too long to reach https://hooks.example.com/in?token=secret")

    monkeypatch.setattr(httpx, "post", timeout)
    result = delivery.send_request(URL, {}, b"{}")
    assert result == SendResult(None, "The request failed (ConnectTimeout)") and "secret" not in result.error


def test_the_real_sender_refuses_a_private_address_without_connecting(monkeypatch):
    monkeypatch.setattr(service, "resolve_host", lambda host: ["10.0.0.7"])
    calls = []
    monkeypatch.setattr(httpx, "post", lambda *a, **k: calls.append(1))

    result = delivery.send_request(URL, {}, b"{}")

    assert calls == [] and result.status_code is None and "not a public address" in result.error


def test_old_finished_deliveries_are_cleared_but_waiting_ones_are_kept(client, admin, db_session, make_business):
    make_hook(client, admin)
    for index in range(3):
        make_business(f"Shop {index}", phones=[f"030{index} 1112223"])
    done, failed, waiting = deliveries(db_session)
    done.status, failed.status = "delivered", "failed"
    old = datetime.now(UTC) - timedelta(days=31)
    for row in (done, failed, waiting):
        row.created_at = old
    db_session.commit()

    assert service.prune(db_session) == 2
    assert [d.id for d in deliveries(db_session)] == [waiting.id]


def test_a_webhook_url_is_checked_again_when_sending(client, admin, db_session, make_business, monkeypatch):
    make_hook(client, admin)
    make_business("Al Noor Solar", phones=["0300 4438424"])
    (queued,) = deliveries(db_session)
    monkeypatch.setattr(service, "resolve_host", lambda host: ["192.168.0.9"])

    delivery.attempt(db_session, queued.id)

    db_session.refresh(queued)
    assert queued.status == "queued" and "not a public address" in queued.error
