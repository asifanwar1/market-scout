import copy

import pytest

PROFILE_PAYLOAD = {
    "name": "Water Pumps",
    "description": "Pump dealers and installers.",
    "segments": [
        {"name": "Dealer", "match_rules": {"name_patterns": ["dealer"]}, "sort_order": 1},
        {"name": "Installer", "slug": "installer", "sort_order": 2},
    ],
    "search_terms": [
        {
            "text": "water pump dealer",
            "segment_slug": "dealer",
            "osm_filter": {"clauses": [["shop=hardware", "name~pump|motor"]]},
        },
        {"text": "pump installer", "segment_slug": "installer"},
        {"text": "pump ki dukan", "segment_slug": "dealer", "language": "ur-roman"},
    ],
}


@pytest.fixture()
def payload():
    return copy.deepcopy(PROFILE_PAYLOAD)


@pytest.fixture()
def created_profile(client, admin_user, auth_headers, payload):
    response = client.post("/api/v1/profiles/", headers=auth_headers(admin_user), json=payload)
    assert response.status_code == 201, response.text
    return response.json()


# ---- create / read --------------------------------------------------------

def test_create_profile_with_segments_and_terms(created_profile):
    assert created_profile["slug"] == "water-pumps"
    assert [s["slug"] for s in created_profile["segments"]] == ["dealer", "installer"]
    assert created_profile["segments"][0]["match_rules"] == {"name_patterns": ["dealer"]}
    assert len(created_profile["search_terms"]) == 3
    by_text = {t["text"]: t for t in created_profile["search_terms"]}
    assert by_text["water pump dealer"]["segment_slug"] == "dealer"
    assert by_text["water pump dealer"]["osm_filter"]["clauses"] == [["shop=hardware", "name~pump|motor"]]
    assert by_text["pump installer"]["osm_filter"] is None
    assert by_text["pump ki dukan"]["language"] == "ur-roman"
    # Defaults are filled in.
    assert created_profile["scoring_config"]["has_phone"] == 30
    assert created_profile["is_active"] is True


def test_sales_can_read_but_not_write(client, created_profile, sales_user, auth_headers, payload):
    headers = auth_headers(sales_user)
    assert client.get("/api/v1/profiles/", headers=headers).status_code == 200
    assert client.get(f"/api/v1/profiles/{created_profile['id']}", headers=headers).status_code == 200
    payload["name"] = "Other"
    assert client.post("/api/v1/profiles/", headers=headers, json=payload).status_code == 403
    assert client.put(f"/api/v1/profiles/{created_profile['id']}", headers=headers, json={"name": "X"}).status_code == 403
    assert client.delete(f"/api/v1/profiles/{created_profile['id']}", headers=headers).status_code == 403


def test_requires_authentication(client):
    assert client.get("/api/v1/profiles/").status_code == 401


def test_duplicate_name_conflicts(client, created_profile, admin_user, auth_headers, payload):
    response = client.post("/api/v1/profiles/", headers=auth_headers(admin_user), json=payload)
    assert response.status_code == 409


def test_list_shows_counts_and_supports_search_and_active_filter(client, created_profile, admin_user, sales_user, auth_headers):
    client.post(
        "/api/v1/profiles/", headers=auth_headers(admin_user),
        json={"name": "CCTV Cameras", "is_active": False},
    )
    headers = auth_headers(sales_user)

    everything = client.get("/api/v1/profiles/", headers=headers).json()
    assert everything["count"] == 2
    pumps = next(p for p in everything["data"] if p["slug"] == "water-pumps")
    assert pumps["segment_count"] == 2 and pumps["term_count"] == 3

    assert client.get("/api/v1/profiles/?search=pump", headers=headers).json()["count"] == 1
    inactive = client.get("/api/v1/profiles/?is_active=false", headers=headers).json()
    assert [p["name"] for p in inactive["data"]] == ["CCTV Cameras"]


def test_get_missing_profile_returns_404(client, sales_user, auth_headers):
    assert client.get("/api/v1/profiles/9999", headers=auth_headers(sales_user)).status_code == 404


# ---- validation -----------------------------------------------------------

def test_term_referring_to_unknown_segment_is_rejected(client, admin_user, auth_headers, payload):
    payload["search_terms"][0]["segment_slug"] = "wholesaler"
    response = client.post("/api/v1/profiles/", headers=auth_headers(admin_user), json=payload)
    assert response.status_code == 422


def test_duplicate_segment_slugs_and_terms_are_rejected(client, admin_user, auth_headers, payload):
    headers = auth_headers(admin_user)

    duplicate_segments = copy.deepcopy(payload)
    duplicate_segments["segments"].append({"name": "Dealer"})
    assert client.post("/api/v1/profiles/", headers=headers, json=duplicate_segments).status_code == 422

    duplicate_terms = copy.deepcopy(payload)
    duplicate_terms["search_terms"].append({"text": "Water Pump Dealer", "segment_slug": "dealer"})
    assert client.post("/api/v1/profiles/", headers=headers, json=duplicate_terms).status_code == 422


@pytest.mark.parametrize(
    "condition",
    [
        'name~solar"];out;//',   # quote / statement injection into the Overpass query
        "shop=hard;ware",        # semicolon
        "no operator here",      # not key=value / key~regex
        "name~(unclosed",        # invalid regex
        "=value",                # missing key
    ],
)
def test_unsafe_or_malformed_osm_conditions_are_rejected(client, admin_user, auth_headers, payload, condition):
    payload["search_terms"][0]["osm_filter"] = {"clauses": [[condition]]}
    response = client.post("/api/v1/profiles/", headers=auth_headers(admin_user), json=payload)
    assert response.status_code == 422


def test_osm_filter_size_limits(client, admin_user, auth_headers, payload):
    headers = auth_headers(admin_user)
    payload["search_terms"][0]["osm_filter"] = {"clauses": []}
    assert client.post("/api/v1/profiles/", headers=headers, json=payload).status_code == 422
    payload["search_terms"][0]["osm_filter"] = {"clauses": [["a=1"] * 6]}
    assert client.post("/api/v1/profiles/", headers=headers, json=payload).status_code == 422


def test_invalid_match_rule_regex_is_rejected(client, admin_user, auth_headers, payload):
    payload["segments"][0]["match_rules"] = {"name_patterns": ["(unclosed"]}
    assert client.post("/api/v1/profiles/", headers=auth_headers(admin_user), json=payload).status_code == 422


def test_scoring_weights_are_bounded(client, admin_user, auth_headers, payload):
    payload["scoring_config"] = {"has_phone": 500}
    assert client.post("/api/v1/profiles/", headers=auth_headers(admin_user), json=payload).status_code == 422


# ---- update (nested sync) -------------------------------------------------

def test_update_scalars_keeps_slug_and_leaves_lists_alone(client, created_profile, admin_user, auth_headers):
    response = client.put(
        f"/api/v1/profiles/{created_profile['id']}",
        headers=auth_headers(admin_user),
        json={"name": "Pumps & Motors", "is_active": False, "scoring_config": {"has_phone": 50}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Pumps & Motors"
    assert body["slug"] == "water-pumps"
    assert body["is_active"] is False
    assert body["scoring_config"]["has_phone"] == 50
    assert len(body["segments"]) == 2 and len(body["search_terms"]) == 3


def test_update_rename_to_existing_name_conflicts(client, created_profile, admin_user, auth_headers):
    headers = auth_headers(admin_user)
    client.post("/api/v1/profiles/", headers=headers, json={"name": "CCTV Cameras"})
    response = client.put(f"/api/v1/profiles/{created_profile['id']}", headers=headers, json={"name": "CCTV Cameras"})
    assert response.status_code == 409


def test_update_syncs_segments_by_id_and_cascades_removed_terms(client, created_profile, admin_user, auth_headers):
    headers = auth_headers(admin_user)
    dealer, installer = created_profile["segments"]

    response = client.put(
        f"/api/v1/profiles/{created_profile['id']}",
        headers=headers,
        json={
            "segments": [
                # Keep "dealer" (same id, renamed), drop "installer", add "wholesaler".
                {"id": dealer["id"], "name": "Authorised Dealer", "slug": "dealer"},
                {"name": "Wholesaler"},
            ],
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()

    segments = {s["slug"]: s for s in body["segments"]}
    assert set(segments) == {"dealer", "wholesaler"}
    assert segments["dealer"]["id"] == dealer["id"]          # identity preserved
    assert segments["dealer"]["name"] == "Authorised Dealer"
    assert "installer" not in segments                       # (its row id may be reused by SQLite, so check by slug)
    # The installer's term went with it; the dealer's two terms survive.
    assert sorted(t["text"] for t in body["search_terms"]) == ["pump ki dukan", "water pump dealer"]


def test_update_syncs_terms_and_can_target_new_segments(client, created_profile, admin_user, auth_headers):
    headers = auth_headers(admin_user)
    kept = next(t for t in created_profile["search_terms"] if t["text"] == "water pump dealer")

    response = client.put(
        f"/api/v1/profiles/{created_profile['id']}",
        headers=headers,
        json={
            "segments": [
                {"id": s["id"], "name": s["name"], "slug": s["slug"]} for s in created_profile["segments"]
            ] + [{"name": "Retailer"}],
            "search_terms": [
                {"id": kept["id"], "text": "submersible pump dealer", "segment_slug": "dealer", "is_active": False},
                {"text": "pump shop", "segment_slug": "retailer"},
            ],
        },
    )
    assert response.status_code == 200, response.text
    terms = {t["text"]: t for t in response.json()["search_terms"]}
    assert set(terms) == {"submersible pump dealer", "pump shop"}
    assert terms["submersible pump dealer"]["id"] == kept["id"]
    assert terms["submersible pump dealer"]["is_active"] is False
    assert terms["submersible pump dealer"]["osm_filter"] is None    # replaced by the payload's value
    assert terms["pump shop"]["segment_slug"] == "retailer"


def test_replacing_segments_and_terms_without_ids_works_even_when_slugs_and_texts_repeat(
    client, created_profile, admin_user, auth_headers
):
    """An id-less item is a new one. A client that lost its ids (a stale form) replaces the
    segment/term with a fresh copy; the database must not trip over the unique (slug / text)
    the old copy still held mid-update."""
    response = client.put(
        f"/api/v1/profiles/{created_profile['id']}",
        headers=auth_headers(admin_user),
        json={
            "segments": [{"name": "Dealer", "slug": "dealer"}, {"name": "Installer", "slug": "installer"}],
            "search_terms": [
                {"text": "water pump dealer", "segment_slug": "dealer"},
                {"text": "pump installer", "segment_slug": "installer"},
            ],
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert [s["slug"] for s in body["segments"]] == ["dealer", "installer"]       # no duplicates left behind
    assert sorted(t["text"] for t in body["search_terms"]) == ["pump installer", "water pump dealer"]
    # The replaced terms carry only what was sent: the old term's OSM filter is gone with it.
    assert all(t["osm_filter"] is None for t in body["search_terms"])


def test_update_rejects_items_from_other_profiles_and_unknown_segments(client, created_profile, admin_user, auth_headers):
    headers = auth_headers(admin_user)
    other = client.post(
        "/api/v1/profiles/", headers=headers,
        json={"name": "CCTV Cameras", "segments": [{"name": "Dealer"}]},
    ).json()
    url = f"/api/v1/profiles/{created_profile['id']}"

    foreign_segment = client.put(url, headers=headers, json={"segments": [{"id": other["segments"][0]["id"], "name": "Dealer"}]})
    assert foreign_segment.status_code == 400

    unknown_slug = client.put(url, headers=headers, json={"search_terms": [{"text": "pump shop", "segment_slug": "nope"}]})
    assert unknown_slug.status_code == 400

    # The failed updates changed nothing.
    assert len(client.get(url, headers=headers).json()["segments"]) == 2


def test_delete_profile_removes_everything_beneath_it(client, created_profile, admin_user, auth_headers, db_session):
    from app.features.profiles.models import ProfileSearchTerm, ProfileSegment

    headers = auth_headers(admin_user)
    assert client.delete(f"/api/v1/profiles/{created_profile['id']}", headers=headers).status_code == 204
    assert client.get(f"/api/v1/profiles/{created_profile['id']}", headers=headers).status_code == 404
    assert db_session.query(ProfileSegment).count() == 0
    assert db_session.query(ProfileSearchTerm).count() == 0
