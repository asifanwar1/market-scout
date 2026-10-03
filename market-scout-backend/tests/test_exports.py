import csv
import io

import pytest
from openpyxl import load_workbook

from app.features.exports.service import LEAD_HEADERS, csv_safe

URL = "/api/v1/exports/leads.csv"
XLSX_URL = "/api/v1/exports/leads.xlsx"
LEADS = "/api/v1/businesses"
COLUMN = {name: index for index, name in enumerate(LEAD_HEADERS)}


def parse(response) -> list[list[str]]:
    text = response.content.decode("utf-8")
    assert text.startswith("﻿"), "Excel needs the UTF-8 marker to read Urdu names correctly"
    return list(csv.reader(io.StringIO(text[1:])))


@pytest.fixture()
def leads(make_business):
    return {
        "noor": make_business(
            "Al Noor Solar Dealer", phones=["0300 4438424", "042 3577 1769"], emails=["info@alnoor.pk"],
            website="https://alnoor.pk", address="12 Mall Road, Lahore", review_count=20, rating=4.6,
        ),
        "bilal": make_business("Bilal Wholesale Traders", hint="wholesaler", phones=["0301 1112223"], source="google_places"),
        "quetta": make_business("Quetta Solar Works", city="quetta", hint="installer", emails=["hello@quettasolar.pk"]),
    }


def test_export_needs_a_login(client, leads):
    assert client.get(URL).status_code == 401


def test_sales_can_export(client, leads, sales_user, auth_headers):
    response = client.get(URL, headers=auth_headers(sales_user))
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["content-disposition"].startswith('attachment; filename="market-scout-leads-')
    assert response.headers["x-row-count"] == "3"


def test_header_and_a_row_per_lead_with_matching_columns(client, leads, sales_user, auth_headers):
    rows = parse(client.get(URL, headers=auth_headers(sales_user)))
    assert rows[0] == LEAD_HEADERS
    assert len(rows) == 4
    assert all(len(row) == len(LEAD_HEADERS) for row in rows)


def test_a_lead_row_carries_what_sales_needs(client, leads, seeded_profile, sales_user, auth_headers):
    rows = parse(client.get(URL, headers=auth_headers(sales_user)))
    noor = next(row for row in rows[1:] if row[COLUMN["Name"]] == "Al Noor Solar Dealer")

    assert noor[COLUMN["Lead ID"]] == str(leads["noor"].id)
    assert noor[COLUMN["Industry"]] == seeded_profile.name
    assert noor[COLUMN["Segment"]] == "Dealer"
    assert noor[COLUMN["Score"]] == "100"
    assert noor[COLUMN["Status"]] == "New"
    assert noor[COLUMN["Phone numbers"]] == "+923004438424; +924235771769"
    assert noor[COLUMN["WhatsApp chat"]] == "https://wa.me/923004438424"
    assert noor[COLUMN["Email"]] == "info@alnoor.pk"
    assert noor[COLUMN["Website"]] == "https://alnoor.pk"
    assert noor[COLUMN["City"]] == "Lahore" and noor[COLUMN["Province"]] == "Punjab"
    assert noor[COLUMN["Rating"]] == "4.6" and noor[COLUMN["Reviews"]] == "20"
    assert noor[COLUMN["Found by"]] == "OpenStreetMap"
    assert noor[COLUMN["Map"]].startswith("https://www.google.com/maps?q=")
    assert len(noor[COLUMN["First found"]]) == 10


def test_status_notes_and_assignee_show_what_sales_recorded(client, leads, sales_user, admin_user, auth_headers):
    client.patch(
        f"{LEADS}/{leads['noor'].id}", headers=auth_headers(admin_user),
        json={"lead_status": "not_interested", "notes": "Wants cash only, call after Eid", "assigned_to_id": sales_user.id},
    )
    rows = parse(client.get(URL, headers=auth_headers(sales_user)))
    noor = next(row for row in rows[1:] if row[COLUMN["Name"]] == "Al Noor Solar Dealer")

    assert noor[COLUMN["Status"]] == "Not interested"
    assert noor[COLUMN["Notes"]] == "Wants cash only, call after Eid"
    assert noor[COLUMN["Assigned to"]] == "Sales User"


def test_export_follows_the_same_filters_as_the_list(client, leads, sales_user, auth_headers):
    headers = auth_headers(sales_user)
    for query in ("has_email=true", "search=bilal", "status=contacted"):
        listed = client.get(f"{LEADS}/?{query}", headers=headers).json()
        exported = parse(client.get(f"{URL}?{query}", headers=headers))
        assert len(exported) - 1 == listed["count"], query

    only_emails = parse(client.get(f"{URL}?has_email=true", headers=headers))
    assert {row[COLUMN["Name"]] for row in only_emails[1:]} == {"Al Noor Solar Dealer", "Quetta Solar Works"}


def test_a_filter_that_matches_nothing_is_a_header_only_file(client, leads, sales_user, auth_headers):
    rows = parse(client.get(f"{URL}?status=customer", headers=auth_headers(sales_user)))
    assert rows == [LEAD_HEADERS]


def test_bad_filters_are_rejected_like_the_list_does(client, leads, sales_user, auth_headers):
    assert client.get(f"{URL}?segment=dealer", headers=auth_headers(sales_user)).status_code == 400


def test_someone_on_do_not_contact_is_never_exported(client, leads, sales_user, auth_headers):
    headers = auth_headers(sales_user)
    client.post(f"{LEADS}/{leads['noor'].id}/do-not-contact", headers=headers, json={"reason": "asked us to stop"})

    rows = parse(client.get(URL, headers=headers))

    names = {row[COLUMN["Name"]] for row in rows[1:]}
    assert "Al Noor Solar Dealer" not in names
    assert names == {"Bilal Wholesale Traders", "Quetta Solar Works"}
    assert not any("+923004438424" in cell or "info@alnoor.pk" in cell for row in rows for cell in row)


def test_a_blocked_phone_number_hides_whoever_owns_it_from_the_export(client, leads, sales_user, auth_headers):
    headers = auth_headers(sales_user)
    client.post("/api/v1/compliance/do-not-contact", headers=headers, json={"phone": "0301 1112223"})

    names = {row[COLUMN["Name"]] for row in parse(client.get(URL, headers=headers))[1:]}
    assert "Bilal Wholesale Traders" not in names


def test_a_business_named_like_a_formula_cannot_run_in_excel(client, make_business, sales_user, auth_headers):
    make_business('=HYPERLINK("http://evil.example","Click")', phones=["0300 1234567"], address="@SUM(A1)")

    row = parse(client.get(URL, headers=auth_headers(sales_user)))[1]

    assert row[COLUMN["Name"]].startswith("'=")
    assert row[COLUMN["Address"]].startswith("'@")
    assert row[COLUMN["Phone numbers"]] == "+923001234567"


def test_urdu_and_accented_names_survive(client, make_business, sales_user, auth_headers):
    make_business("سولر پاور ہاؤس Café Élan", phones=["0300 1234567"])

    row = parse(client.get(URL, headers=auth_headers(sales_user)))[1]

    assert row[COLUMN["Name"]] == "سولر پاور ہاؤس Café Élan"


def test_a_lead_with_no_details_still_exports_cleanly(client, make_business, sales_user, auth_headers):
    make_business("Ghost Energy", hint=None)
    row = parse(client.get(URL, headers=auth_headers(sales_user)))[1]
    assert row[COLUMN["Phone numbers"]] == "" and row[COLUMN["WhatsApp chat"]] == "" and row[COLUMN["Email"]] == ""


def test_the_export_is_one_row_per_lead_however_many_contacts_it_has(client, leads, sales_user, auth_headers):
    rows = parse(client.get(URL, headers=auth_headers(sales_user)))
    ids = [row[COLUMN["Lead ID"]] for row in rows[1:]]
    assert len(ids) == len(set(ids)) == 3


@pytest.mark.parametrize(
    "value, expected",
    [
        ("=1+1", "'=1+1"),
        ("@cmd", "'@cmd"),
        ("\tTab", "'\tTab"),
        ("+cmd|' /C calc'!A0", "'+cmd|' /C calc'!A0"),
        ("-2+3", "-2+3"),
        ("+923001234567", "+923001234567"),
        ("+92 300 1234567", "+92 300 1234567"),
        ("+923004438424; +924235771769", "+923004438424; +924235771769"),
        ("Al Noor", "Al Noor"),
        ("", ""),
        (42, 42),
        (None, None),
    ],
)
def test_csv_safe(value, expected):
    assert csv_safe(value) == expected


def sheet_rows(response) -> list[list]:
    workbook = load_workbook(io.BytesIO(response.content))
    return [[cell.value for cell in row] for row in workbook["Leads"].iter_rows()]


def test_excel_export_needs_a_login(client, leads):
    assert client.get(XLSX_URL).status_code == 401


def test_sales_can_export_to_excel(client, leads, sales_user, auth_headers):
    response = client.get(XLSX_URL, headers=auth_headers(sales_user))

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    assert response.headers["content-disposition"].startswith('attachment; filename="market-scout-leads-')
    assert response.headers["content-disposition"].endswith('.xlsx"')
    assert response.headers["x-row-count"] == "3"


def test_excel_export_has_the_same_rows_as_the_csv(client, leads, seeded_profile, sales_user, auth_headers):
    headers = auth_headers(sales_user)
    csv_rows = parse(client.get(URL, headers=headers))
    excel_rows = sheet_rows(client.get(XLSX_URL, headers=headers))

    assert excel_rows[0] == LEAD_HEADERS
    assert len(excel_rows) == len(csv_rows) == 4
    noor = next(row for row in excel_rows[1:] if row[COLUMN["Name"]] == "Al Noor Solar Dealer")
    assert noor[COLUMN["Lead ID"]] == leads["noor"].id
    assert noor[COLUMN["Score"]] == 100
    assert noor[COLUMN["Phone numbers"]] == "+923004438424; +924235771769"
    assert noor[COLUMN["Rating"]] == 4.6


def test_excel_export_follows_the_same_filters_as_the_list(client, leads, sales_user, auth_headers):
    rows = sheet_rows(client.get(f"{XLSX_URL}?has_email=true", headers=auth_headers(sales_user)))

    assert {row[COLUMN["Name"]] for row in rows[1:]} == {"Al Noor Solar Dealer", "Quetta Solar Works"}


def test_a_business_named_like_a_formula_is_stored_as_text_in_excel(client, make_business, sales_user, auth_headers):
    make_business('=HYPERLINK("http://evil.example","Click")', phones=["0300 1234567"], address="@SUM(A1)")

    response = client.get(XLSX_URL, headers=auth_headers(sales_user))
    sheet = load_workbook(io.BytesIO(response.content))["Leads"]
    name, address = sheet.cell(2, COLUMN["Name"] + 1), sheet.cell(2, COLUMN["Address"] + 1)

    assert name.data_type == "s" and name.value == '=HYPERLINK("http://evil.example","Click")'
    assert address.data_type == "s" and address.value == "@SUM(A1)"


def test_urdu_names_and_control_characters_survive_in_excel(client, make_business, sales_user, auth_headers):
    make_business("سولر پاور ہاؤس Café Élan", phones=["0300 1234567"])

    rows = sheet_rows(client.get(XLSX_URL, headers=auth_headers(sales_user)))

    assert rows[1][COLUMN["Name"]] == "سولر پاور ہاؤس Café Élan"


def test_a_filter_that_matches_nothing_is_a_header_only_sheet(client, leads, sales_user, auth_headers):
    response = client.get(f"{XLSX_URL}?search=zzzzz", headers=auth_headers(sales_user))

    assert sheet_rows(response) == [LEAD_HEADERS]
    assert response.headers["x-row-count"] == "0"


def test_someone_on_do_not_contact_is_never_exported_to_excel(client, leads, sales_user, auth_headers):
    headers = auth_headers(sales_user)
    client.post(f"{LEADS}/{leads['noor'].id}/do-not-contact", headers=headers, json={})

    names = {row[COLUMN["Name"]] for row in sheet_rows(client.get(XLSX_URL, headers=headers))[1:]}

    assert "Al Noor Solar Dealer" not in names
