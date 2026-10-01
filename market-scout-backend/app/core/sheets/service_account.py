"""Reading a Google service-account key and exchanging it for an access token."""
import json
import time
from dataclasses import dataclass

import httpx
from cryptography.hazmat.primitives import serialization
from jose import jwt

from app.core.sheets.errors import SheetsAuthError, SheetsError

SCOPE = "https://www.googleapis.com/auth/spreadsheets"
TOKEN_URL = "https://oauth2.googleapis.com/token"
_TOKEN_LIFETIME_S = 3600


@dataclass(frozen=True)
class ServiceAccount:
    client_email: str
    private_key: str = ""

    def __repr__(self) -> str:  # never let the key reach a log line or traceback
        return f"ServiceAccount(client_email={self.client_email!r})"


def parse_service_account(raw: str) -> ServiceAccount:
    """Validate the JSON a person downloads from Google Cloud. Messages are written for them,
    and never echo any part of the private key."""
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        raise SheetsError("That isn't valid JSON. Paste the whole contents of the downloaded key file.") from None
    if not isinstance(data, dict):
        raise SheetsError("That isn't a service-account key file.")

    if data.get("type") != "service_account":
        raise SheetsError(
            'This JSON is not a service-account key (its "type" should be "service_account"). '
            "Create the key under IAM & Admin > Service Accounts, not an OAuth client."
        )
    email = data.get("client_email")
    private_key = data.get("private_key")
    if not isinstance(email, str) or "@" not in email:
        raise SheetsError('The key file has no "client_email".')
    if not isinstance(private_key, str) or not private_key.strip():
        raise SheetsError('The key file has no "private_key".')
    try:
        serialization.load_pem_private_key(private_key.encode("utf-8"), password=None)
    except (ValueError, TypeError):
        raise SheetsError("The private key in this file can't be read. Download a fresh key and paste it again.") from None
    return ServiceAccount(client_email=email.strip(), private_key=private_key)


def request_access_token(
    account: ServiceAccount,
    client: httpx.Client,
    token_url: str = TOKEN_URL,
    now: float | None = None,
) -> str:
    """Sign a short-lived assertion with the private key and trade it for an access token."""
    issued_at = int(now if now is not None else time.time())
    assertion = jwt.encode(
        {
            "iss": account.client_email,
            "scope": SCOPE,
            "aud": token_url,
            "iat": issued_at,
            "exp": issued_at + _TOKEN_LIFETIME_S,
        },
        account.private_key,
        algorithm="RS256",
    )
    try:
        response = client.post(
            token_url,
            data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": assertion},
        )
    except httpx.TransportError as exc:
        raise SheetsError(f"Couldn't reach Google to sign in ({exc.__class__.__name__}). Check the internet connection.") from exc

    if response.status_code != 200:
        detail = _error_description(response)
        raise SheetsAuthError(
            "Google rejected the service-account key"
            + (f" ({detail})" if detail else "")
            + ". If it was deleted or disabled in Google Cloud, create a new key and save it here."
        )
    token = response.json().get("access_token")
    if not token:
        raise SheetsAuthError("Google's sign-in answer had no access token.")
    return token


def _error_description(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return ""
    return str(body.get("error_description") or body.get("error") or "")[:200]
