from datetime import UTC, datetime, timedelta

import pytest

from app.core.scouting.normalize import PhoneInfo
from app.core.scouting.types import RawBusiness
from app.features.businesses import ingest as service
from app.features.businesses.ingest import IngestContext
from app.features.businesses.models import Business, BusinessClassification, ContactPoint, SourceRecord
from app.features.geographies.models import Geography
from app.features.profiles.models import Profile
from app.features.runs.service import _profile_scoring
from scripts.seed import seed_geographies, seed_solar_profile

NOW = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)


@pytest.fixture()
def world(db_session):
    seed_geographies(db_session)
    seed_solar_profile(db_session)
    profile = db_session.query(Profile).filter_by(slug="solar-inverters-batteries").one()
    lahore = db_session.query(Geography).filter_by(slug="lahore").one()
    return profile, lahore


def ctx_for(world, hint="dealer", now=NOW) -> IngestContext:
    profile, lahore = world
    return IngestContext(
        run_id=None, geography_id=lahore.id, hint_segment_slug=hint, now=now, profile=_profile_scoring(profile)
    )


def raw(external_id="node/1", name="Al Noor Solar", source="osm", **overrides) -> RawBusiness:
    data = dict(
        source_key=source, external_id=external_id, name=name,
        latitude=31.5204, longitude=74.3587, phones=[], emails=[], categories=[],
    )
    data.update(overrides)
    return RawBusiness(**data)


def contacts(db, business):
    return {(c.kind, c.value) for c in db.query(ContactPoint).filter_by(business_id=business.id)}


def test_new_business_is_stored_with_contacts_provenance_and_classification(db_session, world):
    outcome = service.ingest_business(
        db_session,
        raw(
            phones=["0300-4438424, 042 3577 1769"], emails=["Info@AlNoor.pk"], website="https://www.alnoor.pk/",
            address="Mall Road, Lahore", categories=["shop=electrical"], raw={"tags": {"name": "Al Noor Solar"}},
        ),
        ctx_for(world),
    )
    db_session.commit()
    business = outcome.business

    assert outcome.created and (outcome.phone_count, outcome.has_website, outcome.has_email) == (2, True, True)
    assert business.name == "Al Noor Solar" and business.normalized_name == "al noor solar"
    assert business.website == "https://alnoor.pk" and business.website_domain == "alnoor.pk"
    assert business.geography_id == world[1].id and business.lead_status == "new"
    assert business.first_seen_at.replace(tzinfo=None) == NOW.replace(tzinfo=None)

    assert contacts(db_session, business) == {
        ("phone", "+923004438424"), ("phone", "+924235771769"), ("email", "info@alnoor.pk"),
    }
    mobile = db_session.query(ContactPoint).filter_by(value="+923004438424").one()
    landline = db_session.query(ContactPoint).filter_by(value="+924235771769").one()
    assert (mobile.is_mobile, mobile.whatsapp_likely, mobile.source_key) == (True, True, "osm")
    assert (landline.is_mobile, landline.whatsapp_likely) == (False, False)

    record = db_session.query(SourceRecord).one()
    assert (record.source_key, record.external_id, record.raw_payload) == ("osm", "node/1", {"tags": {"name": "Al Noor Solar"}})
    assert record.business_id == business.id


def test_classification_uses_the_search_segment_and_scores_signals(db_session, world):
    outcome = service.ingest_business(
        db_session,
        raw(phones=["03004438424"], emails=["a@alnoor.pk"], website="alnoor.pk", review_count=10, rating=4.5),
        ctx_for(world, hint="dealer"),
    )
    classification = db_session.query(BusinessClassification).one()

    assert {s.id: s.slug for s in world[0].segments}[classification.segment_id] == "dealer"
    assert classification.score == 80
    assert outcome.business.review_count == 10


def test_name_evidence_overrides_the_search_segment(db_session, world):
    outcome = service.ingest_business(
        db_session, raw(name="Noor Wholesale Traders", phones=["03004438424"]), ctx_for(world, hint="retailer")
    )
    classification = db_session.query(BusinessClassification).filter_by(business_id=outcome.business.id).one()
    assert {s.id: s.slug for s in world[0].segments}[classification.segment_id] == "wholesaler"
    assert classification.score == 30 + 20 + 20


def test_seeing_the_same_record_again_adds_nothing_but_refreshes_it(db_session, world):
    first = service.ingest_business(db_session, raw(phones=["03004438424"]), ctx_for(world))
    later = NOW + timedelta(days=1)
    second = service.ingest_business(
        db_session, raw(phones=["03004438424"], emails=["new@alnoor.pk"]), ctx_for(world, now=later)
    )

    assert second.created is False and second.business.id == first.business.id
    assert db_session.query(Business).count() == 1
    assert db_session.query(SourceRecord).count() == 1
    assert contacts(db_session, second.business) == {("phone", "+923004438424"), ("email", "new@alnoor.pk")}
    assert second.business.last_seen_at.replace(tzinfo=None) == later.replace(tzinfo=None)
    assert second.business.first_seen_at.replace(tzinfo=None) == NOW.replace(tzinfo=None)


def test_two_sources_describing_one_business_become_one_lead(db_session, world):
    osm = service.ingest_business(
        db_session,
        raw(phones=["03004438424"], categories=["shop=electrical"]),
        ctx_for(world),
    )
    places = service.ingest_business(
        db_session,
        raw(
            source="google_places", external_id="ChIJ-abc", name="Al-Noor Solar",
            latitude=31.5206, longitude=74.3588, phones=["+92 300 4438424", "042 3577 1769"],
            website="https://alnoor.pk", address="12 Mall Road", categories=["electronics_store"],
            rating=4.6, review_count=41,
        ),
        ctx_for(world),
    )

    assert places.created is False and places.business.id == osm.business.id
    business = places.business
    assert db_session.query(Business).count() == 1
    assert {r.source_key for r in db_session.query(SourceRecord)} == {"osm", "google_places"}
    assert business.website == "https://alnoor.pk" and business.address == "12 Mall Road"
    assert (business.rating, business.review_count) == (4.6, 41)
    assert business.categories == ["shop=electrical", "electronics_store"]
    assert contacts(db_session, business) == {("phone", "+923004438424"), ("phone", "+924235771769")}


def test_same_website_domain_merges_records_with_different_names_and_places(db_session, world):
    first = service.ingest_business(db_session, raw(name="Alnoor Energy", latitude=31.5, longitude=74.3, website="alnoor.pk"), ctx_for(world))
    second = service.ingest_business(
        db_session,
        raw(source="google_places", external_id="p1", name="A. Noor Solar Systems", latitude=31.9, longitude=74.9,
            website="https://www.alnoor.pk/contact"),
        ctx_for(world),
    )
    assert second.business.id == first.business.id


def test_a_shared_facebook_page_url_is_never_used_to_merge(db_session, world):
    a = service.ingest_business(db_session, raw("n/1", "Zahid Battery House", latitude=31.50, longitude=74.30,
                                                website="https://facebook.com/pages/zahid"), ctx_for(world))
    b = service.ingest_business(db_session, raw("n/2", "Karachi Mobile Center", latitude=31.60, longitude=74.40,
                                                website="https://facebook.com/pages/karachi"), ctx_for(world))
    assert a.business.id != b.business.id


def test_facebook_url_in_the_website_field_becomes_a_social_contact(db_session, world):
    outcome = service.ingest_business(db_session, raw(website="https://www.facebook.com/alnoorsolar/"), ctx_for(world))
    assert outcome.business.website is None and outcome.has_website is False
    assert contacts(db_session, outcome.business) == {("facebook", "https://facebook.com/alnoorsolar")}


def test_nearby_unrelated_shops_and_far_same_named_branches_stay_separate(db_session, world):
    a = service.ingest_business(db_session, raw("n/1", "Madina Electric", latitude=31.5204, longitude=74.3587), ctx_for(world))
    b = service.ingest_business(db_session, raw("n/2", "Bilal Traders", latitude=31.5205, longitude=74.3587), ctx_for(world))
    c = service.ingest_business(db_session, raw("n/3", "Madina Electric", latitude=31.6204, longitude=74.3587), ctx_for(world))
    assert len({a.business.id, b.business.id, c.business.id}) == 3


def test_shared_switchboard_number_does_not_merge_unrelated_names(db_session, world):
    a = service.ingest_business(db_session, raw("n/1", "Zahid Battery House", latitude=31.50, longitude=74.30, phones=["042 3577 1769"]), ctx_for(world))
    b = service.ingest_business(db_session, raw("n/2", "Karachi Mobile Center", latitude=31.60, longitude=74.40, phones=["042 3577 1769"]), ctx_for(world))
    assert a.business.id != b.business.id


def test_a_later_search_does_not_reclassify_without_name_evidence(db_session, world):
    service.ingest_business(db_session, raw(name="Noor Wholesale Traders"), ctx_for(world, hint="retailer"))
    again = service.ingest_business(db_session, raw(name="Noor Wholesale Traders"), ctx_for(world, hint="installer"))
    row = db_session.query(BusinessClassification).filter_by(business_id=again.business.id).one()
    assert {s.id: s.slug for s in world[0].segments}[row.segment_id] == "wholesaler"

    plain = service.ingest_business(db_session, raw("n/9", "Bright Future", latitude=30.0, longitude=70.0), ctx_for(world, hint="dealer"))
    service.ingest_business(db_session, raw("n/9", "Bright Future", latitude=30.0, longitude=70.0), ctx_for(world, hint="installer"))
    row = db_session.query(BusinessClassification).filter_by(business_id=plain.business.id).one()
    assert {s.id: s.slug for s in world[0].segments}[row.segment_id] == "dealer"


def test_unusable_phone_numbers_and_emails_are_ignored(db_session, world):
    outcome = service.ingest_business(
        db_session, raw(phones=["call us", "12345"], emails=["not-an-email", "logo@2x.png"]), ctx_for(world)
    )
    assert outcome.phone_count == 0 and outcome.has_email is False
    assert contacts(db_session, outcome.business) == set()
    assert db_session.query(BusinessClassification).one().score == 0


def test_enrichment_contacts_are_added_once_and_raise_the_score(db_session, world):
    outcome = service.ingest_business(db_session, raw(phones=["042 3577 1769"]), ctx_for(world))
    business, scoring = outcome.business, ctx_for(world).profile
    before = db_session.query(BusinessClassification).one().score

    kwargs = dict(
        emails=["sales@alnoor.pk"], phones=[PhoneInfo("+923004438424", True)], whatsapp=["+923014962026"],
        facebook="https://facebook.com/alnoor", instagram=None, source_key="website_enrichment",
    )
    added = service.add_enrichment_contacts(db_session, business, **kwargs)
    service.rescore_business(db_session, business, scoring)

    assert added == 4
    assert service.add_enrichment_contacts(db_session, business, **kwargs) == 0
    whatsapp = db_session.query(ContactPoint).filter_by(kind="whatsapp").one()
    assert (whatsapp.whatsapp_likely, whatsapp.source_key) == (True, "website_enrichment")
    assert before == 30
    assert db_session.query(BusinessClassification).one().score == 60


def test_a_number_marked_unreliable_is_not_used_to_match_but_is_still_stored(db_session, seeded_profile):
    ingest_business = service.ingest_business
    context = IngestContext(run_id=None, geography_id=None, hint_segment_slug=None, now=datetime.now(UTC),
                            profile=_profile_scoring(seeded_profile))

    def raw(external_id, name, unreliable):
        return RawBusiness(source_key="import:t", external_id=external_id, name=name, phones=["0330-5845448"],
                           unreliable_phones=["+923305845448"] if unreliable else [])

    first = ingest_business(db_session, raw("a", "Royal Energy Pakistan", False), context).business
    second = ingest_business(db_session, raw("b", "AFM Energy", True), context)
    third = ingest_business(db_session, raw("c", "AFM Energy", False), context)

    assert second.created and second.business.id != first.id
    assert not third.created and third.business.id == first.id
    assert {c.value for c in second.business.contact_points if c.kind == "phone"} == {"+923305845448"}
