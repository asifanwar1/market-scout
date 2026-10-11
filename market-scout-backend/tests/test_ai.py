from datetime import UTC, datetime, timedelta

import pytest

from app.core.ai.analyzer import AiError, AiStopError, AnalysisOutcome, AnalysisPayload
from app.core.ai.models import cost_usd, get_model
from app.core.config import settings
from app.core.crypto import decrypt_secret
from app.core.scouting.enrichment.website import EnrichmentError, WebsiteText
from app.features.ai import service
from app.features.ai.models import AiBatch, AiUsage, LeadAiResult
from app.features.businesses.models import BusinessClassification
from app.features.jobs.models import Job
from app.features.pipeline.models import LeadActivity
from app.features.sheets.models import AppSetting

AI = "/api/v1/ai"
LEADS = "/api/v1/businesses"
KEY = "sk-ant-test-key-1234"
PAGE = "We design, supply and install solar systems for homes and small shops across Lahore. " * 5
OPUS = get_model("claude-opus-5-5")
HAIKU = get_model("claude-haiku-4-5")


def payload(slug="dealer", fit=80, confidence="high", **overrides) -> AnalysisPayload:
    data = {
        "summary": "Sells and installs solar for homes.", "segment_slug": slug, "segment_reason": "Says it supplies and installs.",
        "fit_score": fit, "fit_reason": "A small shop that quotes by hand.", "confidence": confidence,
    }
    data.update(overrides)
    return AnalysisPayload(**data)


def ok(fit=80, slug="dealer", input_tokens=1000, output_tokens=100, **overrides) -> AnalysisOutcome:
    return AnalysisOutcome(status="ok", payload=payload(slug, fit, **overrides), input_tokens=input_tokens, output_tokens=output_tokens)


class FakeAnalyzer:
    def __init__(self, outcomes=None, stop_at=None, key_error=None):
        self.outcomes = list(outcomes or [])
        self.stop_at = stop_at
        self.key_error = key_error
        self.calls = []

    def analyze(self, brief, segments, ideal_customer):
        self.calls.append((brief, segments, ideal_customer))
        if self.stop_at is not None and len(self.calls) == self.stop_at:
            raise AiStopError("Anthropic rejected the API key.")
        return self.outcomes.pop(0) if self.outcomes else ok()

    def check_key(self):
        if self.key_error:
            raise AiError(self.key_error)


class FakeEnricher:
    def __init__(self, pages=None, default=None):
        self.pages = pages or {}
        self.default = default if default is not None else WebsiteText(text=PAGE, pages_read=2, truncated=False)
        self.requested = []

    def read_text(self, url, max_chars):
        self.requested.append(url)
        result = self.pages.get(url, self.default)
        if isinstance(result, Exception):
            raise result
        return result


@pytest.fixture()
def admin(admin_user, auth_headers):
    return auth_headers(admin_user)


@pytest.fixture()
def sales(sales_user, auth_headers):
    return auth_headers(sales_user)


@pytest.fixture()
def ready(client, admin):
    response = client.put(f"{AI}/settings", headers=admin, json={"api_key": KEY, "is_enabled": True})
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture()
def lead(make_business):
    return make_business("Noor Solar", website="https://noor.pk", phones=["0300 1111111"])


def run(db_session, batch_id, analyzer=None, enricher=None):
    analyzer = analyzer or FakeAnalyzer()
    enricher = enricher or FakeEnricher()
    service.run_batch(db_session, batch_id, analyzer_factory=lambda key, model: analyzer, enricher_factory=lambda: enricher)
    return db_session.get(AiBatch, batch_id)


def analyze(client, headers, profile, leads, **extra):
    response = client.post(f"{AI}/analyze", headers=headers, json={"business_ids": [item.id for item in leads], "profile_id": profile.id, **extra})
    assert response.status_code == 201, response.text
    return response.json()


def detail(client, headers, lead):
    return client.get(f"{LEADS}/{lead.id}", headers=headers).json()


def test_a_fresh_install_is_switched_off_with_the_default_model_and_budget(client, admin):
    body = client.get(f"{AI}/settings", headers=admin).json()

    assert body["is_enabled"] is False and body["has_key"] is False and body["key_hint"] is None
    assert body["model"] == "claude-opus-5-5" and body["monthly_budget_usd"] == 5.0
    assert body["spent_this_month_usd"] == 0 and body["remaining_usd"] == 5.0 and body["analyses_this_month"] == 0
    assert {m["id"] for m in body["models"]} == {"claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-4-5"}
    assert all(m["input_per_mtok_usd"] > 0 and m["output_per_mtok_usd"] > 0 for m in body["models"])


def test_the_settings_are_for_admins_but_anyone_can_see_whether_the_assistant_is_ready(client, sales):
    assert client.get(f"{AI}/settings", headers=sales).status_code == 403
    assert client.put(f"{AI}/settings", headers=sales, json={"is_enabled": True}).status_code == 403
    assert client.get(f"{AI}/status", headers=sales).status_code == 200


def test_a_saved_key_is_stored_encrypted_and_never_shown_again(client, admin, db_session):
    body = client.put(f"{AI}/settings", headers=admin, json={"api_key": f"  {KEY}  ", "is_enabled": True}).json()

    assert body["has_key"] and body["is_enabled"] and body["key_source"] == "saved" and body["key_hint"] == "…1234"
    assert KEY not in client.get(f"{AI}/settings", headers=admin).text
    stored = db_session.get(AppSetting, "ai").value
    assert KEY not in str(stored) and decrypt_secret(stored["encrypted_key"]) == KEY


def test_it_cannot_be_switched_on_without_a_key(client, admin):
    response = client.put(f"{AI}/settings", headers=admin, json={"is_enabled": True})

    assert response.status_code == 400 and "API key" in response.json()["detail"]


def test_a_key_set_on_the_server_counts_as_a_key(client, admin, monkeypatch):
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "server-key-98765")

    body = client.put(f"{AI}/settings", headers=admin, json={"is_enabled": True}).json()

    assert body["has_key"] and body["key_source"] == "environment" and body["key_hint"] == "…8765" and body["is_enabled"]


def test_removing_the_saved_key_switches_the_assistant_off(client, admin, ready):
    body = client.put(f"{AI}/settings", headers=admin, json={"clear_api_key": True}).json()

    assert body["has_key"] is False and body["is_enabled"] is False


def test_the_model_and_budget_can_be_changed_but_only_to_sensible_values(client, admin):
    body = client.put(f"{AI}/settings", headers=admin, json={"model": "claude-haiku-4-5", "monthly_budget_usd": 12.5}).json()

    assert body["model"] == "claude-haiku-4-5" and body["monthly_budget_usd"] == 12.5 and body["remaining_usd"] == 12.5
    assert client.put(f"{AI}/settings", headers=admin, json={"model": "gpt-4"}).status_code == 400
    assert client.put(f"{AI}/settings", headers=admin, json={"model": None}).status_code == 400
    assert client.put(f"{AI}/settings", headers=admin, json={"monthly_budget_usd": -1}).status_code == 422
    assert client.put(f"{AI}/settings", headers=admin, json={"monthly_budget_usd": None}).status_code == 400
    assert client.put(f"{AI}/settings", headers=admin, json={"api_key": "short"}).status_code == 422
    assert client.put(f"{AI}/settings", headers=admin, json={"surprise": 1}).status_code == 422


def test_the_key_test_reports_what_is_wrong_or_that_it_works(client, admin, ready, monkeypatch):
    monkeypatch.setattr(service, "_default_analyzer", lambda key, model: FakeAnalyzer())
    assert client.post(f"{AI}/settings/test", headers=admin).json() == {"ok": True, "message": "The key works with Claude Opus 5.5."}

    monkeypatch.setattr(service, "_default_analyzer", lambda key, model: FakeAnalyzer(key_error="Anthropic rejected the API key."))
    assert client.post(f"{AI}/settings/test", headers=admin).json() == {"ok": False, "message": "Anthropic rejected the API key."}


def test_testing_without_a_key_says_so(client, admin):
    body = client.post(f"{AI}/settings/test", headers=admin).json()

    assert body["ok"] is False and "no Anthropic API key" in body["message"]


def test_the_status_explains_why_the_assistant_cannot_be_used(client, admin, sales, db_session):
    assert "switched off" in client.get(f"{AI}/status", headers=sales).json()["reason"]

    client.put(f"{AI}/settings", headers=admin, json={"api_key": KEY, "is_enabled": True})
    ready_body = client.get(f"{AI}/status", headers=sales).json()
    assert ready_body["is_ready"] is True and ready_body["reason"] is None and ready_body["model_label"] == "Claude Opus 5.5"

    client.put(f"{AI}/settings", headers=admin, json={"monthly_budget_usd": 1})
    db_session.add(AiUsage(model="claude-opus-5-5", input_tokens=1, output_tokens=1, cost_usd=1.0, status="ok"))
    db_session.commit()
    spent = client.get(f"{AI}/status", headers=sales).json()
    assert spent["is_ready"] is False and "budget is used up" in spent["reason"] and spent["remaining_usd"] == 0


def test_only_this_months_spending_counts_against_the_budget(client, admin, ready, db_session):
    last_month = datetime.now(UTC).replace(day=1) - timedelta(days=3)
    db_session.add(AiUsage(model="claude-opus-5-5", input_tokens=1, output_tokens=1, cost_usd=4.0, status="ok", created_at=last_month))
    db_session.add(AiUsage(model="claude-opus-5-5", input_tokens=1, output_tokens=1, cost_usd=1.5, status="ok"))
    db_session.commit()

    body = client.get(f"{AI}/settings", headers=admin).json()

    assert body["spent_this_month_usd"] == 1.5 and body["remaining_usd"] == 3.5 and body["analyses_this_month"] == 1


def test_the_estimate_counts_what_would_be_read_and_prices_the_worst_case(client, admin, ready, seeded_profile, make_business, lead, db_session):
    no_site = make_business("No Site Solar")
    estimate = client.post(f"{AI}/estimate", headers=admin, json={"business_ids": [lead.id, no_site.id], "profile_id": seeded_profile.id}).json()

    per_lead = service.max_cost_per_lead(OPUS, seeded_profile)
    assert estimate["leads"] == 2 and estimate["to_analyze"] == 1 and estimate["without_website"] == 1 and estimate["already_analyzed"] == 0
    assert estimate["estimated_cost_usd"] == pytest.approx(round(per_lead, 4), abs=1e-4)
    assert estimate["remaining_usd"] == 5.0 and estimate["within_budget"] is True and estimate["model_label"] == "Claude Opus 5.5"
    assert any("without a website" in warning for warning in estimate["warnings"])


def test_the_estimate_skips_leads_already_analysed_unless_asked_to_repeat(client, admin, ready, seeded_profile, lead, db_session):
    batch = analyze(client, admin, seeded_profile, [lead])
    run(db_session, batch["id"])
    body = {"business_ids": [lead.id], "profile_id": seeded_profile.id}

    skipped = client.post(f"{AI}/estimate", headers=admin, json=body).json()
    repeated = client.post(f"{AI}/estimate", headers=admin, json={**body, "refresh": True}).json()

    assert skipped["to_analyze"] == 0 and skipped["already_analyzed"] == 1 and skipped["estimated_cost_usd"] == 0
    assert repeated["to_analyze"] == 1 and repeated["already_analyzed"] == 0


def test_the_estimate_warns_when_the_worst_case_is_over_budget(client, admin, ready, seeded_profile, lead):
    client.put(f"{AI}/settings", headers=admin, json={"monthly_budget_usd": 0.001})

    estimate = client.post(f"{AI}/estimate", headers=admin, json={"business_ids": [lead.id], "profile_id": seeded_profile.id}).json()

    assert estimate["within_budget"] is False and any("budget" in warning for warning in estimate["warnings"])


def test_the_estimate_uses_the_chosen_models_prices(client, admin, ready, seeded_profile, lead):
    body = {"business_ids": [lead.id], "profile_id": seeded_profile.id}
    opus = client.post(f"{AI}/estimate", headers=admin, json=body).json()["estimated_cost_usd"]
    client.put(f"{AI}/settings", headers=admin, json={"model": "claude-haiku-4-5"})
    haiku = client.post(f"{AI}/estimate", headers=admin, json=body).json()

    assert haiku["model_label"] == "Claude Haiku 4.5" and 0 < haiku["estimated_cost_usd"] < opus


@pytest.mark.parametrize("body", [{"business_ids": [], "profile_id": 1}, {"business_ids": list(range(1, 102)), "profile_id": 1}, {"business_ids": [1]}])
def test_estimates_and_batches_need_a_sensible_request(client, admin, ready, body):
    assert client.post(f"{AI}/estimate", headers=admin, json=body).status_code == 422
    assert client.post(f"{AI}/analyze", headers=admin, json=body).status_code == 422


def test_an_unknown_profile_is_not_found(client, admin, ready, lead):
    assert client.post(f"{AI}/estimate", headers=admin, json={"business_ids": [lead.id], "profile_id": 999999}).status_code == 404
    assert client.post(f"{AI}/analyze", headers=admin, json={"business_ids": [lead.id], "profile_id": 999999}).status_code == 404


def test_nothing_can_be_analysed_until_the_assistant_is_set_up(client, sales, seeded_profile, lead):
    response = client.post(f"{AI}/analyze", headers=sales, json={"business_ids": [lead.id], "profile_id": seeded_profile.id})

    assert response.status_code == 400 and "switched off" in response.json()["detail"]


def test_a_batch_starts_queued_and_unknown_leads_are_not_found(client, sales, ready, seeded_profile, lead):
    body = analyze(client, sales, seeded_profile, [lead])

    assert body["status"] == "queued" and body["total"] == 1 and body["done"] == 0
    assert client.get(f"{AI}/batches/{body['id']}", headers=sales).json()["id"] == body["id"]
    assert client.get(f"{AI}/batches/999999", headers=sales).status_code == 404
    gone = client.post(f"{AI}/analyze", headers=sales, json={"business_ids": [999999], "profile_id": seeded_profile.id})
    assert gone.status_code == 404


def test_analysing_a_lead_stores_the_assessment_the_cost_and_shows_it_on_the_lead(client, admin, ready, seeded_profile, lead, db_session):
    client.put(f"/api/v1/profiles/{seeded_profile.id}", headers=admin, json={"ideal_customer": "  Small shops that quote by hand  "})
    analyzer = FakeAnalyzer([ok(fit=88, slug="installer", input_tokens=2000, output_tokens=300)])
    batch = analyze(client, admin, seeded_profile, [lead])

    finished = run(db_session, batch["id"], analyzer)

    brief, segments, ideal = analyzer.calls[0]
    assert brief.name == "Noor Solar" and brief.city == "Lahore" and brief.website == "https://noor.pk" and "solar systems" in brief.page_text
    assert ideal == "Small shops that quote by hand" and {s.slug for s in segments} >= {"dealer", "installer"}
    assert (finished.status, finished.total, finished.done, finished.analyzed, finished.skipped, finished.failed) == ("completed", 1, 1, 1, 0, 0)
    expected_cost = cost_usd(OPUS, 2000, 300)
    assert finished.spent_usd == pytest.approx(expected_cost)
    usage = db_session.query(AiUsage).one()
    assert (usage.input_tokens, usage.output_tokens, usage.status) == (2000, 300, "ok") and usage.cost_usd == pytest.approx(expected_cost)

    ai = detail(client, admin, lead)["ai"]
    assert ai["status"] == "ok" and ai["fit_score"] == 88 and ai["segment_slug"] == "installer" and ai["segment_name"] == "Installer"
    assert ai["summary"] == "Sells and installs solar for homes." and ai["confidence"] == "high" and ai["model"] == "claude-opus-5-5"
    assert ai["pages_read"] == 2 and ai["truncated"] is False and ai["error"] is None and ai["current_segment_slug"] == "dealer"
    row = next(item for item in client.get(f"{LEADS}/?profile_id={seeded_profile.id}", headers=admin).json()["data"] if item["id"] == lead.id)
    assert row["ai_fit"] == 88
    settings_body = client.get(f"{AI}/settings", headers=admin).json()
    assert settings_body["spent_this_month_usd"] == pytest.approx(expected_cost, abs=1e-4) and settings_body["analyses_this_month"] == 1


def test_a_lead_nobody_analysed_has_no_assessment(client, admin, seeded_profile, lead):
    assert detail(client, admin, lead)["ai"] is None
    row = next(item for item in client.get(f"{LEADS}/?profile_id={seeded_profile.id}", headers=admin).json()["data"] if item["id"] == lead.id)
    assert row["ai_fit"] is None


def test_a_lead_without_a_website_is_skipped_for_free_and_says_why(client, admin, ready, seeded_profile, make_business, db_session):
    no_site = make_business("No Site Solar")
    analyzer = FakeAnalyzer()

    batch = run(db_session, analyze(client, admin, seeded_profile, [no_site])["id"], analyzer)

    assert analyzer.calls == [] and (batch.skipped, batch.analyzed) == (1, 0) and db_session.query(AiUsage).count() == 0
    ai = detail(client, admin, no_site)["ai"]
    assert ai["status"] == "no_text" and "no website" in ai["error"] and ai["fit_score"] is None


@pytest.mark.parametrize(
    ("page", "expected"),
    [
        (EnrichmentError("HTTP 404"), "Couldn't read the website: HTTP 404"),
        (WebsiteText(blocked_by_robots=True), "robots.txt"),
        (WebsiteText(text="Coming soon", pages_read=1), "too little text"),
    ],
)
def test_a_site_that_cannot_be_read_is_skipped_for_free_with_the_reason(client, admin, ready, seeded_profile, lead, db_session, page, expected):
    analyzer = FakeAnalyzer()

    batch = run(db_session, analyze(client, admin, seeded_profile, [lead])["id"], analyzer, FakeEnricher(default=page))

    assert analyzer.calls == [] and batch.skipped == 1 and db_session.query(AiUsage).count() == 0
    assert expected in detail(client, admin, lead)["ai"]["error"] and expected in batch.error_samples[0]


def test_leads_already_analysed_are_not_paid_for_again_unless_refreshed(client, admin, ready, seeded_profile, lead, db_session):
    run(db_session, analyze(client, admin, seeded_profile, [lead])["id"], FakeAnalyzer([ok(fit=40)]))
    again = FakeAnalyzer([ok(fit=95)])

    skipped = run(db_session, analyze(client, admin, seeded_profile, [lead])["id"], again)
    assert again.calls == [] and skipped.skipped == 1 and detail(client, admin, lead)["ai"]["fit_score"] == 40

    refreshed = run(db_session, analyze(client, admin, seeded_profile, [lead], refresh=True)["id"], again)
    assert len(again.calls) == 1 and refreshed.analyzed == 1 and detail(client, admin, lead)["ai"]["fit_score"] == 95
    assert db_session.query(LeadAiResult).count() == 1


def test_a_failed_repeat_keeps_the_earlier_good_assessment(client, admin, ready, seeded_profile, lead, db_session):
    run(db_session, analyze(client, admin, seeded_profile, [lead])["id"], FakeAnalyzer([ok(fit=70)]))
    failing = FakeAnalyzer([AnalysisOutcome(status="failed", error="Anthropic returned an error (500): overloaded")])

    batch = run(db_session, analyze(client, admin, seeded_profile, [lead], refresh=True)["id"], failing)

    assert batch.failed == 1 and "overloaded" in batch.error_samples[0]
    assert detail(client, admin, lead)["ai"]["status"] == "ok" and detail(client, admin, lead)["ai"]["fit_score"] == 70


def test_a_failed_first_attempt_and_a_refusal_are_recorded_and_still_cost_their_tokens(client, admin, ready, seeded_profile, make_business, lead, db_session):
    second = make_business("Second Solar", website="https://second.pk")
    outcomes = [
        AnalysisOutcome(status="declined", error="The AI declined to assess this business.", input_tokens=900, output_tokens=5),
        AnalysisOutcome(status="failed", error="The AI's answer was cut short or unreadable.", input_tokens=900, output_tokens=2000),
    ]

    batch = run(db_session, analyze(client, admin, seeded_profile, [lead, second])["id"], FakeAnalyzer(outcomes))

    assert (batch.declined, batch.failed, batch.analyzed) == (1, 1, 0)
    assert detail(client, admin, lead)["ai"]["status"] == "declined" and detail(client, admin, second)["ai"]["status"] == "failed"
    assert db_session.query(AiUsage).count() == 2 and batch.spent_usd == pytest.approx(cost_usd(OPUS, 900, 5) + cost_usd(OPUS, 900, 2000))


def test_an_unknown_segment_is_dropped_and_the_score_is_kept_in_range(client, admin, ready, seeded_profile, make_business, lead, db_session):
    other = make_business("Other Solar", website="https://other.pk")
    third = make_business("Third Solar", website="https://third.pk")
    outcomes = [ok(fit=150, slug="made-up"), ok(fit=-20, slug="unknown"), ok(fit=None)]

    run(db_session, analyze(client, admin, seeded_profile, [lead, other, third])["id"], FakeAnalyzer(outcomes))

    first, second, last = (detail(client, admin, item)["ai"] for item in (lead, other, third))
    assert first["segment_slug"] is None and first["fit_score"] == 100
    assert second["segment_slug"] is None and second["fit_score"] == 0
    assert last["fit_score"] is None and last["status"] == "ok"


def test_a_rejected_key_stops_the_batch_and_keeps_what_was_done(client, admin, ready, seeded_profile, make_business, lead, db_session):
    second = make_business("Second Solar", website="https://second.pk")
    third = make_business("Third Solar", website="https://third.pk")

    batch = run(db_session, analyze(client, admin, seeded_profile, [lead, second, third])["id"], FakeAnalyzer(stop_at=2))

    assert batch.status == "stopped" and "rejected the API key" in batch.error and (batch.analyzed, batch.done) == (1, 1)
    assert detail(client, admin, lead)["ai"] is not None and detail(client, admin, third)["ai"] is None


def test_a_batch_stops_before_it_could_go_over_the_monthly_budget(client, admin, ready, seeded_profile, make_business, lead, db_session):
    second = make_business("Second Solar", website="https://second.pk")
    per_lead = service.max_cost_per_lead(OPUS, seeded_profile)
    client.put(f"{AI}/settings", headers=admin, json={"monthly_budget_usd": per_lead * 1.001})
    analyzer = FakeAnalyzer([ok(input_tokens=1000, output_tokens=100)])

    batch = run(db_session, analyze(client, admin, seeded_profile, [lead, second])["id"], analyzer)

    assert batch.status == "stopped" and "budget" in batch.error and len(analyzer.calls) == 1 and batch.analyzed == 1


def test_a_lead_marked_do_not_contact_while_waiting_is_left_alone(client, admin, ready, seeded_profile, lead, db_session):
    batch = analyze(client, admin, seeded_profile, [lead])
    client.post(f"{LEADS}/{lead.id}/do-not-contact", headers=admin, json={})
    analyzer = FakeAnalyzer()

    finished = run(db_session, batch["id"], analyzer)

    assert analyzer.calls == [] and finished.skipped == 1 and db_session.query(LeadAiResult).count() == 0


def test_leads_can_be_sorted_and_filtered_by_ai_fit(client, admin, ready, seeded_profile, make_business, lead, db_session):
    mid = make_business("Mid Solar", website="https://mid.pk")
    low = make_business("Low Solar", website="https://low.pk")
    unread = make_business("Unread Solar")
    run(db_session, analyze(client, admin, seeded_profile, [lead, mid, low])["id"], FakeAnalyzer([ok(fit=90), ok(fit=60), ok(fit=20)]))
    query = f"profile_id={seeded_profile.id}"

    def names(extra):
        return [item["name"] for item in client.get(f"{LEADS}/?{query}&{extra}", headers=admin).json()["data"]]

    assert names("sort=ai_fit&direction=desc")[:3] == ["Noor Solar", "Mid Solar", "Low Solar"]
    assert names("sort=ai_fit&direction=asc")[0] == unread.name
    assert set(names("min_ai_fit=60")) == {"Noor Solar", "Mid Solar"}
    assert set(names("min_ai_fit=95")) == set()
    assert client.get(f"{LEADS}/?min_ai_fit=101", headers=admin).status_code == 422


def test_ai_fit_is_scoped_to_the_chosen_profile(client, admin, ready, seeded_profile, lead, db_session):
    run(db_session, analyze(client, admin, seeded_profile, [lead])["id"], FakeAnalyzer([ok(fit=77)]))
    other = client.post("/api/v1/profiles/", headers=admin, json={"name": "Other industry", "segments": [], "search_terms": []}).json()

    rows = client.get(f"{LEADS}/?profile_id={other['id']}&min_ai_fit=1", headers=admin).json()

    assert rows["count"] == 0


def test_applying_the_suggested_segment_moves_the_lead_and_logs_it(client, admin, ready, seeded_profile, lead, db_session):
    run(db_session, analyze(client, admin, seeded_profile, [lead])["id"], FakeAnalyzer([ok(slug="installer")]))

    response = client.post(f"{AI}/leads/{lead.id}/apply-segment", headers=admin, json={"profile_id": seeded_profile.id})

    assert response.status_code == 200 and response.json()["current_segment_slug"] == "installer"
    db_session.expire_all()
    classification = db_session.query(BusinessClassification).filter_by(business_id=lead.id, profile_id=seeded_profile.id).one()
    assert classification.segment_id is not None
    entry = db_session.query(LeadActivity).filter_by(business_id=lead.id, kind="segment_changed").one()
    assert (entry.from_value, entry.to_value, entry.summary) == ("Dealer", "Installer", "Applied the AI's suggestion")

    client.post(f"{AI}/leads/{lead.id}/apply-segment", headers=admin, json={"profile_id": seeded_profile.id})
    assert db_session.query(LeadActivity).filter_by(business_id=lead.id, kind="segment_changed").count() == 1


@pytest.mark.parametrize("slug", ["unknown", "made-up"])
def test_there_is_nothing_to_apply_when_the_ai_did_not_suggest_a_segment(client, admin, ready, seeded_profile, lead, db_session, slug):
    run(db_session, analyze(client, admin, seeded_profile, [lead])["id"], FakeAnalyzer([ok(slug=slug)]))

    response = client.post(f"{AI}/leads/{lead.id}/apply-segment", headers=admin, json={"profile_id": seeded_profile.id})

    assert response.status_code == 400 and "didn't suggest" in response.json()["detail"]


def test_applying_needs_a_successful_analysis_and_a_visible_lead(client, admin, ready, seeded_profile, lead):
    body = {"profile_id": seeded_profile.id}

    assert client.post(f"{AI}/leads/{lead.id}/apply-segment", headers=admin, json=body).status_code == 400
    assert client.post(f"{AI}/leads/999999/apply-segment", headers=admin, json=body).status_code == 404
    client.post(f"{LEADS}/{lead.id}/do-not-contact", headers=admin, json={})
    assert client.post(f"{AI}/leads/{lead.id}/apply-segment", headers=admin, json=body).status_code == 404


def test_a_batch_interrupted_with_tries_left_is_queued_again_and_continues_where_it_stopped(
    client, admin, ready, seeded_profile, lead, db_session
):
    batch = analyze(client, admin, seeded_profile, [lead])
    stored = db_session.get(AiBatch, batch["id"])
    stored.status, stored.done = "running", 1
    db_session.commit()

    assert service.recover_batch(db_session, stored.id, True) is True
    assert db_session.get(AiBatch, stored.id).status == "queued"

    analyzer = FakeAnalyzer()
    finished = run(db_session, stored.id, analyzer)

    assert finished.status == "completed" and analyzer.calls == []


def test_a_batch_interrupted_out_of_tries_is_marked_failed(db_session):
    running = AiBatch(status="running", business_ids=[1], total=1)
    db_session.add(running)
    db_session.commit()

    assert service.recover_batch(db_session, running.id, False) is False

    db_session.refresh(running)
    assert running.status == "failed" and "restart" in running.error


def test_recovering_a_batch_that_is_not_running_does_nothing(db_session):
    queued = AiBatch(status="queued", business_ids=[2], total=1)
    db_session.add(queued)
    db_session.commit()

    assert service.recover_batch(db_session, queued.id, True) is False
    assert service.recover_batch(db_session, 999999, True) is False
    assert db_session.get(AiBatch, queued.id).status == "queued"


def test_starting_a_batch_queues_a_job_with_it(client, admin, ready, seeded_profile, lead, db_session):
    batch = analyze(client, admin, seeded_profile, [lead])

    assert db_session.query(Job).filter_by(kind="ai_batch", ref_id=batch["id"], status="queued").count() == 1


def test_a_finished_batch_is_not_run_a_second_time(client, admin, ready, seeded_profile, lead, db_session):
    batch = analyze(client, admin, seeded_profile, [lead])
    first = run(db_session, batch["id"])
    again = FakeAnalyzer()

    second = run(db_session, batch["id"], again)

    assert first.status == "completed" and second.status == "completed" and again.calls == []


def test_a_profile_keeps_its_ideal_customer_text_trimmed_and_can_clear_it(client, admin, seeded_profile):
    url = f"/api/v1/profiles/{seeded_profile.id}"

    saved = client.put(url, headers=admin, json={"ideal_customer": "  Installers with 5-50 staff  "}).json()
    assert saved["ideal_customer"] == "Installers with 5-50 staff"
    assert client.get(url, headers=admin).json()["ideal_customer"] == "Installers with 5-50 staff"

    assert client.put(url, headers=admin, json={"ideal_customer": "   "}).json()["ideal_customer"] is None
    assert client.put(url, headers=admin, json={"ideal_customer": "x" * 2001}).status_code == 422
    created = client.post("/api/v1/profiles/", headers=admin, json={"name": "HVAC", "ideal_customer": "Small HVAC shops"}).json()
    assert created["ideal_customer"] == "Small HVAC shops"
