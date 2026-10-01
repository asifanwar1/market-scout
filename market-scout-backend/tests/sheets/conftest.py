import json

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.core.sheets.client import SheetsClient
from app.core.sheets.service_account import ServiceAccount
from tests.sheets.fake_google import FakeGoogle

CLIENT_EMAIL = "market-scout@test-project.iam.gserviceaccount.com"
SPREADSHEET_ID = "1AbCdEfGhIjKlMnOpQrStUvWxYz0123456789"


def _pem_pair() -> tuple[str, str]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    ).decode()
    public = key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()
    return private, public


@pytest.fixture(scope="session")
def rsa_pems() -> tuple[str, str]:
    return _pem_pair()


@pytest.fixture(scope="session")
def other_rsa_pems() -> tuple[str, str]:
    return _pem_pair()


@pytest.fixture()
def service_account_json(rsa_pems) -> str:
    return json.dumps({
        "type": "service_account",
        "project_id": "test-project",
        "private_key_id": "abc123",
        "private_key": rsa_pems[0],
        "client_email": CLIENT_EMAIL,
        "client_id": "1234567890",
        "token_uri": "https://oauth2.googleapis.com/token",
    })


@pytest.fixture()
def account(rsa_pems) -> ServiceAccount:
    return ServiceAccount(client_email=CLIENT_EMAIL, private_key=rsa_pems[0])


@pytest.fixture()
def fake_google(rsa_pems) -> FakeGoogle:
    fake = FakeGoogle(public_key_pem=rsa_pems[1], client_email=CLIENT_EMAIL)
    fake.add_spreadsheet(SPREADSHEET_ID, "Sales leads")
    return fake


@pytest.fixture()
def make_client(fake_google):
    """Builds a SheetsClient that talks to the fake instead of the internet."""

    def handler(request: httpx.Request) -> httpx.Response:
        status, body = fake_google.handle(
            request.method,
            request.url.path,
            dict(request.url.params),
            {key.lower(): value for key, value in request.headers.items()},
            request.content,
        )
        return httpx.Response(status, json=body)

    def _make(account: ServiceAccount) -> SheetsClient:
        return SheetsClient(account, transport=httpx.MockTransport(handler), sleep=lambda _s: None)

    return _make
