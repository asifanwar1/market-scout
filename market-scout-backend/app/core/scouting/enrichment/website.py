import ipaddress
import re
import socket
from collections.abc import Callable
from dataclasses import dataclass, field
from http import HTTPStatus
from urllib.parse import parse_qs, unquote, urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

from app.core.constants import PLATFORM_FACEBOOK, PLATFORM_INSTAGRAM, URL_SCHEMES
from app.core.scouting.normalize import (
    PhoneInfo,
    extract_emails,
    extract_phones,
    normalize_email,
    normalize_website,
)

SOCKADDR_INDEX = 4
ADDRESS_INDEX = 0
REQUEST_TIMEOUT_SECONDS = 10
HTML_CONTENT_TYPE = "html"
CONTENT_TYPE_HEADER = "Content-Type"
MAILTO_PREFIX = "mailto:"
TEL_PREFIX = "tel:"
WHATSAPP_SCHEME = "whatsapp:"
WHATSAPP_LINK_MARKERS = ("wa.me/", "whatsapp.com/send")
MIN_WHATSAPP_DIGITS = 8
CONTACT_PAGE_KEYWORD = "contact"
ABOUT_PAGE_KEYWORD = "about"
HIDDEN_TEXT_TAGS = ("script", "style", "noscript", "svg", "template")
WHITESPACE = re.compile(r"\s+")
PAGE_SEPARATOR = " "


MAX_PAGE_BYTES = 1_500_000
PROBE_BLOCKED_STATUSES = (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN, HTTPStatus.TOO_MANY_REQUESTS)
PROBE_ALIVE = "The website answers"
PROBE_BLOCKS_BOTS = "The website answers but turns away automated visits"
PROBE_NOT_A_URL = "Not a usable website address"
PROBE_NOT_PUBLIC = "Skipped: not a public address"
PROBE_NO_SUCH_HOST = "The website's domain could not be found"
PROBE_BAD_REDIRECT = "The website redirects nowhere"
PROBE_TIMED_OUT = "The website took too long to answer"
PROBE_UNREACHABLE = "The website could not be reached"
PROBE_HTTP_ERROR = "The website returned HTTP {status}"
PROBE_TOO_MANY_REDIRECTS = "The website redirects in a loop"
MAX_TEXT_CHARS = 300_000
MAX_REDIRECTS = 3
MAX_ITEMS = 5
_SOCIAL_NON_PROFILE_PATHS = ("/sharer", "/share", "/plugins", "/tr", "/dialog", "/login", "/intent")


class EnrichmentError(Exception):
    pass


class UnsafeUrlError(EnrichmentError):
    pass


@dataclass
class WebsiteContacts:
    emails: list[str] = field(default_factory=list)
    phones: list[PhoneInfo] = field(default_factory=list)
    whatsapp: list[str] = field(default_factory=list)
    facebook: str | None = None
    instagram: str | None = None
    blocked_by_robots: bool = False

    @property
    def is_empty(self) -> bool:
        return not (self.emails or self.phones or self.whatsapp or self.facebook or self.instagram)


@dataclass
class WebsiteText:
    text: str = ""
    pages_read: int = 0
    truncated: bool = False
    blocked_by_robots: bool = False


def default_resolver(host: str) -> list[str]:
    try:
        return sorted({info[SOCKADDR_INDEX][ADDRESS_INDEX] for info in socket.getaddrinfo(host, None)})
    except socket.gaierror as exc:
        raise EnrichmentError(f"Could not resolve {host}") from exc


@dataclass
class SiteProbe:
    is_alive: bool | None
    note: str


class WebsiteEnricher:
    def __init__(
        self,
        user_agent: str,
        client: httpx.Client | None = None,
        resolver: Callable[[str], list[str]] = default_resolver,
    ):
        self._user_agent = user_agent
        self._client = client or httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS, follow_redirects=False)
        self._resolver = resolver

    def enrich(self, url: str) -> WebsiteContacts:
        site = normalize_website(url)
        if not site.url:
            raise EnrichmentError("Not a usable website URL")

        robots = self._load_robots(site.url)
        if not robots.can_fetch(self._user_agent, site.url):
            return WebsiteContacts(blocked_by_robots=True)

        html, final_url = self._fetch(site.url)
        contacts = _extract(html, final_url)

        contact_page = _find_contact_page(html, final_url)
        if contact_page and robots.can_fetch(self._user_agent, contact_page):
            try:
                page_html, page_url = self._fetch(contact_page)
            except EnrichmentError:
                pass
            else:
                _merge(contacts, _extract(page_html, page_url))
        return contacts


    def probe(self, url: str) -> SiteProbe:
        site = normalize_website(url)
        if not site.url:
            return SiteProbe(False, PROBE_NOT_A_URL)
        current = site.url
        for _ in range(MAX_REDIRECTS + 1):
            try:
                self._assert_public(current)
            except UnsafeUrlError:
                return SiteProbe(None, PROBE_NOT_PUBLIC)
            except EnrichmentError:
                return SiteProbe(False, PROBE_NO_SUCH_HOST)
            try:
                with self._client.stream("GET", current, headers={"User-Agent": self._user_agent}) as response:
                    status = response.status_code
                    if response.is_redirect:
                        location = response.headers.get("Location")
                        if not location:
                            return SiteProbe(False, PROBE_BAD_REDIRECT)
                        current = urljoin(current, location)
                        continue
            except httpx.TimeoutException:
                return SiteProbe(None, PROBE_TIMED_OUT)
            except httpx.HTTPError:
                return SiteProbe(False, PROBE_UNREACHABLE)
            if status in PROBE_BLOCKED_STATUSES:
                return SiteProbe(True, PROBE_BLOCKS_BOTS)
            if status >= HTTPStatus.BAD_REQUEST:
                return SiteProbe(False, PROBE_HTTP_ERROR.format(status=status))
            return SiteProbe(True, PROBE_ALIVE)
        return SiteProbe(False, PROBE_TOO_MANY_REDIRECTS)

    def read_text(self, url: str, max_chars: int) -> WebsiteText:
        site = normalize_website(url)
        if not site.url:
            raise EnrichmentError("Not a usable website URL")

        robots = self._load_robots(site.url)
        if not robots.can_fetch(self._user_agent, site.url):
            return WebsiteText(blocked_by_robots=True)

        html, final_url = self._fetch(site.url)
        parts = [_visible_text(html)]
        about_page = _find_linked_page(html, final_url, ABOUT_PAGE_KEYWORD)
        if about_page and robots.can_fetch(self._user_agent, about_page):
            try:
                page_html, _ = self._fetch(about_page)
            except EnrichmentError:
                pass
            else:
                parts.append(_visible_text(page_html))

        text = PAGE_SEPARATOR.join(part for part in parts if part)
        return WebsiteText(text=text[:max_chars], pages_read=len(parts), truncated=len(text) > max_chars)

    def _assert_public(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in URL_SCHEMES or not parsed.hostname:
            raise UnsafeUrlError("Only http(s) URLs are fetched")
        try:
            addresses = [str(ipaddress.ip_address(parsed.hostname))]
        except ValueError:
            addresses = self._resolver(parsed.hostname)
        if not addresses:
            raise EnrichmentError(f"Could not resolve {parsed.hostname}")
        if not all(ipaddress.ip_address(address).is_global for address in addresses):
            raise UnsafeUrlError(f"{parsed.hostname} is not a public address")

    def _fetch(self, url: str) -> tuple[str, str]:
        current = url
        for _ in range(MAX_REDIRECTS + 1):
            self._assert_public(current)
            try:
                with self._client.stream("GET", current, headers={"User-Agent": self._user_agent}) as response:
                    if response.is_redirect:
                        location = response.headers.get("Location")
                        if not location:
                            raise EnrichmentError("Redirect without a location")
                        current = urljoin(current, location)
                        continue
                    if response.status_code != HTTPStatus.OK:
                        raise EnrichmentError(f"HTTP {response.status_code}")
                    if HTML_CONTENT_TYPE not in response.headers.get(CONTENT_TYPE_HEADER, HTML_CONTENT_TYPE).lower():
                        raise EnrichmentError("Not an HTML page")
                    body = bytearray()
                    for chunk in response.iter_bytes():
                        body.extend(chunk)
                        if len(body) > MAX_PAGE_BYTES:
                            break
                    encoding = response.encoding or "utf-8"
                    return bytes(body[:MAX_PAGE_BYTES]).decode(encoding, errors="replace"), current
            except httpx.HTTPError as exc:
                raise EnrichmentError(f"Fetch failed: {exc.__class__.__name__}") from exc
        raise EnrichmentError("Too many redirects")

    def _load_robots(self, url: str) -> RobotFileParser:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        parser = RobotFileParser()
        try:
            text, _ = self._fetch(robots_url)
        except EnrichmentError:
            parser.parse([])
            return parser
        parser.parse(text.splitlines())
        return parser


def _extract(html: str, base_url: str) -> WebsiteContacts:
    soup = BeautifulSoup(html, "html.parser")
    contacts = WebsiteContacts()

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        lowered = href.lower()

        if lowered.startswith(MAILTO_PREFIX):
            email = normalize_email(unquote(href))
            if email:
                _append_unique(contacts.emails, email)
        elif lowered.startswith(TEL_PREFIX):
            for phone in extract_phones(unquote(href[len(TEL_PREFIX):])):
                _append_phone(contacts.phones, phone)
        elif any(marker in lowered for marker in WHATSAPP_LINK_MARKERS) or lowered.startswith(WHATSAPP_SCHEME):
            number = _whatsapp_number(href)
            if number:
                _append_unique(contacts.whatsapp, number)
        else:
            _collect_social(contacts, urljoin(base_url, href))

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(" ")[:MAX_TEXT_CHARS]
    for email in extract_emails(text):
        _append_unique(contacts.emails, email)
    for phone in extract_phones(text):
        _append_phone(contacts.phones, phone)

    contacts.emails = contacts.emails[:MAX_ITEMS]
    contacts.phones = contacts.phones[:MAX_ITEMS]
    contacts.whatsapp = contacts.whatsapp[:MAX_ITEMS]
    return contacts


def _whatsapp_number(href: str) -> str | None:
    parsed = urlparse(href)
    digits = parse_qs(parsed.query).get("phone", [""])[0] or parsed.path.strip("/").split("/")[-1]
    digits = "".join(ch for ch in digits if ch.isdigit())
    if len(digits) < MIN_WHATSAPP_DIGITS:
        return None
    phones = extract_phones("+" + digits)
    return phones[0].e164 if phones else None


def _collect_social(contacts: WebsiteContacts, url: str) -> None:
    site = normalize_website(url)
    if not site.social_platform or not site.social_url:
        return
    path = urlparse(site.social_url).path
    if len(path.strip("/")) == 0 or path.lower().startswith(_SOCIAL_NON_PROFILE_PATHS):
        return
    if site.social_platform == PLATFORM_FACEBOOK and contacts.facebook is None:
        contacts.facebook = site.social_url
    elif site.social_platform == PLATFORM_INSTAGRAM and contacts.instagram is None:
        contacts.instagram = site.social_url


def _visible_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(HIDDEN_TEXT_TAGS):
        tag.decompose()
    return WHITESPACE.sub(" ", soup.get_text(" ")).strip()


def _find_contact_page(html: str, base_url: str) -> str | None:
    return _find_linked_page(html, base_url, CONTACT_PAGE_KEYWORD)


def _find_linked_page(html: str, base_url: str, keyword: str) -> str | None:
    base_host = urlparse(base_url).hostname
    for anchor in BeautifulSoup(html, "html.parser").find_all("a", href=True):
        label = f"{anchor.get_text(' ')} {anchor['href']}".lower()
        if keyword not in label:
            continue
        target = urljoin(base_url, anchor["href"])
        if urlparse(target).hostname == base_host and target.split("#")[0] != base_url:
            return target.split("#")[0]
    return None


def _merge(into: WebsiteContacts, extra: WebsiteContacts) -> None:
    for email in extra.emails:
        _append_unique(into.emails, email)
    for phone in extra.phones:
        _append_phone(into.phones, phone)
    for number in extra.whatsapp:
        _append_unique(into.whatsapp, number)
    into.facebook = into.facebook or extra.facebook
    into.instagram = into.instagram or extra.instagram
    into.emails, into.phones, into.whatsapp = into.emails[:MAX_ITEMS], into.phones[:MAX_ITEMS], into.whatsapp[:MAX_ITEMS]


def _append_unique(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def _append_phone(items: list[PhoneInfo], phone: PhoneInfo) -> None:
    if all(existing.e164 != phone.e164 for existing in items):
        items.append(phone)
