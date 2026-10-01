import pytest

from app.core.sheets.client import MAX_CELL_CHARS, WRITE_CHUNK_ROWS, column_letter
from app.core.sheets.errors import SheetsError
from tests.sheets.conftest import CLIENT_EMAIL, SPREADSHEET_ID

HEADER = ["Lead ID", "Name", "Phone"]


def _rows(count: int, width: int = 3) -> list[list]:
    return [[i, f"Shop {i}", f"+92300{i:07d}"][:width] for i in range(1, count + 1)]


@pytest.mark.parametrize("index, letters", [(1, "A"), (26, "Z"), (27, "AA"), (52, "AZ"), (53, "BA"), (703, "AAA")])
def test_column_letters(index, letters):
    assert column_letter(index) == letters


def test_reports_the_spreadsheet_title(account, make_client):
    with make_client(account) as client:
        assert client.spreadsheet_title(SPREADSHEET_ID) == "Sales leads"


def test_unknown_spreadsheet(account, make_client):
    with make_client(account) as client:
        with pytest.raises(SheetsError, match="wasn't found"):
            client.spreadsheet_title("1NoSuchSpreadsheet000000000000000000")


def test_not_shared_with_the_service_account_names_the_address_to_share_with(account, make_client, fake_google):
    fake_google.forbidden.add(SPREADSHEET_ID)
    with make_client(account) as client:
        with pytest.raises(SheetsError) as caught:
            client.spreadsheet_title(SPREADSHEET_ID)
    assert CLIENT_EMAIL in str(caught.value)
    assert "Editor" in str(caught.value)


def test_api_not_enabled_is_explained_differently_from_not_shared(account, make_client, fake_google):
    fake_google.api_disabled = True
    with make_client(account) as client:
        with pytest.raises(SheetsError) as caught:
            client.spreadsheet_title(SPREADSHEET_ID)
    assert "Google Sheets API" in str(caught.value)
    assert CLIENT_EMAIL not in str(caught.value)


def test_an_uploaded_excel_file_is_explained(account, make_client, fake_google):
    fake_google.fail_next.append((400, {"error": {"message": "This operation is not supported for this document"}}))
    with make_client(account) as client:
        with pytest.raises(SheetsError, match="Excel"):
            client.spreadsheet_title(SPREADSHEET_ID)


def test_creates_the_worksheet_and_writes_header_then_rows(account, make_client, fake_google):
    with make_client(account) as client:
        written = client.replace_worksheet(SPREADSHEET_ID, "Leads", HEADER, _rows(3))

    assert written == 3
    assert fake_google.table(SPREADSHEET_ID, "Leads") == [HEADER, *_rows(3)]


def test_header_is_frozen_bold_and_filterable(account, make_client, fake_google):
    with make_client(account) as client:
        client.replace_worksheet(SPREADSHEET_ID, "Leads", HEADER, _rows(4))

    sheet = fake_google.worksheet(SPREADSHEET_ID, "Leads")
    assert sheet["frozen"] == 1
    assert sheet["bold_header"] is True
    assert sheet["filter"]["endRowIndex"] == 5 and sheet["filter"]["endColumnIndex"] == 3


def test_writing_twice_gives_an_identical_sheet(account, make_client, fake_google):
    with make_client(account) as client:
        client.replace_worksheet(SPREADSHEET_ID, "Leads", HEADER, _rows(5))
        first = fake_google.table(SPREADSHEET_ID, "Leads")
        client.replace_worksheet(SPREADSHEET_ID, "Leads", HEADER, _rows(5))

    assert fake_google.table(SPREADSHEET_ID, "Leads") == first
    assert list(fake_google.spreadsheets[SPREADSHEET_ID]["sheets"]) == ["Sheet1", "Leads"]


def test_fewer_rows_than_last_time_leave_nothing_behind(account, make_client, fake_google):
    with make_client(account) as client:
        client.replace_worksheet(SPREADSHEET_ID, "Leads", HEADER, _rows(8))
        client.replace_worksheet(SPREADSHEET_ID, "Leads", HEADER, _rows(2))

    assert fake_google.table(SPREADSHEET_ID, "Leads") == [HEADER, *_rows(2)]


def test_fewer_columns_than_last_time_leave_nothing_behind(account, make_client, fake_google):
    with make_client(account) as client:
        client.replace_worksheet(SPREADSHEET_ID, "Leads", HEADER, _rows(3))
        client.replace_worksheet(SPREADSHEET_ID, "Leads", HEADER[:2], _rows(3, width=2))

    assert fake_google.table(SPREADSHEET_ID, "Leads") == [HEADER[:2], *_rows(3, width=2)]


def test_no_leads_leaves_just_the_header(account, make_client, fake_google):
    with make_client(account) as client:
        client.replace_worksheet(SPREADSHEET_ID, "Leads", HEADER, _rows(4))
        assert client.replace_worksheet(SPREADSHEET_ID, "Leads", HEADER, []) == 0

    assert fake_google.table(SPREADSHEET_ID, "Leads") == [HEADER]


def test_more_rows_than_the_default_grid_grows_it_and_is_written_in_chunks(account, make_client, fake_google):
    count = WRITE_CHUNK_ROWS * 2 + 500
    fake_google.add_spreadsheet("1LargeSpreadsheet0000000000000000000", worksheets={"Leads": [HEADER]})
    with make_client(account) as client:
        client.replace_worksheet("1LargeSpreadsheet0000000000000000000", "Leads", HEADER, _rows(count))

    table = fake_google.table("1LargeSpreadsheet0000000000000000000", "Leads")
    assert len(table) == count + 1
    assert table[-1] == _rows(count)[-1]
    puts = [c for c in fake_google.calls if c[0] == "PUT"]
    assert len(puts) == 3


def test_an_empty_existing_worksheet_of_that_name_is_used(account, make_client, fake_google):
    fake_google.add_spreadsheet("1EmptyLeadsSheet00000000000000000000", worksheets={"Leads": []})
    with make_client(account) as client:
        client.replace_worksheet("1EmptyLeadsSheet00000000000000000000", "Leads", HEADER, _rows(2))
    assert fake_google.table("1EmptyLeadsSheet00000000000000000000", "Leads") == [HEADER, *_rows(2)]


def test_refuses_to_overwrite_a_worksheet_that_holds_someone_elses_data(account, make_client, fake_google):
    theirs = [["Customer", "Owes"], ["Ali", 500]]
    fake_google.add_spreadsheet("1SomeoneElsesSheet000000000000000000", worksheets={"Leads": theirs})
    with make_client(account) as client:
        with pytest.raises(SheetsError, match="already exists"):
            client.replace_worksheet("1SomeoneElsesSheet000000000000000000", "Leads", HEADER, _rows(2))

    assert fake_google.table("1SomeoneElsesSheet000000000000000000", "Leads") == theirs


def test_never_touches_other_worksheets(account, make_client, fake_google):
    fake_google.add_spreadsheet("1TwoWorksheets0000000000000000000000", worksheets={"Notes": [["keep", "me"]]})
    with make_client(account) as client:
        client.replace_worksheet("1TwoWorksheets0000000000000000000000", "Leads", HEADER, _rows(2))
    assert fake_google.table("1TwoWorksheets0000000000000000000000", "Notes") == [["keep", "me"]]


def test_a_title_with_an_apostrophe_works(account, make_client, fake_google):
    with make_client(account) as client:
        client.replace_worksheet(SPREADSHEET_ID, "Bob's leads", HEADER, _rows(2))
        client.replace_worksheet(SPREADSHEET_ID, "Bob's leads", HEADER, _rows(1))
    assert fake_google.table(SPREADSHEET_ID, "Bob's leads") == [HEADER, *_rows(1)]


def test_values_stay_text_and_are_capped(account, make_client, fake_google):
    rows = [[1, '=HYPERLINK("http://evil","x")', "y" * (MAX_CELL_CHARS + 500)], [2, None, 4.5]]
    with make_client(account) as client:
        client.replace_worksheet(SPREADSHEET_ID, "Leads", HEADER, rows)

    table = fake_google.table(SPREADSHEET_ID, "Leads")
    assert table[1][1] == '=HYPERLINK("http://evil","x")'
    assert len(table[1][2]) == MAX_CELL_CHARS
    assert table[2] == [2, "", 4.5]


def test_signs_in_once_per_sync(account, make_client, fake_google):
    with make_client(account) as client:
        client.replace_worksheet(SPREADSHEET_ID, "Leads", HEADER, _rows(2))
    assert fake_google.token_requests == 1


def test_an_expired_token_mid_sync_is_renewed_and_the_call_repeated(account, make_client, fake_google):
    with make_client(account) as client:
        client.spreadsheet_title(SPREADSHEET_ID)
        fake_google.expire_token_once = True
        client.replace_worksheet(SPREADSHEET_ID, "Leads", HEADER, _rows(2))

    assert fake_google.token_requests == 2
    assert fake_google.table(SPREADSHEET_ID, "Leads") == [HEADER, *_rows(2)]


def test_a_temporary_google_error_is_retried(account, make_client, fake_google):
    fake_google.fail_next.extend([(503, {}), (429, {})])
    with make_client(account) as client:
        assert client.spreadsheet_title(SPREADSHEET_ID) == "Sales leads"


def test_giving_up_after_repeated_google_errors_is_a_plain_message(account, make_client, fake_google):
    fake_google.fail_next.extend([(503, {})] * 10)
    with make_client(account) as client:
        with pytest.raises(SheetsError, match="isn't responding"):
            client.spreadsheet_title(SPREADSHEET_ID)
