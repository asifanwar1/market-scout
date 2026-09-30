import re
from dataclasses import dataclass
from urllib.parse import urlparse

import phonenumbers
from phonenumbers import Leniency, PhoneNumberFormat, PhoneNumberType

DEFAULT_REGION = "PK"

_MOBILE_TYPES = {PhoneNumberType.MOBILE, PhoneNumberType.FIXED_LINE_OR_MOBILE}


@dataclass(frozen=True)
class PhoneInfo:
    e164: str
    is_mobile: bool


def extract_phones(text: str | None, region: str = DEFAULT_REGION) -> list[PhoneInfo]:
    """Every valid phone number in ``text``, as E.164, de-duplicated, in order of appearance.

    Handles the formats seen in the wild in Pakistan: ``0301-4962026``, ``+92 333 9993333``,
    ``00923333675555`` and several numbers packed into one field.
    """
    if not text:
        return []

    found: dict[str, PhoneInfo] = {}
    for match in phonenumbers.PhoneNumberMatcher(text, region, leniency=Leniency.VALID):
        e164 = phonenumbers.format_number(match.number, PhoneNumberFormat.E164)
        if e164 not in found:
            found[e164] = PhoneInfo(e164, phonenumbers.number_type(match.number) in _MOBILE_TYPES)
    return list(found.values())


def extract_phones_from_many(values: list[str], region: str = DEFAULT_REGION) -> list[PhoneInfo]:
    found: dict[str, PhoneInfo] = {}
    for value in values:
        for phone in extract_phones(value, region):
            found.setdefault(phone.e164, phone)
    return list(found.values())


# ---- email -----------------------------------------------------------------

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}")
_EMAIL_FULL_RE = re.compile(r"^" + _EMAIL_RE.pattern + r"$")
_JUNK_EMAIL_DOMAINS = {"example.com", "domain.com", "email.com", "sentry.io", "wixpress.com", "yourdomain.com"}
_FILE_LIKE_TLDS = {"png", "jpg", "jpeg", "gif", "svg", "webp", "css", "js", "ico", "woff", "woff2"}


def normalize_email(value: str | None) -> str | None:
    if not value:
        return None
    email = value.strip().lower().removeprefix("mailto:").split("?")[0].strip()
    if not _EMAIL_FULL_RE.match(email):
        return None
    domain = email.rsplit("@", 1)[1]
    if domain in _JUNK_EMAIL_DOMAINS or domain.rsplit(".", 1)[-1] in _FILE_LIKE_TLDS:
        return None
    return email


_TOKEN_SPLIT_RE = re.compile(r"[\s<>\"'()\[\],;:|]+")
_MAX_EMAIL_LENGTH = 254


def extract_emails(text: str | None) -> list[str]:
    """Emails found in free text.

    Splits into tokens and only inspects those containing "@". Running the email regex
    over the whole text is quadratic on a long run of address-like characters (80k of them
    took ~12 s), which a real web page can easily contain.
    """
    if not text:
        return []
    seen: dict[str, None] = {}
    for token in _TOKEN_SPLIT_RE.split(text):
        if "@" not in token or len(token) > _MAX_EMAIL_LENGTH:
            continue
        for candidate in _EMAIL_RE.findall(token):
            email = normalize_email(candidate)
            if email:
                seen.setdefault(email)
    return list(seen)


# ---- website / social ------------------------------------------------------

_SOCIAL_HOSTS = {
    "facebook.com": "facebook",
    "fb.com": "facebook",
    "fb.me": "facebook",
    "instagram.com": "instagram",
}
# Hosts shared by countless unrelated businesses: never a business's own website, and
# useless for telling whether two records are the same business.
_SHARED_HOSTS = {
    "linktr.ee", "wa.me", "api.whatsapp.com", "whatsapp.com", "google.com", "goo.gl", "g.page",
    "maps.app.goo.gl", "youtube.com", "youtu.be", "tiktok.com", "twitter.com", "x.com", "linkedin.com",
    "olx.com.pk", "daraz.pk", "pakwheels.com",
}


@dataclass(frozen=True)
class SiteInfo:
    url: str | None
    domain: str | None
    social_platform: str | None = None
    social_url: str | None = None


def _host_matches(host: str, suffix_map_or_set) -> str | None:
    for known in suffix_map_or_set:
        if host == known or host.endswith("." + known):
            return known
    return None


def normalize_website(value: str | None) -> SiteInfo:
    """Split a raw URL into (own website | social page). Shared hosts yield nothing."""
    empty = SiteInfo(url=None, domain=None)
    if not value:
        return empty

    raw = value.strip()
    if not raw:
        return empty
    if "://" not in raw:
        raw = "https://" + raw
    parsed = urlparse(raw)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return empty

    host = parsed.hostname.lower().removeprefix("www.")
    if "." not in host:
        return empty

    social = _host_matches(host, _SOCIAL_HOSTS)
    if social:
        clean = f"https://{host}{parsed.path.rstrip('/')}"
        return SiteInfo(url=None, domain=None, social_platform=_SOCIAL_HOSTS[social], social_url=clean)
    if _host_matches(host, _SHARED_HOSTS):
        return empty

    path = parsed.path.rstrip("/")
    return SiteInfo(url=f"{parsed.scheme}://{host}{path}", domain=host)


# ---- names -----------------------------------------------------------------

_NAME_NOISE_WORDS = {"pvt", "private", "ltd", "limited", "co", "company", "the", "and", "smc", "inc", "llc"}


def normalize_name(name: str | None) -> str:
    """Lower-case, punctuation-free, without legal suffixes; used for matching, not display."""
    if not name:
        return ""
    words = re.sub(r"[^\w\s]", " ", name.lower().replace("&", " and ")).split()
    return " ".join(word for word in words if word not in _NAME_NOISE_WORDS)
