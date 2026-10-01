import json

import httpx
import pytest
from jose import jwt

from app.core.sheets.errors import SheetsAuthError, SheetsError
from app.core.sheets.service_account import ServiceAccount, parse_service_account, request_access_token
from tests.sheets.conftest import CLIENT_EMAIL


def test_parses_a_downloaded_key(service_account_json):
    account = parse_service_account(service_account_json)
    assert account.client_email == CLIENT_EMAIL
    assert "BEGIN PRIVATE KEY" in account.private_key


def test_repr_never_shows_the_private_key(service_account_json):
    account = parse_service_account(service_account_json)
    assert "PRIVATE KEY" not in repr(account)
    assert CLIENT_EMAIL in repr(account)


@pytest.mark.parametrize(
    "raw, fragment",
    [
        ("not json at all", "isn't valid JSON"),
        ("[1, 2]", "isn't a service-account key"),
        (json.dumps({"type": "authorized_user"}), "not a service-account key"),
        (json.dumps({"type": "service_account", "private_key": "x"}), "client_email"),
        (json.dumps({"type": "service_account", "client_email": "a@b.iam.gserviceaccount.com"}), "private_key"),
        (
            json.dumps({"type": "service_account", "client_email": "a@b.iam.gserviceaccount.com", "private_key": "garbage"}),
            "can't be read",
        ),
    ],
)
def test_rejects_bad_keys_with_a_plain_message(raw, fragment):
    with pytest.raises(SheetsError) as caught:
        parse_service_account(raw)
    assert fragment in str(caught.value)


def test_rejection_never_echoes_the_private_key(service_account_json):
    data = json.loads(service_account_json)
    data["type"] = "authorized_user"
    with pytest.raises(SheetsError) as caught:
        parse_service_account(json.dumps(data))
    assert "PRIVATE KEY" not in str(caught.value)


def test_token_request_is_a_correctly_signed_assertion(account, rsa_pems):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        form = dict(pair.split("=", 1) for pair in request.content.decode().split("&"))
        seen["form"] = form
        return httpx.Response(200, json={"access_token": "tok"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        token = request_access_token(account, client, now=1_000_000)

    assert token == "tok"
    assert seen["form"]["grant_type"].startswith("urn%3Aietf")
    from urllib.parse import unquote

    claims = jwt.decode(
        unquote(seen["form"]["assertion"]), rsa_pems[1], algorithms=["RS256"],
        audience="https://oauth2.googleapis.com/token", options={"verify_exp": False},
    )
    assert claims["iss"] == CLIENT_EMAIL
    assert claims["scope"] == "https://www.googleapis.com/auth/spreadsheets"
    assert claims["exp"] - claims["iat"] == 3600


def test_google_refusing_the_key_gives_a_helpful_error(account):
    def handler(_request):
        return httpx.Response(400, json={"error": "invalid_grant", "error_description": "Invalid signature"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(SheetsAuthError) as caught:
            request_access_token(account, client)
    assert "Invalid signature" in str(caught.value)
    assert "create a new key" in str(caught.value)


def test_network_failure_while_signing_in_is_reported(account):
    def handler(_request):
        raise httpx.ConnectError("no route")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(SheetsError) as caught:
            request_access_token(account, client)
    assert "internet" in str(caught.value)


def test_a_wrongly_signed_assertion_is_rejected_by_the_fake_like_real_google(other_rsa_pems, make_client):
    wrong = ServiceAccount(client_email=CLIENT_EMAIL, private_key=other_rsa_pems[0])
    with make_client(wrong) as client:
        with pytest.raises(SheetsAuthError):
            client.spreadsheet_title("1AbCdEfGhIjKlMnOpQrStUvWxYz0123456789")
