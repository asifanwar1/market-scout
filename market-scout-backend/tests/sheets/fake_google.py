"""An in-memory stand-in for Google's token endpoint and Sheets API v4.

It checks the things that matter to the real service: the token request is a properly signed
assertion, every call carries the bearer token, writes can't go outside the worksheet's grid, and
a worksheet can be created, grown, cleared and formatted. ``handle`` is transport-agnostic so the
same fake backs ``httpx.MockTransport`` in tests and a real local HTTP server for browser tests.
"""
import json
import re
from urllib.parse import unquote

from jose import jwt

TOKEN = "fake-access-token"
API_PREFIX = "/v4"

_A1 = re.compile(r"^(?:'((?:[^']|'')+)'|([^!']+))!([A-Z]+)(\d+)(?::([A-Z]+)(\d+))?$")


def _col_number(letters: str) -> int:
    number = 0
    for char in letters:
        number = number * 26 + ord(char) - 64
    return number


class FakeGoogle:
    def __init__(self, public_key_pem: str, client_email: str) -> None:
        self.public_key_pem = public_key_pem
        self.client_email = client_email
        # spreadsheet id -> {"title": str, "sheets": {title: worksheet}}
        self.spreadsheets: dict[str, dict] = {}
        self.forbidden: set[str] = set()
        self.api_disabled = False
        self.token_requests = 0
        self.audience = "https://oauth2.googleapis.com/token"
        self.calls: list[tuple[str, str]] = []
        self._next_sheet_id = 100
        self.expire_token_once = False
        self.fail_next: list[tuple[int, dict]] = []

    # ---- test helpers ------------------------------------------------------------------------

    def add_spreadsheet(self, spreadsheet_id: str, title: str = "Sales leads", worksheets: dict | None = None) -> None:
        self.spreadsheets[spreadsheet_id] = {"title": title, "sheets": {}}
        for name, rows in (worksheets or {"Sheet1": []}).items():
            sheet = self._new_worksheet(name, 1000, 26)
            for r, row in enumerate(rows, start=1):
                for c, value in enumerate(row, start=1):
                    sheet["cells"][(r, c)] = value
            self.spreadsheets[spreadsheet_id]["sheets"][name] = sheet

    def table(self, spreadsheet_id: str, worksheet: str) -> list[list]:
        """The worksheet as a list of rows, trailing empty cells and rows trimmed."""
        sheet = self.spreadsheets[spreadsheet_id]["sheets"][worksheet]
        cells = {k: v for k, v in sheet["cells"].items() if v not in ("", None)}
        if not cells:
            return []
        max_row = max(r for r, _ in cells)
        max_col = max(c for _, c in cells)
        return [[cells.get((r, c), "") for c in range(1, max_col + 1)] for r in range(1, max_row + 1)]

    def worksheet(self, spreadsheet_id: str, title: str) -> dict:
        return self.spreadsheets[spreadsheet_id]["sheets"][title]

    def _new_worksheet(self, title: str, rows: int, cols: int) -> dict:
        self._next_sheet_id += 1
        return {
            "id": self._next_sheet_id, "title": title, "rows": rows, "cols": cols,
            "cells": {}, "frozen": 0, "bold_header": False, "filter": None,
        }

    # ---- HTTP surface ------------------------------------------------------------------------

    def handle(self, method: str, url_path: str, params: dict, headers: dict, body: bytes) -> tuple[int, dict]:
        if url_path.endswith("/token"):
            return self._token(body)

        if self.fail_next:
            status, payload = self.fail_next.pop(0)
            return status, payload

        if headers.get("authorization") != f"Bearer {TOKEN}":
            return 401, {"error": {"code": 401, "message": "Request had invalid authentication credentials."}}
        if self.expire_token_once:
            self.expire_token_once = False
            return 401, {"error": {"code": 401, "message": "Token expired."}}
        if self.api_disabled:
            return 403, {"error": {
                "code": 403, "status": "PERMISSION_DENIED",
                "message": "Google Sheets API has not been used in project 1234 before or it is disabled.",
                "details": [{"reason": "SERVICE_DISABLED"}],
            }}

        path = unquote(url_path)
        assert path.startswith(API_PREFIX), path
        path = path[len(API_PREFIX):]
        self.calls.append((method, path))
        payload = json.loads(body) if body else {}

        match = re.match(r"^/spreadsheets/([^/:]+)(.*)$", path)
        if not match:
            return 404, {"error": {"message": "Not found"}}
        spreadsheet_id, rest = match.groups()
        if spreadsheet_id in self.forbidden:
            return 403, {"error": {"code": 403, "status": "PERMISSION_DENIED", "message": "The caller does not have permission"}}
        spreadsheet = self.spreadsheets.get(spreadsheet_id)
        if spreadsheet is None:
            return 404, {"error": {"code": 404, "status": "NOT_FOUND", "message": "Requested entity was not found."}}

        if rest == "" and method == "GET":
            return 200, self._metadata(spreadsheet, params.get("fields", ""))
        if rest == ":batchUpdate" and method == "POST":
            return self._batch_update(spreadsheet, payload)
        if rest == "/values:batchClear" and method == "POST":
            return self._batch_clear(spreadsheet, payload)
        if rest.startswith("/values/"):
            range_ = rest[len("/values/"):]
            if method == "GET":
                return self._get_values(spreadsheet, range_)
            if method == "PUT":
                assert params.get("valueInputOption") == "RAW", "values must be written RAW so nothing becomes a formula"
                return self._put_values(spreadsheet, range_, payload)
        return 404, {"error": {"message": f"Unhandled {method} {path}"}}

    def _token(self, body: bytes) -> tuple[int, dict]:
        self.token_requests += 1
        form = dict(pair.split("=", 1) for pair in body.decode().split("&"))
        assert unquote(form["grant_type"]) == "urn:ietf:params:oauth:grant-type:jwt-bearer"
        try:
            claims = jwt.decode(
                unquote(form["assertion"]), self.public_key_pem, algorithms=["RS256"],
                audience=self.audience,
            )
        except Exception as exc:  # a badly signed assertion is what real Google rejects
            return 400, {"error": "invalid_grant", "error_description": f"Invalid JWT: {exc.__class__.__name__}"}
        assert claims["iss"] == self.client_email
        assert claims["scope"] == "https://www.googleapis.com/auth/spreadsheets"
        return 200, {"access_token": TOKEN, "expires_in": 3600, "token_type": "Bearer"}

    def _metadata(self, spreadsheet: dict, fields: str) -> dict:
        result: dict = {}
        if "properties.title" in fields:
            result["properties"] = {"title": spreadsheet["title"]}
        if "sheets" in fields:
            result["sheets"] = [
                {"properties": {
                    "sheetId": s["id"], "title": s["title"],
                    "gridProperties": {"rowCount": s["rows"], "columnCount": s["cols"]},
                }}
                for s in spreadsheet["sheets"].values()
            ]
        return result

    def _batch_update(self, spreadsheet: dict, payload: dict) -> tuple[int, dict]:
        replies = []
        for request in payload["requests"]:
            if "addSheet" in request:
                props = request["addSheet"]["properties"]
                if props["title"] in spreadsheet["sheets"]:
                    return 400, {"error": {"message": "A sheet with that name already exists"}}
                grid = props.get("gridProperties", {})
                sheet = self._new_worksheet(props["title"], grid.get("rowCount", 1000), grid.get("columnCount", 26))
                spreadsheet["sheets"][props["title"]] = sheet
                replies.append({"addSheet": {"properties": {
                    "sheetId": sheet["id"], "title": sheet["title"],
                    "gridProperties": {"rowCount": sheet["rows"], "columnCount": sheet["cols"]},
                }}})
                continue
            sheet_id = self._sheet_id_of(request)
            sheet = next((s for s in spreadsheet["sheets"].values() if s["id"] == sheet_id), None)
            if sheet is None:
                return 400, {"error": {"message": f"No sheet with id {sheet_id}"}}
            if "updateSheetProperties" in request:
                grid = request["updateSheetProperties"]["properties"].get("gridProperties", {})
                sheet["rows"] = grid.get("rowCount", sheet["rows"])
                sheet["cols"] = grid.get("columnCount", sheet["cols"])
                sheet["frozen"] = grid.get("frozenRowCount", sheet["frozen"])
            elif "repeatCell" in request:
                sheet["bold_header"] = True
            elif "setBasicFilter" in request:
                sheet["filter"] = request["setBasicFilter"]["filter"]["range"]
            replies.append({})
        return 200, {"replies": replies}

    @staticmethod
    def _sheet_id_of(request: dict) -> int:
        body = next(iter(request.values()))
        return (body.get("properties") or body.get("range") or body.get("filter", {}).get("range")).get("sheetId")

    def _parse_range(self, spreadsheet: dict, range_: str) -> tuple[dict | None, int, int, int, int]:
        match = _A1.match(range_)
        assert match, f"unparseable range {range_!r}"
        quoted, plain, c1, r1, c2, r2 = match.groups()
        title = quoted.replace("''", "'") if quoted else plain
        sheet = spreadsheet["sheets"].get(title)
        return sheet, int(r1), _col_number(c1), int(r2 or r1), _col_number(c2 or c1)

    def _get_values(self, spreadsheet: dict, range_: str) -> tuple[int, dict]:
        sheet, r1, c1, r2, c2 = self._parse_range(spreadsheet, range_)
        if sheet is None:
            return 400, {"error": {"message": f"Unable to parse range: {range_}"}}
        rows = []
        for r in range(r1, r2 + 1):
            row = [sheet["cells"].get((r, c), "") for c in range(c1, c2 + 1)]
            while row and row[-1] == "":
                row.pop()
            rows.append(row)
        while rows and not rows[-1]:
            rows.pop()
        return 200, {"range": range_, "majorDimension": "ROWS", **({"values": rows} if rows else {})}

    def _put_values(self, spreadsheet: dict, range_: str, payload: dict) -> tuple[int, dict]:
        sheet, r1, c1, _, _ = self._parse_range(spreadsheet, range_)
        if sheet is None:
            return 400, {"error": {"message": f"Unable to parse range: {range_}"}}
        values = payload["values"]
        last_row = r1 + len(values) - 1
        last_col = c1 + max((len(row) for row in values), default=1) - 1
        if last_row > sheet["rows"] or last_col > sheet["cols"]:
            return 400, {"error": {"message": f"Range ('{sheet['title']}'!A{r1}) exceeds grid limits. Max rows: {sheet['rows']}, max columns: {sheet['cols']}"}}
        for offset, row in enumerate(values):
            for c, value in enumerate(row):
                sheet["cells"][(r1 + offset, c1 + c)] = value
        return 200, {"updatedRows": len(values)}

    def _batch_clear(self, spreadsheet: dict, payload: dict) -> tuple[int, dict]:
        for range_ in payload["ranges"]:
            sheet, r1, c1, r2, c2 = self._parse_range(spreadsheet, range_)
            if sheet is None:
                return 400, {"error": {"message": f"Unable to parse range: {range_}"}}
            if r2 > sheet["rows"] or c2 > sheet["cols"]:
                return 400, {"error": {"message": f"Range {range_} exceeds grid limits."}}
            for key in [k for k in sheet["cells"] if r1 <= k[0] <= r2 and c1 <= k[1] <= c2]:
                del sheet["cells"][key]
        return 200, {"clearedRanges": payload["ranges"]}
