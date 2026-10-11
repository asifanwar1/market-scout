from datetime import UTC, datetime, timedelta

import pytest

from app.features.businesses.models import Business, ContactPoint
from app.features.compliance import service as compliance_service
from app.features.outreach.models import MessageTemplate, OutreachMessage
from app.features.pipeline.models import LeadActivity
from app.features.quality import duplicates

BASE = "/api/v1/outreach"
LEADS = "/api/v1/businesses"
PIPELINE = "/api/v1/pipeline"
WHATSAPP_BODY = "Hello {contact_name}, we help {business_name} in {city}."
EMAIL_SUBJECT = "Hello {business_name}"
EMAIL_BODY = "Dear {contact_name}, a short note for {business_name}."


@pytest.fixture()
def admin(admin_user, auth_headers):
    return auth_headers(admin_user)


@pytest.fixture()
def sales(sales_user, auth_headers):
    return auth_headers(sales_user)


@pytest.fixture()
def other_sales(make_user, auth_headers):
    return auth_headers(make_user("other@example.com", full_name="Other Seller"))


@pytest.fixture()
def lead(make_business):
    return make_business("Al Noor Solar", phones=["0300 4438424"], emails=["info@alnoor.pk"])


def contact(db_session, lead, kind):
    return db_session.query(ContactPoint).filter(ContactPoint.business_id == lead.id, ContactPoint.kind == kind).first()


def make_template(client, headers, name="Intro", channel="whatsapp", subject=None, body=WHATSAPP_BODY):
    payload = {"name": name, "channel": channel, "body": body}
    if subject is not None:
        payload["subject"] = subject
    return client.post(f"{BASE}/templates", headers=headers, json=payload)


def prepare(client, headers, lead, contact_point, channel="whatsapp", **extra):
    body = {
        "business_id": lead.id, "contact_id": contact_point.id, "channel": channel, "body": WHATSAPP_BODY, **extra,
    }
    return client.post(f"{BASE}/messages", headers=headers, json=body)


def decide(client, headers, message_id, sent):
    return client.post(f"{BASE}/messages/{message_id}/decision", headers=headers, json={"sent": sent})


def kinds(client, headers, lead):
    return [item["kind"] for item in client.get(f"{PIPELINE}/leads/{lead.id}/activities", headers=headers).json()["data"]]


def test_the_config_lists_the_placeholders_templates_may_use(client, sales):
    config = client.get(f"{BASE}/config", headers=sales).json()

    assert [item["key"] for item in config["placeholders"]] == ["business_name", "city", "contact_name"]
    assert config["template_channels"] == ["whatsapp", "email", "any"]
    assert config["recent_days"] == 14


def test_only_an_admin_can_create_change_or_delete_a_template(client, admin, sales):
    created = make_template(client, admin).json()

    assert make_template(client, sales, name="Mine").status_code == 403
    assert client.patch(f"{BASE}/templates/{created['id']}", headers=sales, json={"name": "Changed"}).status_code == 403
    assert client.delete(f"{BASE}/templates/{created['id']}", headers=sales).status_code == 403
    assert client.get(f"{BASE}/templates", headers=sales).json()["count"] == 1


def test_a_template_name_must_be_unique_ignoring_case(client, admin):
    make_template(client, admin, name="Intro")

    assert make_template(client, admin, name="intro").status_code == 409
    other = make_template(client, admin, name="Follow up").json()
    assert client.patch(f"{BASE}/templates/{other['id']}", headers=admin, json={"name": "INTRO"}).status_code == 409
    assert client.patch(f"{BASE}/templates/{other['id']}", headers=admin, json={"name": "Follow up"}).status_code == 200


def test_a_template_with_an_unknown_placeholder_is_refused(client, admin):
    response = make_template(client, admin, body="Hi {owner_name}")

    assert response.status_code == 400
    assert "owner_name" in response.json()["detail"] and "business_name" in response.json()["detail"]
    created = make_template(client, admin).json()
    assert client.patch(f"{BASE}/templates/{created['id']}", headers=admin, json={"body": "Hi {nope}"}).status_code == 400
    assert make_template(client, admin, name="Subject", channel="email", subject="{nope}", body="x").status_code == 400


def test_a_blank_template_is_refused(client, admin):
    assert make_template(client, admin, body="   ").status_code == 422
    assert make_template(client, admin, name=" ").status_code == 422
    created = make_template(client, admin).json()
    assert client.patch(f"{BASE}/templates/{created['id']}", headers=admin, json={}).status_code == 400
    assert client.patch(f"{BASE}/templates/{created['id']}", headers=admin, json={"body": "  "}).status_code == 400


def test_a_whatsapp_template_has_no_subject_and_an_email_one_keeps_it(client, admin):
    whatsapp = make_template(client, admin, subject="ignored").json()
    email = make_template(client, admin, name="Mail", channel="email", subject=EMAIL_SUBJECT, body=EMAIL_BODY).json()

    assert whatsapp["subject"] is None
    assert email["subject"] == EMAIL_SUBJECT
    switched = client.patch(f"{BASE}/templates/{email['id']}", headers=admin, json={"channel": "whatsapp"}).json()
    assert switched["subject"] is None


def test_the_template_list_can_be_narrowed_to_a_channel_and_includes_any(client, admin, sales):
    make_template(client, admin, name="WhatsApp one", channel="whatsapp")
    make_template(client, admin, name="Email one", channel="email", body=EMAIL_BODY)
    make_template(client, admin, name="Either", channel="any")

    def names(channel):
        return [t["name"] for t in client.get(f"{BASE}/templates", headers=sales, params={"channel": channel}).json()["data"]]

    assert names("whatsapp") == ["Either", "WhatsApp one"]
    assert names("email") == ["Either", "Email one"]
    assert len(names("any")) == 3


def test_a_missing_template_is_404(client, admin):
    assert client.patch(f"{BASE}/templates/999", headers=admin, json={"name": "x2"}).status_code == 404
    assert client.delete(f"{BASE}/templates/999", headers=admin).status_code == 404


def test_the_preview_fills_in_the_business_name_city_and_a_fallback_for_the_contact(client, lead, admin, sales):
    template = make_template(client, admin).json()

    response = client.post(f"{BASE}/preview", headers=sales, json={"business_id": lead.id, "template_id": template["id"]})

    assert response.status_code == 200
    assert response.json() == {"subject": None, "body": "Hello there, we help Al Noor Solar in Lahore."}


def test_the_preview_uses_the_saved_contact_person(client, lead, admin, sales):
    template = make_template(client, admin).json()
    client.patch(f"{LEADS}/{lead.id}", headers=sales, json={"contact_name": "  Mr Khan "})

    body = client.post(f"{BASE}/preview", headers=sales, json={"business_id": lead.id, "template_id": template["id"]}).json()["body"]

    assert body == "Hello Mr Khan, we help Al Noor Solar in Lahore."


def test_the_preview_accepts_edited_text_in_place_of_the_template(client, lead, admin, sales):
    template = make_template(client, admin).json()

    edited = client.post(
        f"{BASE}/preview", headers=sales, json={"business_id": lead.id, "template_id": template["id"], "body": "Salam {business_name}"}
    )
    adhoc = client.post(f"{BASE}/preview", headers=sales, json={"business_id": lead.id, "body": "Hi {city}"})

    assert edited.json()["body"] == "Salam Al Noor Solar"
    assert adhoc.json()["body"] == "Hi Lahore"


def test_the_preview_needs_some_text_and_only_known_placeholders(client, lead, sales):
    assert client.post(f"{BASE}/preview", headers=sales, json={"business_id": lead.id}).status_code == 400
    assert client.post(f"{BASE}/preview", headers=sales, json={"business_id": lead.id, "body": "  "}).status_code == 400
    assert client.post(f"{BASE}/preview", headers=sales, json={"business_id": lead.id, "body": "{nope}"}).status_code == 400
    assert client.post(f"{BASE}/preview", headers=sales, json={"business_id": 999, "body": "x"}).status_code == 404
    assert client.post(f"{BASE}/preview", headers=sales, json={"business_id": lead.id, "template_id": 999}).status_code == 404


def test_a_lead_without_a_city_gets_the_fallback_wording(client, make_business, db_session, sales):
    lead = make_business("Nowhere Solar", phones=["0300 1112223"])
    db_session.query(Business).filter(Business.id == lead.id).update({Business.geography_id: None})
    db_session.commit()

    body = client.post(f"{BASE}/preview", headers=sales, json={"business_id": lead.id, "body": "Hi {city}"}).json()["body"]

    assert body == "Hi your city"


def test_opening_whatsapp_builds_a_chat_link_and_logs_nothing_until_confirmed(client, lead, db_session, sales):
    phone = contact(db_session, lead, "phone")

    response = prepare(client, sales, lead, phone, body="Hello {business_name} & co?")

    assert response.status_code == 201
    data = response.json()
    assert data["link"] == "https://wa.me/923004438424?text=Hello%20Al%20Noor%20Solar%20%26%20co%3F"
    assert data["body"] == "Hello Al Noor Solar & co?" and data["to_value"] == "+923004438424"
    assert data["last_sent_at"] is None
    assert kinds(client, sales, lead) == []
    assert client.get(f"{LEADS}/{lead.id}", headers=sales).json()["lead_status"] == "new"
    row = db_session.get(OutreachMessage, data["id"])
    assert row.status == "opened" and row.decided_at is None


def test_opening_the_mail_app_builds_a_mailto_link_with_subject_and_body(client, lead, db_session, sales):
    email = contact(db_session, lead, "email")

    response = prepare(
        client, sales, lead, email, channel="email", subject=EMAIL_SUBJECT, body="Line one\nLine two for {business_name}"
    )

    assert response.status_code == 201
    assert response.json()["link"] == (
        "mailto:info@alnoor.pk?subject=Hello%20Al%20Noor%20Solar&body=Line%20one%0ALine%20two%20for%20Al%20Noor%20Solar"
    )
    assert response.json()["subject"] == "Hello Al Noor Solar"


def test_a_whatsapp_message_ignores_a_subject(client, lead, db_session, sales):
    data = prepare(client, sales, lead, contact(db_session, lead, "phone"), subject="Ignored").json()

    assert data["subject"] is None


def test_confirming_a_send_logs_it_on_the_timeline_and_moves_a_new_lead_to_contacted(client, lead, db_session, sales):
    data = prepare(client, sales, lead, contact(db_session, lead, "phone"), body="Hello {business_name}").json()

    response = decide(client, sales, data["id"], True)

    assert response.status_code == 200
    assert response.json()["status"] == "sent" and response.json()["decided_at"] is not None
    timeline = client.get(f"{PIPELINE}/leads/{lead.id}/activities", headers=sales).json()["data"]
    assert [entry["kind"] for entry in timeline] == ["status_change", "whatsapp"]
    whatsapp = next(entry for entry in timeline if entry["kind"] == "whatsapp")
    assert whatsapp["summary"] == "Hello Al Noor Solar"
    assert client.get(f"{LEADS}/{lead.id}", headers=sales).json()["lead_status"] == "contacted"


def test_a_confirmed_email_is_logged_with_its_subject_and_template(client, lead, admin, db_session, sales):
    template = make_template(client, admin, name="Mail", channel="email", subject=EMAIL_SUBJECT, body=EMAIL_BODY).json()
    data = prepare(
        client, sales, lead, contact(db_session, lead, "email"), channel="email", template_id=template["id"],
        subject=EMAIL_SUBJECT, body=EMAIL_BODY,
    ).json()

    decide(client, sales, data["id"], True)

    entry = next(e for e in client.get(f"{PIPELINE}/leads/{lead.id}/activities", headers=sales).json()["data"] if e["kind"] == "email")
    assert entry["summary"] == 'Template "Mail"\nSubject: Hello Al Noor Solar\nDear there, a short note for Al Noor Solar.'


def test_not_sending_logs_no_activity_and_leaves_the_status_alone(client, lead, db_session, sales):
    data = prepare(client, sales, lead, contact(db_session, lead, "phone")).json()

    response = decide(client, sales, data["id"], False)

    assert response.json()["status"] == "not_sent"
    assert kinds(client, sales, lead) == []
    assert client.get(f"{LEADS}/{lead.id}", headers=sales).json()["lead_status"] == "new"


def test_a_lead_further_along_is_not_moved_back_to_contacted(client, lead, db_session, sales):
    client.patch(f"{LEADS}/{lead.id}", headers=sales, json={"lead_status": "interested"})
    data = prepare(client, sales, lead, contact(db_session, lead, "phone")).json()

    decide(client, sales, data["id"], True)

    assert client.get(f"{LEADS}/{lead.id}", headers=sales).json()["lead_status"] == "interested"
    assert kinds(client, sales, lead).count("status_change") == 1


def test_a_message_can_only_be_marked_once(client, lead, db_session, sales):
    data = prepare(client, sales, lead, contact(db_session, lead, "phone")).json()
    decide(client, sales, data["id"], False)

    assert decide(client, sales, data["id"], True).status_code == 409
    assert kinds(client, sales, lead) == []


def test_only_the_writer_or_an_admin_can_mark_a_message(client, lead, db_session, sales, other_sales, admin):
    first = prepare(client, sales, lead, contact(db_session, lead, "phone")).json()
    second = prepare(client, sales, lead, contact(db_session, lead, "phone")).json()

    assert decide(client, other_sales, first["id"], True).status_code == 403
    assert decide(client, admin, first["id"], True).status_code == 200
    assert decide(client, sales, second["id"], False).status_code == 200
    assert decide(client, sales, 999, True).status_code == 404


def test_a_second_message_warns_about_a_recent_send(client, lead, db_session, sales, sales_user):
    first = prepare(client, sales, lead, contact(db_session, lead, "phone")).json()
    decide(client, sales, first["id"], True)

    second = prepare(client, sales, lead, contact(db_session, lead, "phone")).json()

    assert second["last_sent_at"] is not None
    assert second["last_sent_by"] == {"id": sales_user.id, "full_name": sales_user.full_name}


def test_a_send_older_than_the_warning_window_is_not_mentioned(client, lead, db_session, sales):
    first = prepare(client, sales, lead, contact(db_session, lead, "phone")).json()
    decide(client, sales, first["id"], True)
    db_session.query(OutreachMessage).update({OutreachMessage.decided_at: datetime.now(UTC) - timedelta(days=15)})
    db_session.commit()

    assert prepare(client, sales, lead, contact(db_session, lead, "phone")).json()["last_sent_at"] is None


def test_an_unsent_message_does_not_count_as_a_recent_send(client, lead, db_session, sales):
    first = prepare(client, sales, lead, contact(db_session, lead, "phone")).json()
    decide(client, sales, first["id"], False)

    assert prepare(client, sales, lead, contact(db_session, lead, "phone")).json()["last_sent_at"] is None


def test_an_email_whose_domain_cannot_receive_mail_is_refused(client, lead, db_session, sales):
    email = contact(db_session, lead, "email")
    email.check_status = "bad"
    db_session.commit()

    response = prepare(client, sales, lead, email, channel="email", body="x")

    assert response.status_code == 400 and "can't receive mail" in response.json()["detail"]
    assert db_session.query(OutreachMessage).count() == 0


def test_the_contact_must_suit_the_channel_and_belong_to_the_lead(client, lead, make_business, db_session, sales):
    stranger = make_business("Other Solar", phones=["0301 9998887"], emails=["hi@other.pk"])

    assert prepare(client, sales, lead, contact(db_session, lead, "email"), channel="whatsapp").status_code == 400
    assert prepare(client, sales, lead, contact(db_session, lead, "phone"), channel="email").status_code == 400
    assert prepare(client, sales, lead, contact(db_session, stranger, "phone")).status_code == 400
    assert db_session.query(OutreachMessage).count() == 0


def test_a_whatsapp_contact_can_be_used_for_whatsapp(client, make_business, db_session, sales):
    lead = make_business("Chat Solar", phones=["0300 5556667"])
    db_session.add(ContactPoint(business_id=lead.id, kind="whatsapp", value="+923005556667", source_key="manual"))
    db_session.commit()

    response = prepare(client, sales, lead, contact(db_session, lead, "whatsapp"))

    assert response.status_code == 201 and response.json()["link"].startswith("https://wa.me/923005556667?text=")


def test_a_template_for_the_other_channel_is_refused(client, lead, admin, db_session, sales):
    template = make_template(client, admin, name="Mail", channel="email", body=EMAIL_BODY).json()

    response = prepare(client, sales, lead, contact(db_session, lead, "phone"), template_id=template["id"])

    assert response.status_code == 400 and "email" in response.json()["detail"]
    template_any = make_template(client, admin, name="Either", channel="any").json()
    assert prepare(client, sales, lead, contact(db_session, lead, "phone"), template_id=template_any["id"]).status_code == 201


def test_unknown_placeholders_and_missing_templates_are_refused_when_preparing(client, lead, db_session, sales):
    phone = contact(db_session, lead, "phone")

    assert prepare(client, sales, lead, phone, body="Hi {nope}").status_code == 400
    assert prepare(client, sales, lead, phone, template_id=999).status_code == 404
    blank = {"business_id": lead.id, "contact_id": phone.id, "channel": "whatsapp", "body": " "}
    assert client.post(f"{BASE}/messages", headers=sales, json=blank).status_code == 422


def test_a_do_not_contact_lead_cannot_be_messaged_or_listed(client, lead, db_session, sales):
    phone = contact(db_session, lead, "phone")
    opened = prepare(client, sales, lead, phone).json()
    compliance_service.block_business(db_session, lead.id, None, 1)
    db_session.commit()

    assert prepare(client, sales, lead, phone).status_code == 404
    assert decide(client, sales, opened["id"], True).status_code == 404
    assert client.post(f"{BASE}/preview", headers=sales, json={"business_id": lead.id, "body": "x"}).status_code == 404
    assert client.get(f"{BASE}/messages", headers=sales).json()["count"] == 0


def test_the_send_log_lists_newest_first_and_can_be_filtered(client, lead, make_business, db_session, sales, other_sales):
    second = make_business("Bright Solar", phones=["0302 3334445"])
    one = prepare(client, sales, lead, contact(db_session, lead, "phone")).json()
    two = prepare(client, other_sales, second, contact(db_session, second, "phone")).json()
    decide(client, sales, one["id"], True)

    everything = client.get(f"{BASE}/messages", headers=sales).json()
    mine = client.get(f"{BASE}/messages", headers=sales, params={"mine": True}).json()
    one_lead = client.get(f"{BASE}/messages", headers=sales, params={"business_id": second.id}).json()
    sent = client.get(f"{BASE}/messages", headers=sales, params={"status": "sent"}).json()

    assert [m["id"] for m in everything["data"]] == [two["id"], one["id"]] and everything["count"] == 2
    assert [m["id"] for m in mine["data"]] == [one["id"]]
    assert [m["id"] for m in one_lead["data"]] == [two["id"]]
    assert [m["id"] for m in sent["data"]] == [one["id"]]
    first = everything["data"][1]
    assert first["business_name"] == "Al Noor Solar" and first["created_by"]["full_name"] == "Sales User"
    assert first["channel"] == "whatsapp" and first["to_value"] == "+923004438424"


def test_the_send_log_is_paged(client, lead, db_session, sales):
    phone = contact(db_session, lead, "phone")
    for _ in range(3):
        prepare(client, sales, lead, phone)

    page = client.get(f"{BASE}/messages", headers=sales, params={"limit": 2, "page": 2}).json()

    assert page["count"] == 3 and len(page["data"]) == 1


def test_deleting_a_template_keeps_the_log_of_what_was_sent(client, lead, admin, db_session, sales):
    template = make_template(client, admin).json()
    data = prepare(client, sales, lead, contact(db_session, lead, "phone"), template_id=template["id"]).json()
    decide(client, sales, data["id"], True)

    assert client.delete(f"{BASE}/templates/{template['id']}", headers=admin).status_code == 204

    row = client.get(f"{BASE}/messages", headers=sales).json()["data"][0]
    assert row["template_name"] == "Intro" and row["status"] == "sent"
    assert db_session.query(MessageTemplate).count() == 0


def test_the_contact_person_can_be_set_trimmed_and_cleared(client, lead, sales):
    saved = client.patch(f"{LEADS}/{lead.id}", headers=sales, json={"contact_name": "  Mr Khan  "}).json()
    assert saved["contact_name"] == "Mr Khan"

    cleared = client.patch(f"{LEADS}/{lead.id}", headers=sales, json={"contact_name": "  "}).json()
    assert cleared["contact_name"] is None

    assert client.patch(f"{LEADS}/{lead.id}", headers=sales, json={"contact_name": "x" * 101}).status_code == 422


def test_merging_two_leads_keeps_the_send_log_and_the_contact_person(client, make_business, db_session, sales, admin_user):
    keep = make_business("Noor Solar", phones=["0300 1111111"])
    remove = make_business("Noor Solar Traders", phones=["0300 2222222"])
    client.patch(f"{LEADS}/{remove.id}", headers=sales, json={"contact_name": "Mr Khan"})
    data = prepare(client, sales, remove, contact(db_session, remove, "phone")).json()
    decide(client, sales, data["id"], True)
    keep_id, remove_id = keep.id, remove.id

    duplicates.merge_businesses(db_session, db_session.get(Business, keep_id), db_session.get(Business, remove_id), admin_user.id)
    db_session.commit()

    assert db_session.get(OutreachMessage, data["id"]).business_id == keep_id
    assert db_session.get(Business, keep_id).contact_name == "Mr Khan"
    assert db_session.query(LeadActivity).filter(LeadActivity.business_id == keep_id, LeadActivity.kind == "whatsapp").count() == 1


def test_everything_needs_a_signed_in_user(client, lead):
    assert client.get(f"{BASE}/config").status_code == 401
    assert client.get(f"{BASE}/templates").status_code == 401
    assert client.post(f"{BASE}/messages", json={}).status_code == 401
    assert client.get(f"{BASE}/messages").status_code == 401
