import pytest


@pytest.fixture()
def hierarchy(client, admin_user, auth_headers):
    """Pakistan > Punjab > Lahore, created through the API."""
    headers = auth_headers(admin_user)
    country = client.post("/api/v1/geographies/", headers=headers, json={"name": "Pakistan", "level": "country"}).json()
    province = client.post(
        "/api/v1/geographies/",
        headers=headers,
        json={"name": "Punjab", "level": "province", "parent_id": country["id"]},
    ).json()
    city = client.post(
        "/api/v1/geographies/",
        headers=headers,
        json={
            "name": "Lahore", "level": "city", "parent_id": province["id"],
            "latitude": 31.5204, "longitude": 74.3587, "radius_km": 20,
        },
    ).json()
    return {"country": country, "province": province, "city": city}


def test_admin_builds_country_province_city_hierarchy(hierarchy):
    assert hierarchy["country"]["slug"] == "pakistan"
    assert hierarchy["province"]["level"] == "province"
    assert hierarchy["city"]["slug"] == "lahore"
    assert hierarchy["city"]["radius_km"] == 20


def test_sales_can_read_but_not_write(client, hierarchy, sales_user, auth_headers):
    headers = auth_headers(sales_user)
    assert client.get("/api/v1/geographies/", headers=headers).status_code == 200
    assert client.get(f"/api/v1/geographies/{hierarchy['city']['id']}", headers=headers).status_code == 200
    assert client.get("/api/v1/geographies/tree", headers=headers).status_code == 200

    forbidden = [
        client.post("/api/v1/geographies/", headers=headers, json={"name": "Nepal", "level": "country"}),
        client.put(f"/api/v1/geographies/{hierarchy['city']['id']}", headers=headers, json={"radius_km": 5}),
        client.delete(f"/api/v1/geographies/{hierarchy['city']['id']}", headers=headers),
    ]
    assert [r.status_code for r in forbidden] == [403, 403, 403]


def test_requires_authentication(client):
    assert client.get("/api/v1/geographies/").status_code == 401
    assert client.get("/api/v1/geographies/tree").status_code == 401


def test_level_and_parent_rules_are_enforced(client, hierarchy, admin_user, auth_headers):
    headers = auth_headers(admin_user)
    country_id, province_id = hierarchy["country"]["id"], hierarchy["province"]["id"]
    city_area = {"latitude": 30.0, "longitude": 70.0, "radius_km": 10}

    # A city must sit under a province, not directly under a country.
    wrong_parent = client.post(
        "/api/v1/geographies/", headers=headers,
        json={"name": "Multan", "level": "city", "parent_id": country_id, **city_area},
    )
    assert wrong_parent.status_code == 400

    missing_parent = client.post(
        "/api/v1/geographies/", headers=headers,
        json={"name": "Multan", "level": "city", "parent_id": 9999, **city_area},
    )
    assert missing_parent.status_code == 404

    # Schema-level rules -> 422.
    no_parent = client.post("/api/v1/geographies/", headers=headers, json={"name": "Sindh", "level": "province"})
    country_with_parent = client.post(
        "/api/v1/geographies/", headers=headers, json={"name": "Nepal", "level": "country", "parent_id": country_id},
    )
    city_without_area = client.post(
        "/api/v1/geographies/", headers=headers,
        json={"name": "Multan", "level": "city", "parent_id": province_id},
    )
    assert no_parent.status_code == country_with_parent.status_code == city_without_area.status_code == 422


def test_coordinate_and_bbox_validation(client, hierarchy, admin_user, auth_headers):
    headers = auth_headers(admin_user)
    base = {"name": "Multan", "level": "city", "parent_id": hierarchy["province"]["id"]}
    bad_latitude = client.post("/api/v1/geographies/", headers=headers, json={**base, "latitude": 95, "longitude": 70, "radius_km": 10})
    bad_radius = client.post("/api/v1/geographies/", headers=headers, json={**base, "latitude": 30, "longitude": 70, "radius_km": 0})
    bad_bbox = client.post(
        "/api/v1/geographies/", headers=headers,
        json={**base, "latitude": 30, "longitude": 70, "radius_km": 10, "bbox": [30, 70, 29, 71]},
    )
    assert bad_latitude.status_code == bad_radius.status_code == bad_bbox.status_code == 422


def test_duplicate_name_in_same_parent_conflicts_but_slug_stays_unique(client, hierarchy, admin_user, auth_headers):
    headers = auth_headers(admin_user)
    duplicate = client.post(
        "/api/v1/geographies/", headers=headers,
        json={
            "name": "Lahore", "level": "city", "parent_id": hierarchy["province"]["id"],
            "latitude": 31.5, "longitude": 74.3, "radius_km": 5,
        },
    )
    assert duplicate.status_code == 409

    # Same name under a different province is allowed and gets a distinct slug.
    sindh = client.post(
        "/api/v1/geographies/", headers=headers,
        json={"name": "Sindh", "level": "province", "parent_id": hierarchy["country"]["id"]},
    ).json()
    other = client.post(
        "/api/v1/geographies/", headers=headers,
        json={
            "name": "Lahore", "level": "city", "parent_id": sindh["id"],
            "latitude": 25.0, "longitude": 68.0, "radius_km": 5,
        },
    )
    assert other.status_code == 201
    assert other.json()["slug"] == "lahore-2"


def test_list_filters_search_and_pagination(client, hierarchy, sales_user, auth_headers):
    headers = auth_headers(sales_user)

    cities = client.get("/api/v1/geographies/?level=city", headers=headers).json()
    assert [g["name"] for g in cities["data"]] == ["Lahore"]

    children = client.get(f"/api/v1/geographies/?parent_id={hierarchy['country']['id']}", headers=headers).json()
    assert [g["name"] for g in children["data"]] == ["Punjab"]

    assert client.get("/api/v1/geographies/?search=lah", headers=headers).json()["count"] == 1

    page = client.get("/api/v1/geographies/?limit=2&page=2", headers=headers).json()
    assert page["count"] == 3 and len(page["data"]) == 1


def test_tree_nests_children_under_parents(client, hierarchy, sales_user, auth_headers):
    tree = client.get("/api/v1/geographies/tree", headers=auth_headers(sales_user)).json()
    assert len(tree) == 1
    assert tree[0]["name"] == "Pakistan"
    assert tree[0]["children"][0]["name"] == "Punjab"
    assert tree[0]["children"][0]["children"][0]["name"] == "Lahore"
    assert tree[0]["children"][0]["children"][0]["children"] == []


def test_update_keeps_slug_and_protects_city_area(client, hierarchy, admin_user, auth_headers):
    headers = auth_headers(admin_user)
    city_id = hierarchy["city"]["id"]

    renamed = client.put(f"/api/v1/geographies/{city_id}", headers=headers, json={"name": "Lahore City", "radius_km": 25})
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Lahore City"
    assert renamed.json()["radius_km"] == 25
    assert renamed.json()["slug"] == "lahore"

    # Explicitly clearing a city's coordinates would leave it unsearchable.
    cleared = client.put(f"/api/v1/geographies/{city_id}", headers=headers, json={"latitude": None})
    assert cleared.status_code == 400

    self_parent = client.put(f"/api/v1/geographies/{city_id}", headers=headers, json={"parent_id": city_id})
    assert self_parent.status_code == 400


def test_delete_blocked_while_children_exist(client, hierarchy, admin_user, auth_headers):
    headers = auth_headers(admin_user)
    assert client.delete(f"/api/v1/geographies/{hierarchy['province']['id']}", headers=headers).status_code == 409
    assert client.delete(f"/api/v1/geographies/{hierarchy['city']['id']}", headers=headers).status_code == 204
    assert client.delete(f"/api/v1/geographies/{hierarchy['province']['id']}", headers=headers).status_code == 204
    assert client.get(f"/api/v1/geographies/{hierarchy['city']['id']}", headers=headers).status_code == 404
