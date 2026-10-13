from app.core.importing.cities import CityMatcher
from scripts.convert_aedb_pdf import convert_row, parse_contacts, squash


def test_a_phone_and_an_email_are_read_from_the_contact_cell():
    phones, emails = parse_contacts("Tel: 042-35342996\nCell: 0305-4009082\nEmail: axovolt3@gmail.com")
    assert phones == ["042-35342996", "0305-4009082"] and emails == ["axovolt3@gmail.com"]


def test_a_second_number_without_an_area_code_shares_the_first_ones():
    phones, emails = parse_contacts("Tel: 021-32750760-3, 32701145\nCell: 0321-2099988\nEmail: info@aptinverex.com\nzstraders@yahoo.com")
    assert phones == ["021-32750760", "021-32701145", "0321-2099988"]
    assert emails == ["info@aptinverex.com", "zstraders@yahoo.com"]


def test_a_fax_number_is_not_a_phone():
    phones, _ = parse_contacts("Tel: 051-5167020-1\nFax: 051-5167022\nCell: 0333-5170711\nEmail: benchmark@bmtpak.com")
    assert phones == ["051-5167020", "0333-5170711"]


def test_an_email_wrapped_over_two_lines_is_joined():
    _, emails = parse_contacts("Cell:0321-8244489\nEmail: muhammadsalman@\nsaqcommunication.com")
    assert emails == ["muhammadsalman@saqcommunication.com"]
    _, emails = parse_contacts("Cell: 051-4444759\nEmail:\ninfo@pakevergreenenergy.com")
    assert emails == ["info@pakevergreenenergy.com"]


def test_a_landline_listed_under_cell_is_still_kept_and_repeats_are_dropped():
    phones, _ = parse_contacts("Cell: 051-4444759\nTel: 051-4444759")
    assert phones == ["051-4444759"]


def test_an_empty_cell_has_no_contacts():
    assert parse_contacts(None) == ([], [])
    assert parse_contacts("") == ([], [])


def test_wrapped_text_is_put_on_one_line():
    assert squash("Pak Evergreen\nEnergy (Private)\nLimited") == "Pak Evergreen Energy (Private) Limited"


def row(number="1.", name="Axovolt\n(SMC-\nPrivate) Limited", address="Office No. 9,\nBahria Town,\nLahore."):
    return [number, name, "CR/24/002/C-3\n(Rev-4)", "22-11-2024", "Solar", "ICT, Punjab,\nSindh", address, "Tel: 042-35342996\nEmail: a@b.pk"]


def test_a_company_row_becomes_a_clean_record_with_its_city():
    matcher = CityMatcher({"Lahore": 0, "Karachi": 1})
    record = convert_row(row(), matcher, {0: "Lahore", 1: "Karachi"})

    assert record["Company"] == "Axovolt (SMC- Private) Limited"
    assert record["City"] == "Lahore"
    assert record["Address"] == "Office No. 9, Bahria Town, Lahore."
    assert record["Phones"] == "042-35342996" and record["Emails"] == "a@b.pk"
    assert record["Certificate No"] == "CR/24/002/C-3 (Rev-4)" and record["Coverage"] == "ICT, Punjab, Sindh"


def test_header_rows_and_fragments_are_ignored():
    matcher = CityMatcher({"Lahore": 0})
    header = ["S.\nNo.", "Company Name", "Certificate No.", "Validity", "Valid for", None, "Registered Address", "Contact Details"]
    subheader = [None, None, None, None, "Technology", "Area", None, None]
    assert convert_row(header, matcher, {}) is None
    assert convert_row(subheader, matcher, {}) is None
    assert convert_row(["1.", "short row"], matcher, {}) is None


def test_an_unknown_city_is_left_blank_for_the_importer_to_default():
    record = convert_row(row(address="Some Village"), CityMatcher({"Lahore": 0}), {0: "Lahore"})
    assert record["City"] == ""


import csv  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402

SAMPLES = Path(__file__).resolve().parents[2] / "sample_data"


@pytest.mark.parametrize(
    "filename, companies, known",
    [
        ("sample-installers.csv", 24, "Sunrise Solar Solutions (Sample 01)"),
    ],
)
def test_each_converted_installer_list_has_clean_rows_ready_for_the_imports_screen(filename, companies, known):
    with (SAMPLES / filename).open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == companies
    assert known in {row["Company"] for row in rows}
    assert all(row["Company"] and (row["Phones"] or row["Emails"]) for row in rows)
    assert all(not any(char in row["Phones"] for char in "()") for row in rows)
    assert rows[0].keys() == {"Company", "Certificate No", "Valid until", "Technology", "Coverage", "Address", "City", "Phones", "Emails"}
