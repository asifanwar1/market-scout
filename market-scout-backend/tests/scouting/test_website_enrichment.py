import httpx
import pytest

from app.core.scouting.enrichment.website import EnrichmentError, UnsafeUrlError, WebsiteEnricher

PUBLIC_IP = "93.184.216.34"

HOME = """
<html><body>
  <a href="/contact-us">Contact</a>
  <a href="mailto:Info@AlNoorSolar.pk?subject=Hello">Email us</a>
  <a href="tel:+92-300-4438424">Call</a>
  <a href="https://wa.me/923014962026?text=hi">WhatsApp</a>
  <a href="https://www.facebook.com/alnoorsolar/">FB</a>
  <a href="https://www.facebook.com/sharer/sharer.php?u=x">Share</a>
  <a href="https://instagram.com/alnoor_solar">IG</a>
  <p>Office: 042-35771769</p>
  <script>var e = "hidden@tracker.io"</script>
</body></html>
"""

CONTACT = """<html><body>Sales: sales@alnoorsolar.pk<br>
<a href="https://api.whatsapp.com/send?phone=923004438424">wa</a></body></html>"""


def make_enricher(pages: dict[str, str | httpx.Response], resolver=lambda host: [PUBLIC_IP]):
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        requested.append(url)
        page = pages.get(url)
        if page is None:
            return httpx.Response(404)
        if isinstance(page, httpx.Response):
            return page
        return httpx.Response(200, text=page, headers={"Content-Type": "text/html; charset=utf-8"})

    client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False)
    return WebsiteEnricher("TestBot/1.0", client=client, resolver=resolver), requested


def test_extracts_contacts_from_homepage_and_contact_page():
    enricher, requested = make_enricher({
        "https://alnoorsolar.pk": HOME,
        "https://alnoorsolar.pk/contact-us": CONTACT,
    })

    contacts = enricher.enrich("alnoorsolar.pk")

    assert contacts.emails == ["info@alnoorsolar.pk", "sales@alnoorsolar.pk"]
    assert {p.e164 for p in contacts.phones} == {"+923004438424", "+924235771769"}
    assert contacts.whatsapp == ["+923014962026", "+923004438424"]
    assert contacts.facebook == "https://facebook.com/alnoorsolar"
    assert contacts.instagram == "https://instagram.com/alnoor_solar"
    assert "https://alnoorsolar.pk/contact-us" in requested


def test_survives_a_missing_contact_page():
    enricher, _ = make_enricher({"https://alnoorsolar.pk": HOME})
    contacts = enricher.enrich("https://alnoorsolar.pk")
    assert contacts.emails == ["info@alnoorsolar.pk"]


def test_robots_txt_disallow_is_honoured():
    enricher, requested = make_enricher({
        "https://alnoorsolar.pk/robots.txt": "User-agent: *\nDisallow: /",
        "https://alnoorsolar.pk": HOME,
    })
    contacts = enricher.enrich("https://alnoorsolar.pk")
    assert contacts.blocked_by_robots is True and contacts.is_empty
    assert "https://alnoorsolar.pk" not in requested


def test_robots_txt_that_allows_the_site_is_fine():
    enricher, _ = make_enricher({
        "https://alnoorsolar.pk/robots.txt": "User-agent: *\nDisallow: /admin",
        "https://alnoorsolar.pk": HOME,
    })
    assert enricher.enrich("https://alnoorsolar.pk").emails


@pytest.mark.parametrize(
    "url, resolver_result",
    [
        ("http://localhost/admin", ["127.0.0.1"]),
        ("http://internal.example.pk", ["10.0.0.5"]),
        ("http://metadata.example.pk", ["169.254.169.254"]),
        ("http://mixed.example.pk", [PUBLIC_IP, "192.168.1.10"]),
        ("http://192.168.0.1/router", []),
        ("http://[::1]/", []),
    ],
)
def test_refuses_non_public_addresses_without_fetching(url, resolver_result):
    enricher, requested = make_enricher({}, resolver=lambda host: resolver_result)
    with pytest.raises((UnsafeUrlError, EnrichmentError)):
        enricher.enrich(url)
    assert requested == []


def test_redirect_to_a_private_address_is_refused():
    def resolver(host):
        return ["127.0.0.1"] if host == "evil.internal" else [PUBLIC_IP]

    enricher, requested = make_enricher(
        {"https://shop.pk": httpx.Response(302, headers={"Location": "http://evil.internal/x"})},
        resolver=resolver,
    )
    with pytest.raises(UnsafeUrlError):
        enricher.enrich("https://shop.pk")
    assert requested == ["https://shop.pk/robots.txt", "https://shop.pk"]


def test_follows_safe_redirects_and_limits_them():
    enricher, _ = make_enricher({
        "http://shop.pk": httpx.Response(301, headers={"Location": "https://www.shop.pk/"}),
        "https://www.shop.pk/": "<a href='mailto:hi@shop.pk'>m</a>",
    })
    assert enricher.enrich("http://shop.pk").emails == ["hi@shop.pk"]

    loop, _ = make_enricher({"https://loop.pk": httpx.Response(302, headers={"Location": "https://loop.pk"})})
    with pytest.raises(EnrichmentError, match="redirects"):
        loop.enrich("https://loop.pk")


def test_non_html_error_status_and_bad_urls_raise_enrichment_errors():
    enricher, _ = make_enricher({
        "https://pdf.pk": httpx.Response(200, content=b"%PDF", headers={"Content-Type": "application/pdf"}),
    })
    with pytest.raises(EnrichmentError, match="HTML"):
        enricher.enrich("https://pdf.pk")
    with pytest.raises(EnrichmentError, match="HTTP 404"):
        enricher.enrich("https://gone.pk")
    with pytest.raises(EnrichmentError):
        enricher.enrich("not a url")
    with pytest.raises(EnrichmentError):
        enricher.enrich("https://www.facebook.com/somepage")


def test_oversized_pages_are_truncated_not_loaded_whole():
    huge = "<a href='mailto:early@shop.pk'>m</a>" + ("x" * 3_000_000) + "<a href='mailto:late@shop.pk'>m</a>"
    enricher, _ = make_enricher({"https://big.pk": huge})
    emails = enricher.enrich("https://big.pk").emails
    assert emails == ["early@shop.pk"]
