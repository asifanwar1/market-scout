import csv
import io

import pytest

from app.features.exports import crm

BASE = "/api/v1/exports/crm.csv"
LEADS = "/api/v1/businesses"


@pytest.fixture()
def admin(admin_user, auth_headers):
    return auth_headers(admin_user)


@pytest.fixture()
def lead(make_business):
    return make_business(
        "Al Noor Solar", phones=["0300 4438424", "042 35761234"], emails=["info@alnoor.pk", "sales@alnoor.pk"],
        website="https://www.alnoor.pk/contact", address="12 Mall Road",
    )


def read(response):
    text = response.content.decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(text)))
    return rows[0], [dict(zip(rows[0], row, strict=True)) for row in rows[1:]]


def test_it_needs_a_login(client):
    assert client.get(BASE).status_code == 401


def test_an_unknown_layout_is_refused(client, admin):
    assert client.get(BASE, headers=admin, params={"layout": "salesforce"}).status_code == 422


def test_the_default_is_the_plain_layout_and_a_download_with_a_row_count(client, lead, admin):
    response = client.get(BASE, headers=admin)

    assert response.status_code == 200 and response.headers["content-type"].startswith("text/csv")
    assert response.headers["x-row-count"] == "1"
    assert "market-scout-generic-" in response.headers["content-disposition"]
    headers, _ = read(response)
    assert headers == crm.GENERIC_HEADERS


def test_the_hubspot_layout_is_one_company_per_lead(client, lead, admin):
    client.patch(f"{LEADS}/{lead.id}", headers=admin, json={"contact_name": "Mr Khan", "lead_status": "meeting", "notes": "Wants a demo"})

    response = client.get(BASE, headers=admin, params={"layout": "hubspot"})

    headers, rows = read(response)
    assert headers == crm.HUBSPOT_HEADERS and "market-scout-hubspot-" in response.headers["content-disposition"]
    (row,) = rows
    assert row["Company name"] == "Al Noor Solar" and row["Company Domain Name"] == "alnoor.pk"
    assert row["City"] == "Lahore" and row["State/Region"] == "Punjab" and row["Country/Region"] == "Pakistan"
    assert row["Street Address"] == "12 Mall Road" and row["Description"] == "Wants a demo"
    assert row["Lifecycle Stage"] == "Opportunity" and row["Market Scout status"] == "Meeting"
    assert row["Contact Name"] == "Mr Khan" and row["Contact Email"] == "info@alnoor.pk"
    assert row["Phone Number"] == "+924235761234"
    assert row["All phone numbers"].count("+92") == 2 and row["Market Scout lead ID"] == str(lead.id)


def test_hubspot_lifecycle_stages_follow_the_lead_status(client, make_business, admin):
    statuses = ["new", "contacted", "interested", "meeting", "quoted", "customer", "not_interested"]
    for index, status in enumerate(statuses):
        lead = make_business(f"Shop {index}", phones=[f"030{index} 1112223"])
        client.patch(f"{LEADS}/{lead.id}", headers=admin, json={"lead_status": status})

    _, rows = read(client.get(BASE, headers=admin, params={"layout": "hubspot", "sort": "name", "direction": "asc"}))

    assert [row["Lifecycle Stage"] for row in rows] == [
        "Lead", "Lead", "Sales Qualified Lead", "Opportunity", "Opportunity", "Customer", "Other",
    ]


def test_the_zoho_layout_always_has_the_required_last_name(client, make_business, admin):
    named = make_business("Named Solar", phones=["0300 1111111"])
    anonymous = make_business("Anonymous Panels", phones=["0301 2222222"])
    client.patch(f"{LEADS}/{named.id}", headers=admin, json={"contact_name": "Ali Raza Khan", "lead_status": "contacted"})

    headers, rows = read(client.get(BASE, headers=admin, params={"layout": "zoho"}))

    by_company = {row["Company"]: row for row in rows}
    assert headers == crm.ZOHO_HEADERS
    assert (by_company["Named Solar"]["First Name"], by_company["Named Solar"]["Last Name"]) == ("Ali Raza", "Khan")
    assert (by_company["Anonymous Panels"]["First Name"], by_company["Anonymous Panels"]["Last Name"]) == ("", "Anonymous Panels")
    assert by_company["Named Solar"]["Lead Status"] == "Contacted" and by_company["Anonymous Panels"]["Lead Status"] == "Not Contacted"
    assert by_company["Named Solar"]["Lead Source"] == "Market Scout" and by_company["Named Solar"]["Country"] == "Pakistan"
    assert anonymous.id and all(row["Last Name"] for row in rows)


def test_zoho_splits_a_landline_and_a_mobile(client, lead, admin):
    _, (row,) = read(client.get(BASE, headers=admin, params={"layout": "zoho"}))

    assert row["Phone"].startswith("+9242") and row["Mobile"] == "+923004438424"
    assert row["Email"] == "info@alnoor.pk" and row["Website"] == "https://alnoor.pk/contact"
    assert row["Street"] == "12 Mall Road" and row["City"] == "Lahore" and row["State"] == "Punjab"


def test_a_lead_with_only_a_mobile_has_no_separate_mobile_column(client, make_business, admin):
    make_business("Mobile Only", phones=["0300 5556667"])

    _, (row,) = read(client.get(BASE, headers=admin, params={"layout": "zoho"}))

    assert row["Phone"] == "+923005556667" and row["Mobile"] == ""


def test_the_plain_layout_carries_the_deal(client, lead, admin):
    client.patch(f"{LEADS}/{lead.id}", headers=admin, json={"lead_status": "customer", "outcome": {"value": 2500, "product": "Billing"}})

    _, (row,) = read(client.get(BASE, headers=admin))

    assert row["Company"] == "Al Noor Solar" and row["Status"] == "Customer" and row["Deal outcome"] == "won"
    assert row["Deal value"] == "2500.0" and row["Deal currency"] == "USD" and row["Deal product"] == "Billing"
    assert row["Email"] == "info@alnoor.pk; sales@alnoor.pk" and row["Closed on"] != "" and row["Loss reason"] == ""
    assert row["Found by"] == "OpenStreetMap" and row["Segment"] != "" and row["Score"] != ""


def test_a_lost_deal_shows_its_reason_and_no_value(client, lead, admin):
    client.patch(f"{LEADS}/{lead.id}", headers=admin, json={"lead_status": "not_interested", "outcome": {"loss_reason": "price"}})

    _, (row,) = read(client.get(BASE, headers=admin))

    assert row["Deal outcome"] == "lost" and row["Loss reason"] == "price" and row["Deal value"] == "" and row["Deal currency"] == ""


def test_an_open_lead_has_empty_deal_columns(client, lead, admin):
    _, (row,) = read(client.get(BASE, headers=admin))

    assert (row["Deal outcome"], row["Deal value"], row["Deal product"], row["Closed on"]) == ("", "", "", "")


def test_the_same_filters_as_the_lead_list_apply(client, make_business, admin):
    make_business("With Email", phones=["0300 1111111"], emails=["a@b.pk"])
    make_business("Without Email", phones=["0301 2222222"])

    response = client.get(BASE, headers=admin, params={"layout": "generic", "has_email": True})

    _, rows = read(response)
    assert response.headers["x-row-count"] == "1" and [row["Company"] for row in rows] == ["With Email"]


def test_do_not_contact_leads_are_left_out(client, lead, make_business, admin):
    make_business("Fine Solar", phones=["0301 2222222"])
    client.post(f"{LEADS}/{lead.id}/do-not-contact", headers=admin, json={})

    _, rows = read(client.get(BASE, headers=admin))

    assert [row["Company"] for row in rows] == ["Fine Solar"]


def test_text_that_could_run_as_a_formula_is_defused(client, make_business, admin):
    lead = make_business("=HYPERLINK(\"http://evil\")", phones=["0300 1111111"])
    client.patch(f"{LEADS}/{lead.id}", headers=admin, json={"notes": "@SUM(1+1)"})

    for layout in ("generic", "hubspot", "zoho"):
        _, (row,) = read(client.get(BASE, headers=admin, params={"layout": layout}))
        assert not any(value.startswith(("=", "@")) for value in row.values()), layout


def test_an_empty_list_still_gives_a_file_with_headers(client, admin):
    response = client.get(BASE, headers=admin, params={"layout": "hubspot"})

    headers, rows = read(response)
    assert headers == crm.HUBSPOT_HEADERS and rows == [] and response.headers["x-row-count"] == "0"
