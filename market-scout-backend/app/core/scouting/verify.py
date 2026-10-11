from collections.abc import Callable
from dataclasses import dataclass

import dns.exception
import dns.name
import dns.resolver

EMAIL_SEPARATOR = "@"
DNS_TIMEOUT_SECONDS = 5.0
RECORD_MX = "mx"
RECORD_ADDRESS = "address"
RECORD_NONE = "none"
RECORD_NULL_MX = "null_mx"
RECORD_NO_DOMAIN = "no_domain"
RECORD_TYPE_MX = "MX"
ADDRESS_RECORD_TYPES = ("A", "AAAA")

NOTE_DELIVERABLE = "The email domain accepts mail"
NOTE_FALLBACK = "The email domain has no mail server listed but can be reached, so mail may still arrive"
NOTE_NO_DOMAIN = "The email domain does not exist"
NOTE_NO_RECORDS = "The email domain has no mail server"
NOTE_NULL_MX = "The email domain says it does not accept mail"
NOTE_UNKNOWN = "The email domain could not be looked up right now"
NOTE_BAD_ADDRESS = "Not a usable email address"


class LookupUnavailable(Exception):
    pass


@dataclass(frozen=True)
class EmailCheck:
    is_deliverable: bool | None
    note: str


def lookup_mail_records(domain: str, timeout: float = DNS_TIMEOUT_SECONDS) -> str:
    resolver = dns.resolver.Resolver()
    resolver.timeout = timeout
    resolver.lifetime = timeout
    try:
        answers = resolver.resolve(domain, RECORD_TYPE_MX)
    except dns.resolver.NXDOMAIN:
        return RECORD_NO_DOMAIN
    except dns.resolver.NoAnswer:
        answers = None
    except (dns.resolver.NoNameservers, dns.exception.Timeout, dns.resolver.LifetimeTimeout) as exc:
        raise LookupUnavailable(domain) from exc

    if answers is not None:
        exchanges = [record.exchange for record in answers]
        if all(exchange == dns.name.root for exchange in exchanges):
            return RECORD_NULL_MX
        return RECORD_MX

    for record_type in ADDRESS_RECORD_TYPES:
        try:
            resolver.resolve(domain, record_type)
            return RECORD_ADDRESS
        except dns.resolver.NoAnswer:
            continue
        except dns.resolver.NXDOMAIN:
            return RECORD_NO_DOMAIN
        except (dns.resolver.NoNameservers, dns.exception.Timeout, dns.resolver.LifetimeTimeout) as exc:
            raise LookupUnavailable(domain) from exc
    return RECORD_NONE


_VERDICTS: dict[str, EmailCheck] = {
    RECORD_MX: EmailCheck(True, NOTE_DELIVERABLE),
    RECORD_ADDRESS: EmailCheck(True, NOTE_FALLBACK),
    RECORD_NO_DOMAIN: EmailCheck(False, NOTE_NO_DOMAIN),
    RECORD_NONE: EmailCheck(False, NOTE_NO_RECORDS),
    RECORD_NULL_MX: EmailCheck(False, NOTE_NULL_MX),
}


class MailDomainChecker:
    def __init__(self, lookup: Callable[[str], str] = lookup_mail_records) -> None:
        self._lookup = lookup
        self._cache: dict[str, EmailCheck] = {}

    def check(self, email: str) -> EmailCheck:
        _, separator, domain = email.rpartition(EMAIL_SEPARATOR)
        domain = domain.strip().lower()
        if not separator or not domain:
            return EmailCheck(False, NOTE_BAD_ADDRESS)
        if domain not in self._cache:
            try:
                self._cache[domain] = _VERDICTS[self._lookup(domain)]
            except LookupUnavailable:
                return EmailCheck(None, NOTE_UNKNOWN)
        return self._cache[domain]
