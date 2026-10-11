import httpx
import pytest

from app.core.scouting.enrichment.website import EnrichmentError, UnsafeUrlError, WebsiteEnricher

PUBLIC_IP = "93.184.216.34"

HOME = """
<html><head><style>body { color: red }</style><script>var secret = "track";</script></head>
<body><nav><a href="/about-us">About us</a></nav>
<h1>Noor   Solar</h1><p>We design and install rooftop solar for homes.</p><noscript>enable js</noscript></body></html>
"""
ABOUT = "<html><body><p>Family business since 2009 serving Lahore.</p></body></html>"


def make_enricher(pages: dict[str, str], resolver=lambda host: [PUBLIC_IP]):
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        requested.append(url)
        page = pages.get(url)
        if page is None:
            return httpx.Response(404)
        return httpx.Response(200, text=page, headers={"Content-Type": "text/html; charset=utf-8"})

    client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False)
    return WebsiteEnricher("TestBot/1.0", client=client, resolver=resolver), requested


def test_reads_the_visible_text_of_the_home_page_and_the_about_page():
    enricher, requested = make_enricher({"https://noor.pk": HOME, "https://noor.pk/about-us": ABOUT})

    page = enricher.read_text("noor.pk", 5000)

    assert page.pages_read == 2 and page.truncated is False and page.blocked_by_robots is False
    assert "Noor Solar We design and install rooftop solar for homes." in page.text
    assert "Family business since 2009" in page.text
    assert "track" not in page.text and "color: red" not in page.text and "enable js" not in page.text
    assert "https://noor.pk/about-us" in requested


def test_whitespace_is_collapsed():
    enricher, _ = make_enricher({"https://noor.pk": "<html><body><p>a\n\n   b\t\tc</p></body></html>"})

    assert enricher.read_text("noor.pk", 100).text == "a b c"


def test_a_missing_about_page_is_not_an_error():
    enricher, _ = make_enricher({"https://noor.pk": HOME})

    page = enricher.read_text("noor.pk", 5000)

    assert page.pages_read == 1 and "rooftop solar" in page.text


def test_long_text_is_cut_and_marked_as_cut():
    enricher, _ = make_enricher({"https://noor.pk": "<html><body>" + "word " * 1000 + "</body></html>"})

    page = enricher.read_text("noor.pk", 500)

    assert len(page.text) == 500 and page.truncated is True


def test_text_that_fits_is_not_marked_as_cut():
    enricher, _ = make_enricher({"https://noor.pk": "<html><body>short</body></html>"})

    assert enricher.read_text("noor.pk", 500).truncated is False


def test_a_site_that_disallows_robots_is_not_read():
    enricher, requested = make_enricher({"https://noor.pk/robots.txt": "User-agent: *\nDisallow: /", "https://noor.pk": HOME})

    page = enricher.read_text("noor.pk", 5000)

    assert page.blocked_by_robots is True and page.text == ""
    assert "https://noor.pk" not in requested


def test_a_private_address_is_refused_before_anything_is_fetched():
    enricher, requested = make_enricher({"http://intranet.local": HOME}, resolver=lambda host: ["10.0.0.5"])

    with pytest.raises(UnsafeUrlError):
        enricher.read_text("http://intranet.local", 5000)

    assert requested == []


def test_an_unusable_url_or_a_failed_fetch_is_an_enrichment_error():
    enricher, _ = make_enricher({})

    with pytest.raises(EnrichmentError):
        enricher.read_text("", 5000)
    with pytest.raises(EnrichmentError, match="HTTP 404"):
        enricher.read_text("noor.pk", 5000)
