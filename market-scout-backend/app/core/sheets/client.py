"""A small Google Sheets client: just what mirroring one table into one worksheet needs.

Pure Python (no database or web framework), like the scouting engine, so it can be tested with
``httpx.MockTransport`` and no network.
"""
import time
from collections.abc import Callable, Sequence
from urllib.parse import quote

import httpx

from app.core.scouting.sources.base import SourceError, request_with_retries
from app.core.sheets.errors import SheetsAuthError, SheetsError
from app.core.sheets.service_account import TOKEN_URL, ServiceAccount, request_access_token

API_BASE = "https://sheets.googleapis.com/v4"
WRITE_CHUNK_ROWS = 1000
# Google rejects a cell over 50,000 characters; stay well clear of it.
MAX_CELL_CHARS = 40_000
# Sync clears with a fixed number of retries kept short: a person is waiting on the result.
RETRY_DELAYS = (2.0, 5.0, 15.0)

Cell = str | int | float | None


def column_letter(index: int) -> str:
    """1 -> A, 26 -> Z, 27 -> AA."""
    letters = ""
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        letters = chr(ord("A") + remainder) + letters
    return letters


def _quote_title(title: str) -> str:
    return "'" + title.replace("'", "''") + "'"


def _clean(cell: Cell) -> Cell:
    if cell is None:
        return ""
    if isinstance(cell, str) and len(cell) > MAX_CELL_CHARS:
        return cell[:MAX_CELL_CHARS]
    return cell


class SheetsClient:
    def __init__(
        self,
        account: ServiceAccount,
        *,
        api_base: str = API_BASE,
        token_url: str = TOKEN_URL,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 30.0,
        sleep: Callable[[float], None] = time.sleep,
        retry_delays: tuple[float, ...] = RETRY_DELAYS,
    ) -> None:
        self._account = account
        self._api_base = api_base.rstrip("/")
        self._token_url = token_url
        self._client = httpx.Client(transport=transport, timeout=timeout)
        self._sleep = sleep
        self._retry_delays = retry_delays
        self._token: str | None = None

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "SheetsClient":
        return self

    def __exit__(self, *_exc) -> None:
        self.close()

    # ---- public ----------------------------------------------------------------------------

    def spreadsheet_title(self, spreadsheet_id: str) -> str:
        """The spreadsheet's name. Proves the key works and the sheet is shared with it."""
        data = self._call("GET", f"/spreadsheets/{spreadsheet_id}", params={"fields": "properties.title"})
        return (data.get("properties") or {}).get("title") or "Untitled"

    def replace_worksheet(
        self,
        spreadsheet_id: str,
        title: str,
        header: Sequence[str],
        rows: Sequence[Sequence[Cell]],
    ) -> int:
        """Make the worksheet hold exactly ``header`` + ``rows``, creating it if needed.

        Idempotent: running it twice with the same input leaves the same sheet. It only ever
        touches the worksheet called ``title``, and refuses one that has someone else's data in it.
        Returns the number of data rows written.
        """
        column_count = len(header)
        row_count = len(rows) + 1  # header
        sheet = self._find_worksheet(spreadsheet_id, title)
        if sheet is None:
            sheet = self._add_worksheet(spreadsheet_id, title, max(row_count, 2), column_count)
        else:
            self._refuse_foreign_worksheet(spreadsheet_id, title, header[0])
            sheet = self._grow_grid(spreadsheet_id, sheet, row_count, column_count)

        quoted = _quote_title(title)
        values = [list(header), *rows]
        for start in range(0, len(values), WRITE_CHUNK_ROWS):
            chunk = [[_clean(cell) for cell in row] for row in values[start:start + WRITE_CHUNK_ROWS]]
            self._call(
                "PUT",
                f"/spreadsheets/{spreadsheet_id}/values/{quote(f'{quoted}!A{start + 1}', safe='')}",
                params={"valueInputOption": "RAW"},
                json={"majorDimension": "ROWS", "values": chunk},
            )

        self._clear_leftovers(spreadsheet_id, quoted, sheet, row_count, column_count)
        self._format(spreadsheet_id, sheet["sheetId"], max(row_count, 2), column_count)
        return len(rows)

    # ---- worksheet plumbing ---------------------------------------------------------------------

    def _find_worksheet(self, spreadsheet_id: str, title: str) -> dict | None:
        data = self._call(
            "GET", f"/spreadsheets/{spreadsheet_id}",
            params={"fields": "sheets.properties(sheetId,title,gridProperties)"},
        )
        for sheet in data.get("sheets", []):
            properties = sheet.get("properties", {})
            if properties.get("title") == title:
                return _normalise_sheet(properties)
        return None

    def _add_worksheet(self, spreadsheet_id: str, title: str, rows: int, columns: int) -> dict:
        data = self._batch_update(spreadsheet_id, [{
            "addSheet": {"properties": {"title": title, "gridProperties": {"rowCount": rows, "columnCount": columns}}}
        }])
        return _normalise_sheet(data["replies"][0]["addSheet"]["properties"])

    def _refuse_foreign_worksheet(self, spreadsheet_id: str, title: str, first_header: str) -> None:
        # The sheet is cleared and rewritten on every sync, so it must never be one somebody
        # else keeps their own data in.
        data = self._call(
            "GET", f"/spreadsheets/{spreadsheet_id}/values/{quote(f'{_quote_title(title)}!A1', safe='')}"
        )
        existing = (data.get("values") or [[""]])[0]
        first_cell = str(existing[0]).strip() if existing else ""
        if first_cell and first_cell != first_header:
            raise SheetsError(
                f'A worksheet called "{title}" already exists in this spreadsheet and holds other data. '
                "Market Scout only overwrites its own sheet: rename or delete that worksheet, or use a different spreadsheet."
            )

    def _grow_grid(self, spreadsheet_id: str, sheet: dict, rows: int, columns: int) -> dict:
        new_rows, new_columns = max(sheet["rows"], rows), max(sheet["columns"], columns)
        if (new_rows, new_columns) != (sheet["rows"], sheet["columns"]):
            self._batch_update(spreadsheet_id, [{
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": sheet["sheetId"],
                        "gridProperties": {"rowCount": new_rows, "columnCount": new_columns},
                    },
                    "fields": "gridProperties(rowCount,columnCount)",
                }
            }])
        return {**sheet, "rows": new_rows, "columns": new_columns}

    def _clear_leftovers(self, spreadsheet_id: str, quoted_title: str, sheet: dict, rows: int, columns: int) -> None:
        """Wipe what the previous, longer or wider, version left below and to the right."""
        ranges = []
        if sheet["rows"] > rows:
            ranges.append(f"{quoted_title}!A{rows + 1}:{column_letter(sheet['columns'])}{sheet['rows']}")
        if sheet["columns"] > columns:
            ranges.append(f"{quoted_title}!{column_letter(columns + 1)}1:{column_letter(sheet['columns'])}{sheet['rows']}")
        if ranges:
            self._call("POST", f"/spreadsheets/{spreadsheet_id}/values:batchClear", json={"ranges": ranges})

    def _format(self, spreadsheet_id: str, sheet_id: int, rows: int, columns: int) -> None:
        self._batch_update(spreadsheet_id, [
            {
                "updateSheetProperties": {
                    "properties": {"sheetId": sheet_id, "gridProperties": {"frozenRowCount": 1}},
                    "fields": "gridProperties.frozenRowCount",
                }
            },
            {
                "repeatCell": {
                    "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1},
                    "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                    "fields": "userEnteredFormat.textFormat.bold",
                }
            },
            {
                "setBasicFilter": {
                    "filter": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 0, "endRowIndex": rows,
                            "startColumnIndex": 0, "endColumnIndex": columns,
                        }
                    }
                }
            },
        ])

    def _batch_update(self, spreadsheet_id: str, requests: list[dict]) -> dict:
        return self._call("POST", f"/spreadsheets/{spreadsheet_id}:batchUpdate", json={"requests": requests})

    # ---- HTTP ---------------------------------------------------------------------------------------

    def _access_token(self, refresh: bool = False) -> str:
        if self._token is None or refresh:
            self._token = request_access_token(self._account, self._client, self._token_url)
        return self._token

    def _call(self, method: str, path: str, **kwargs) -> dict:
        response = self._send(method, path, **kwargs)
        if response.status_code == 401:  # the token expired mid-sync; sign in once more
            self._access_token(refresh=True)
            response = self._send(method, path, **kwargs)
        if response.status_code >= 400:
            raise self._to_error(response)
        return response.json() if response.content else {}

    def _send(self, method: str, path: str, **kwargs) -> httpx.Response:
        try:
            return request_with_retries(
                self._client, method, f"{self._api_base}{path}",
                sleep=self._sleep, retry_delays=self._retry_delays,
                headers={"Authorization": f"Bearer {self._access_token()}"},
                **kwargs,
            )
        except SourceError as exc:
            raise SheetsError(f"Google Sheets isn't responding ({exc}). Try again in a few minutes.") from exc

    def _to_error(self, response: httpx.Response) -> SheetsError:
        message, reasons = _google_error(response)
        status = response.status_code
        lowered = message.lower()

        if status == 401:
            return SheetsAuthError("Google no longer accepts the service-account key. Save a new key and try again.")
        if status == 404:
            return SheetsError("That spreadsheet wasn't found. Check the link or ID.")
        if status == 403 and ("SERVICE_DISABLED" in reasons or "has not been used" in lowered or "is disabled" in lowered):
            return SheetsError(
                "The Google Sheets API isn't switched on for the service account's Google Cloud project. "
                "In Google Cloud open APIs & Services > Library, enable \"Google Sheets API\", wait a minute and try again."
            )
        if status == 403:
            return SheetsError(
                f"The service account can't open this spreadsheet. Share it with {self._account.client_email} "
                "and give it Editor access."
            )
        if status == 400 and "not supported for this document" in lowered:
            return SheetsError(
                "That file is an uploaded Excel file, not a Google Sheet. Open it in Google Sheets and choose "
                "File > Save as Google Sheets, then use the new file."
            )
        return SheetsError(f"Google Sheets said: {message or f'HTTP {status}'}")


def _normalise_sheet(properties: dict) -> dict:
    grid = properties.get("gridProperties") or {}
    return {
        "sheetId": properties["sheetId"],
        "title": properties.get("title"),
        "rows": grid.get("rowCount", 1000),
        "columns": grid.get("columnCount", 26),
    }


def _google_error(response: httpx.Response) -> tuple[str, set[str]]:
    try:
        error = response.json().get("error") or {}
    except ValueError:
        return "", set()
    if not isinstance(error, dict):
        return "", set()
    reasons = {d.get("reason") for d in error.get("details", []) if isinstance(d, dict)} | {error.get("status")}
    return str(error.get("message") or "")[:300], {r for r in reasons if r}
