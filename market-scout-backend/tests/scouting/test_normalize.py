import pytest

from app.core.scouting.normalize import (
    extract_emails,
    extract_phones,
    extract_phones_from_many,
    normalize_email,
    normalize_name,
    normalize_website,
)


# ---- phones (formats taken from the real OpenStreetMap results) -------------

@pytest.mark.parametrize(
    "raw, expected",
    [
        ("+923236444660", ["+923236444660"]),
        ("0301-4962026, 0300-4438424", ["+923014962026", "+923004438424"]),
        ("+92 333 9993333; +92 42 37674194", ["+923339993333", "+924237674194"]),
        ("00923333675555", ["+923333675555"]),
        ("0092 300 1234567", ["+923001234567"]),
        ("03122787840", ["+923122787840"]),
        ("04235781769", ["+924235781769"]),
    ],
)
def test_extract_phones_handles_local_and_international_formats(raw, expected):
    assert [p.e164 for p in extract_phones(raw)] == expected


def test_extract_phones_flags_mobiles_and_landlines():
    mobile, landline = extract_phones("0300-4438424 and 042 3577 1769")
    assert mobile.is_mobile is True
    assert landline.is_mobile is False


@pytest.mark.parametrize("raw", [None, "", "no number here", "12345", "0000000000"])
def test_extract_phones_returns_nothing_for_junk(raw):
    assert extract_phones(raw) == []


def test_extract_phones_from_many_dedupes_across_fields():
    phones = extract_phones_from_many(["0300 4438424", "+92 300 4438424", "0301-4962026"])
    assert [p.e164 for p in phones] == ["+923004438424", "+923014962026"]


# ---- emails ---------------------------------------------------------------

def test_normalize_email_accepts_real_and_rejects_junk():
    assert normalize_email("  Sales@Solar-Shop.PK ") == "sales@solar-shop.pk"
    assert normalize_email("mailto:info@shop.pk?subject=Hi") == "info@shop.pk"
    for junk in [None, "", "not-an-email", "a@b", "logo@2x.png", "x@sentry.io", "you@example.com"]:
        assert normalize_email(junk) is None


def test_extract_emails_is_fast_on_long_runs_of_address_like_characters():
    import time

    started = time.monotonic()
    assert extract_emails("x" * 200_000 + " real@shop.pk") == ["real@shop.pk"]
    assert time.monotonic() - started < 1.0


def test_extract_emails_from_page_text_skips_asset_names():
    text = "Contact: Info@Solar.pk or sales@solar.pk. Image: banner@2x.png  sentry@sentry.io"
    assert extract_emails(text) == ["info@solar.pk", "sales@solar.pk"]


# ---- websites -------------------------------------------------------------

def test_normalize_website_cleans_own_sites():
    site = normalize_website("WWW.Solar-Shop.pk/")
    assert site.url == "https://solar-shop.pk"
    assert site.domain == "solar-shop.pk"
    assert site.social_platform is None

    assert normalize_website("http://solar-shop.pk/products/").url == "http://solar-shop.pk/products"


def test_normalize_website_routes_social_pages_away_from_website():
    site = normalize_website("https://www.facebook.com/alnoorsolar/")
    assert site.url is None and site.domain is None
    assert (site.social_platform, site.social_url) == ("facebook", "https://facebook.com/alnoorsolar")
    assert normalize_website("instagram.com/alnoor").social_platform == "instagram"


@pytest.mark.parametrize("value", [None, "", "  ", "ftp://x.pk", "localhost", "wa.me/923001234567", "https://linktr.ee/x"])
def test_normalize_website_ignores_unusable_or_shared_hosts(value):
    site = normalize_website(value)
    assert site.url is None and site.domain is None


# ---- names ----------------------------------------------------------------

def test_normalize_name_strips_case_punctuation_and_legal_suffixes():
    assert normalize_name("Al-Noor Solar (Pvt.) Ltd.") == "al noor solar"
    assert normalize_name("AL NOOR & Sons Co") == "al noor sons"
    assert normalize_name(None) == ""
