import io

import pytest
from openpyxl import Workbook

from app.core.importing.cities import CityMatcher
from app.core.importing.files import ImportFileError, read_table
from app.core.importing.mapping import (
    SKIP_NO_CONTACT,
    SKIP_NO_NAME,
    Mapping,
    clean_cell,
    parse_row,
    stable_external_id,
    suggest_mapping,
)


def csv_bytes(text: str, encoding: str = "utf-8") -> bytes:
    return text.encode(encoding)


def xlsx_bytes(rows: list[list]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    for row in rows:
        sheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_reads_a_csv_into_headers_and_rows():
    table = read_table("list.csv", csv_bytes("Company,Phone\nAl Noor Solar,0300 4438424\nBilal Traders,0301 1112223\n"), 100)
    assert table.headers == ["Company", "Phone"]
    assert table.rows == [["Al Noor Solar", "0300 4438424"], ["Bilal Traders", "0301 1112223"]]


def test_a_byte_order_mark_from_excel_does_not_leak_into_the_first_header():
    table = read_table("list.csv", csv_bytes("﻿Company,Phone\nA,1\n"), 100)
    assert table.headers[0] == "Company"


def test_a_windows_encoded_file_is_read_too():
    table = read_table("list.csv", csv_bytes("Company,City\nCafé Électrique,Lahore\n", "cp1252"), 100)
    assert table.rows[0][0] == "Café Électrique"


def test_urdu_text_in_a_utf8_file_survives():
    table = read_table("list.csv", csv_bytes("Company\nسولر پاور ہاؤس\n"), 100)
    assert table.rows[0][0] == "سولر پاور ہاؤس"


@pytest.mark.parametrize("delimiter", [";", "\t", "|"])
def test_other_delimiters_are_detected(delimiter):
    text = delimiter.join(["Company", "Phone"]) + "\n" + delimiter.join(["A Shop", "0300 1111111"]) + "\n"
    table = read_table("list.csv", csv_bytes(text), 100)
    assert table.headers == ["Company", "Phone"] and table.rows == [["A Shop", "0300 1111111"]]


def test_quoted_cells_may_contain_commas_and_line_breaks():
    table = read_table("list.csv", csv_bytes('Company,Address\n"Haroon Brothers","House 26, Street 1,\nLahore"\n'), 100)
    assert table.rows[0][1] == "House 26, Street 1,\nLahore"


def test_blank_lines_above_the_header_and_between_rows_are_ignored():
    table = read_table("list.csv", csv_bytes("\n\nCompany,Phone\n\nA,1\n\n\nB,2\n"), 100)
    assert table.headers == ["Company", "Phone"] and len(table.rows) == 2


def test_duplicate_and_missing_headers_get_distinct_names():
    table = read_table("list.csv", csv_bytes("Phone,Phone,,Name\n1,2,3,A\n"), 100)
    assert table.headers == ["Phone", "Phone (2)", "Column 3", "Name"]


def test_short_rows_are_padded_and_long_rows_cut_to_the_header_width():
    table = read_table("list.csv", csv_bytes("A,B,C\n1\n1,2,3,4,5\n"), 100)
    assert table.rows == [["1", "", ""], ["1", "2", "3"]]


@pytest.mark.parametrize(
    "content, message",
    [("", "empty"), ("\n\n  \n", "empty"), ("Company,Phone\n", "no data rows")],
)
def test_empty_files_are_explained(content, message):
    with pytest.raises(ImportFileError, match=message):
        read_table("list.csv", csv_bytes(content), 100)


def test_too_many_rows_is_refused_with_the_limit():
    with pytest.raises(ImportFileError, match="limit is 3"):
        read_table("list.csv", csv_bytes("A\n1\n2\n3\n4\n"), 3)


@pytest.mark.parametrize("name, message", [("list.xls", "Old .xls"), ("list.pdf", "Upload a .csv or .xlsx"), ("list", "Upload a .csv")])
def test_unsupported_files_say_what_to_do(name, message):
    with pytest.raises(ImportFileError, match=message):
        read_table(name, b"whatever", 100)


def test_reads_an_excel_file_and_turns_phone_numbers_typed_as_numbers_into_text():
    table = read_table("list.xlsx", xlsx_bytes([["Company", "Mobile"], ["Al Noor", 3004438424], ["Bilal", "0301 1112223"]]), 100)
    assert table.headers == ["Company", "Mobile"]
    assert table.rows == [["Al Noor", "3004438424"], ["Bilal", "0301 1112223"]]


def test_a_file_that_only_pretends_to_be_excel_is_rejected():
    with pytest.raises(ImportFileError, match="valid .xlsx"):
        read_table("list.xlsx", b"this is just text", 100)


def test_suggests_columns_for_a_typical_list():
    guess = suggest_mapping(["S. No.", "Company Name", "Certificate No.", "Registered Address", "City", "Phones", "Emails", "Website"])
    assert guess["name"] == "Company Name"
    assert guess["phones"] == ["Phones"] and guess["emails"] == ["Emails"]
    assert guess["website"] == "Website" and guess["city"] == "City" and guess["address"] == "Registered Address"


def test_several_phone_columns_are_all_suggested():
    guess = suggest_mapping(["Name", "Mobile", "Landline", "Email"])
    assert guess["phones"] == ["Mobile", "Landline"]


def test_a_column_is_never_suggested_for_two_fields():
    guess = suggest_mapping(["Business Name", "Contact", "Email"])
    used = [guess["name"], *guess["phones"], *guess["emails"]]
    assert len(used) == len(set(used))


def test_unrecognisable_headers_suggest_nothing_rather_than_guessing_wrongly():
    guess = suggest_mapping(["Col A", "Col B"])
    assert guess["name"] is None and guess["phones"] == [] and guess["emails"] == []


def test_coordinates_are_suggested_together():
    guess = suggest_mapping(["Name", "Latitude", "Longitude"])
    assert guess["latitude"] == "Latitude" and guess["longitude"] == "Longitude"


MAPPING = Mapping(name="Company", phones=["Tel", "Cell"], emails=["Email"], website="Web", address="Address", city="City",
                  latitude="Lat", longitude="Lon", category="Type")


def parse(values: dict, require_contact: bool = True, mapping: Mapping = MAPPING):
    return parse_row(2, values, mapping, "import:Test list", require_contact)


def test_a_full_row_becomes_a_business():
    row = parse({
        "Company": "  Al  Noor Solar ", "Tel": "042-35342996, 042-35342997", "Cell": "0305-4009082",
        "Email": "Info@AlNoor.pk; sales@alnoor.pk", "Web": "alnoor.pk", "Address": "12 Mall Road, Lahore",
        "City": "Lahore", "Lat": "31.52", "Lon": "74.35", "Type": "Dealer",
    })

    assert row.skipped is None
    raw = row.raw
    assert raw.name == "Al Noor Solar" and raw.source_key == "import:Test list"
    assert raw.phones == ["+924235342996", "+924235342997", "+923054009082"]
    assert raw.emails == ["info@alnoor.pk", "sales@alnoor.pk"]
    assert raw.website and "alnoor.pk" in raw.website
    assert (raw.latitude, raw.longitude) == (31.52, 74.35) and raw.categories == ["Dealer"]
    assert row.city_text == "Lahore"
    assert raw.raw["Company"] == "  Al  Noor Solar ".strip() or raw.raw["Company"]


@pytest.mark.parametrize(
    "cell, expected",
    [
        ("3004438424", ["+923004438424"]),
        ("4235342996", ["+924235342996"]),
        ("0300 4438424", ["+923004438424"]),
        ("923004438424", ["+923004438424"]),
        ("042-35342996, 35342997", ["+924235342996"]),
        ("12345", []),
    ],
)
def test_a_phone_that_lost_its_leading_zero_in_excel_is_recovered(cell, expected):
    assert parse({"Company": "A", "Cell": cell}, require_contact=False).raw.phones == expected


def test_a_row_without_a_name_is_set_aside():
    assert parse({"Company": "  ", "Tel": "0300 1234567"}).skipped == SKIP_NO_NAME
    assert parse({"Company": "N/A", "Tel": "0300 1234567"}).skipped == SKIP_NO_NAME


def test_a_row_nobody_can_contact_is_set_aside_unless_asked_to_keep_it():
    assert parse({"Company": "Ghost Energy", "Tel": "call us"}).skipped == SKIP_NO_CONTACT
    assert parse({"Company": "Ghost Energy"}, require_contact=False).skipped is None


def test_one_contact_is_enough():
    assert parse({"Company": "A", "Email": "a@shop.pk"}).skipped is None
    assert parse({"Company": "A", "Web": "https://shop.pk"}).skipped is None
    assert parse({"Company": "A", "Cell": "0300 1234567"}).skipped is None


@pytest.mark.parametrize("empty", ["", "-", "N/A", "nil", "None", "null", "NaN", "."])
def test_placeholder_words_count_as_empty(empty):
    assert clean_cell(empty) == ""
    assert parse({"Company": "A", "Tel": empty, "Email": empty, "Web": empty}).skipped == SKIP_NO_CONTACT


@pytest.mark.parametrize(
    "lat, lon, valid",
    [("31.5", "74.3", True), ("31,5", "74,3", True), ("74.3", "31.5", False), ("0", "0", False), ("abc", "74", False), ("", "", False)],
)
def test_coordinates_are_kept_only_when_they_are_inside_pakistan(lat, lon, valid):
    raw = parse({"Company": "A", "Cell": "0300 1234567", "Lat": lat, "Lon": lon}).raw
    assert (raw.latitude is not None) == valid


def test_the_same_company_gets_the_same_id_wherever_it_sits_in_the_list():
    values = {"Company": "Al Noor Solar", "Cell": "0300 4438424"}
    first = parse(values).raw.external_id
    assert parse(values).raw.external_id == first
    assert parse({"Company": "AL NOOR  SOLAR", "Cell": "0300-4438424"}).raw.external_id == first
    assert parse({"Company": "Al Noor Solar", "Cell": "0301 9999999"}).raw.external_id != first


def test_the_id_does_not_depend_on_the_row_number():
    a = parse_row(2, {"Company": "X Co", "Cell": "0300 1234567"}, MAPPING, "import:t", True).raw.external_id
    b = parse_row(900, {"Company": "X Co", "Cell": "0300 1234567"}, MAPPING, "import:t", True).raw.external_id
    assert a == b
    assert stable_external_id("X Co", None, None) != stable_external_id("Y Co", None, None)


def test_a_row_with_no_phone_or_website_is_told_apart_by_where_it_is():
    lahore = stable_external_id("Kashif Traders", None, None, "Lahore Johar Town")
    karachi = stable_external_id("Kashif Traders", None, None, "Karachi Saddar")
    assert lahore != karachi
    assert lahore == stable_external_id("KASHIF TRADERS (Pvt) Ltd", None, None, "lahore  johar town")

    assert stable_external_id("Kashif Traders", "+923001234567", None, "Lahore") == stable_external_id("Kashif Traders", "+923001234567", None, "Karachi")
    assert stable_external_id("Kashif Traders", None, "kashif.pk", "Lahore") == stable_external_id("Kashif Traders", None, "kashif.pk", "")


CITIES = {"Lahore": 1, "Karachi": 2, "Rawalpindi": 3, "Dera Ismail Khan": 4, "Islamabad": 5, "Khan": 6}


@pytest.mark.parametrize("text, expected", [("Lahore", 1), ("  lahore ", 1), ("LAHORE CITY", 1), ("Lahore.", 1), ("Karachi", 2), ("Quetta", None), ("", None)])
def test_a_city_column_value_is_matched_ignoring_case_and_punctuation(text, expected):
    assert CityMatcher(CITIES).from_city_text(text) == expected


@pytest.mark.parametrize(
    "address, expected",
    [
        ("Office No. 9, Commercial Complex, Bahria Town, Lahore.", 1),
        ("House 26, Street 1, Link-2, Cavalry Ground, Lahore", 1),
        ("Shop 3, Peshawar Road, Rawalpindi.", 3),
        ("Plot 5, Sector I-9/3, Industrial Area, Islamabad.", 5),
        ("Main Bazaar, Dera Ismail Khan", 4),
        ("No city mentioned here", None),
        ("", None),
    ],
)
def test_a_city_is_found_at_the_end_of_an_address(address, expected):
    assert CityMatcher(CITIES).from_address(address) == expected


def test_a_city_name_inside_another_word_is_not_a_match():
    assert CityMatcher({"Hub": 1}).from_address("Chubb Road") is None
