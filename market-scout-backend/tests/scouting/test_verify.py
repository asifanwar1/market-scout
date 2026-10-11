import dns.exception
import dns.name
import dns.resolver
import httpx
import pytest

from app.core.scouting import verify
from app.core.scouting.dedupe import BusinessKeys, near_miss
from app.core.scouting.enrichment.website import WebsiteEnricher
from app.core.scouting.verify import LookupUnavailable, MailDomainChecker

PUBLIC_IP = "93.184.216.34"


def checker(records: dict[str, str], unavailable=()):
    calls = []

    def lookup(domain):
        calls.append(domain)
        if domain in unavailable:
            raise LookupUnavailable(domain)
        return records[domain]

    return MailDomainChecker(lookup), calls


def test_a_domain_with_a_mail_server_is_deliverable():
    mail, _ = checker({"shop.pk": verify.RECORD_MX})

    result = mail.check("info@shop.pk")

    assert result.is_deliverable is True and result.note == verify.NOTE_DELIVERABLE


def test_a_domain_with_only_an_address_record_still_counts_but_says_so():
    mail, _ = checker({"shop.pk": verify.RECORD_ADDRESS})

    assert mail.check("info@shop.pk") == verify.EmailCheck(True, verify.NOTE_FALLBACK)


@pytest.mark.parametrize(
    "record, note",
    [
        (verify.RECORD_NO_DOMAIN, verify.NOTE_NO_DOMAIN),
        (verify.RECORD_NONE, verify.NOTE_NO_RECORDS),
        (verify.RECORD_NULL_MX, verify.NOTE_NULL_MX),
    ],
)
def test_domains_that_cannot_receive_mail_are_bad(record, note):
    mail, _ = checker({"gone.pk": record})

    assert mail.check("a@gone.pk") == verify.EmailCheck(False, note)


def test_a_lookup_that_cannot_be_completed_is_unknown_and_not_remembered():
    mail, calls = checker({}, unavailable={"slow.pk"})

    assert mail.check("a@slow.pk") == verify.EmailCheck(None, verify.NOTE_UNKNOWN)
    mail.check("b@slow.pk")
    assert calls == ["slow.pk", "slow.pk"]


def test_each_domain_is_looked_up_once_per_checker_and_case_is_ignored():
    mail, calls = checker({"shop.pk": verify.RECORD_MX})

    for address in ("a@shop.pk", "b@SHOP.pk", "c@Shop.PK"):
        mail.check(address)

    assert calls == ["shop.pk"]


@pytest.mark.parametrize("address", ["nodomain", "trailing@", ""])
def test_text_that_is_not_an_address_is_bad(address):
    mail, calls = checker({})

    assert mail.check(address) == verify.EmailCheck(False, verify.NOTE_BAD_ADDRESS) and calls == []


class FakeAnswer:
    def __init__(self, exchange):
        self.exchange = exchange


class FakeResolver:
    script: dict[tuple[str, str], object] = {}

    def __init__(self):
        self.timeout = self.lifetime = 0

    def resolve(self, domain, record_type):
        outcome = self.script[(domain, record_type)]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


@pytest.fixture()
def dns_script(monkeypatch):
    FakeResolver.script = {}
    monkeypatch.setattr(verify.dns.resolver, "Resolver", FakeResolver)
    return FakeResolver.script


def test_real_lookup_reads_mx_records(dns_script):
    dns_script[("shop.pk", "MX")] = [FakeAnswer(dns.name.from_text("mail.shop.pk."))]

    assert verify.lookup_mail_records("shop.pk") == verify.RECORD_MX


def test_real_lookup_recognises_a_null_mx(dns_script):
    dns_script[("shop.pk", "MX")] = [FakeAnswer(dns.name.root)]

    assert verify.lookup_mail_records("shop.pk") == verify.RECORD_NULL_MX


def test_real_lookup_reports_a_missing_domain(dns_script):
    dns_script[("gone.pk", "MX")] = dns.resolver.NXDOMAIN()

    assert verify.lookup_mail_records("gone.pk") == verify.RECORD_NO_DOMAIN


def test_real_lookup_falls_back_to_address_records(dns_script):
    dns_script[("shop.pk", "MX")] = dns.resolver.NoAnswer()
    dns_script[("shop.pk", "A")] = [object()]

    assert verify.lookup_mail_records("shop.pk") == verify.RECORD_ADDRESS


def test_real_lookup_says_none_when_nothing_answers(dns_script):
    dns_script[("shop.pk", "MX")] = dns.resolver.NoAnswer()
    dns_script[("shop.pk", "A")] = dns.resolver.NoAnswer()
    dns_script[("shop.pk", "AAAA")] = dns.resolver.NoAnswer()

    assert verify.lookup_mail_records("shop.pk") == verify.RECORD_NONE


@pytest.mark.parametrize("failure", [dns.exception.Timeout(), dns.resolver.NoNameservers()])
def test_real_lookup_raises_when_the_resolver_cannot_answer(dns_script, failure):
    dns_script[("shop.pk", "MX")] = failure

    with pytest.raises(LookupUnavailable):
        verify.lookup_mail_records("shop.pk")


def make_probe(handler, resolver=lambda host: [PUBLIC_IP]):
    client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False)
    return WebsiteEnricher("TestBot/1.0", client=client, resolver=resolver)


def test_a_site_that_answers_is_alive():
    probe = make_probe(lambda request: httpx.Response(200, text="hi")).probe("shop.pk")

    assert probe.is_alive is True


def test_a_site_that_turns_bots_away_is_still_alive():
    probe = make_probe(lambda request: httpx.Response(403)).probe("shop.pk")

    assert probe.is_alive is True and "automated" in probe.note


@pytest.mark.parametrize("status", [404, 410, 500, 503])
def test_error_pages_mean_the_site_is_dead(status):
    probe = make_probe(lambda request: httpx.Response(status)).probe("shop.pk")

    assert probe.is_alive is False and str(status) in probe.note


def test_redirects_are_followed_to_the_final_page():
    def handler(request):
        if request.url.host == "old.pk":
            return httpx.Response(301, headers={"Location": "https://new.pk/"})
        return httpx.Response(200, text="hi")

    assert make_probe(handler).probe("old.pk").is_alive is True


def test_a_redirect_loop_is_dead():
    probe = make_probe(lambda request: httpx.Response(302, headers={"Location": "https://shop.pk/again"})).probe("shop.pk")

    assert probe.is_alive is False and "loop" in probe.note


def test_an_unknown_host_is_dead_but_a_slow_one_is_unknown():
    assert make_probe(lambda request: httpx.Response(200), lambda host: []).probe("nowhere.pk").is_alive is False

    def slow(request):
        raise httpx.ReadTimeout("slow")

    assert make_probe(slow).probe("shop.pk").is_alive is None

    def refused(request):
        raise httpx.ConnectError("refused")

    assert make_probe(refused).probe("shop.pk").is_alive is False


def test_private_addresses_are_never_visited():
    called = []
    probe = make_probe(lambda request: called.append(1) or httpx.Response(200), resolver=lambda host: ["10.0.0.5"]).probe("intranet.pk")

    assert probe.is_alive is None and called == []


def test_text_that_is_not_a_website_is_dead():
    assert make_probe(lambda request: httpx.Response(200)).probe("not a url").is_alive is False


def keys(name, phones=(), lat=None, lon=None):
    return BusinessKeys(name, frozenset(phones), None, lat, lon)


def test_the_same_phone_under_a_very_different_name_is_a_near_miss():
    miss = near_miss(keys("al noor solar", ["+923001234567"]), keys("zeta traders", ["+923001234567"]))

    assert miss is not None and miss.reason == "phone" and miss.similarity < 40


def test_a_similar_name_close_by_is_a_near_miss():
    miss = near_miss(keys("noor solar systems", lat=31.5000, lon=74.3000), keys("noor solar", lat=31.5010, lon=74.3010))

    assert miss is not None and miss.reason == "location" and miss.similarity >= 60


def test_similar_names_far_apart_or_different_names_close_by_are_not():
    assert near_miss(keys("noor solar", lat=31.5, lon=74.3), keys("noor solar", lat=31.6, lon=74.4)) is None
    assert near_miss(keys("noor solar", lat=31.5, lon=74.3), keys("quick tyres", lat=31.5, lon=74.3)) is None
    assert near_miss(keys("noor solar"), keys("noor solar")) is None
