"""Recommendation endpoint contract: fields, ordering, filters, cold start."""

from __future__ import annotations

from sqlalchemy import select

from app.db.models import Event

REQUIRED_FIELDS = {"item_id", "title", "category", "price", "tags", "score", "rank",
                   "reason", "sources"}


def test_recommendation_shape_and_order(client, auth_headers):
    response = client.get("/api/v1/recommendations?size=5", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["request_id"]
    assert body["model_version"].startswith("rec-")
    assert body["degraded"] is False
    assert len(body["items"]) == 5
    for position, item in enumerate(body["items"], start=1):
        assert set(item) == REQUIRED_FIELDS
        assert item["rank"] == position
        assert item["reason"]
        assert set(item["sources"]) == {"cf", "content", "popular"}
    scores = [item["score"] for item in body["items"]]
    assert scores == sorted(scores, reverse=True)


def test_purchased_items_are_excluded(client, auth_headers):
    body = client.get("/api/v1/recommendations?size=5", headers=auth_headers).json()
    target = body["items"][0]["item_id"]
    purchase = client.post("/api/v1/events",
                           json={"item_id": target, "type": "purchase"},
                           headers=auth_headers)
    assert purchase.status_code == 201

    after = client.get("/api/v1/recommendations?size=20", headers=auth_headers).json()
    returned = {item["item_id"] for item in after["items"]}
    assert target not in returned
    assert returned


def test_partial_flag_when_candidates_run_out(client, auth_headers):
    body = client.get("/api/v1/recommendations?size=50", headers=auth_headers).json()
    assert body["partial"] is True
    assert len(body["items"]) <= 30


def test_pagination_does_not_repeat(client, auth_headers):
    first = client.get("/api/v1/recommendations?size=3&page=1", headers=auth_headers).json()
    second = client.get("/api/v1/recommendations?size=3&page=2", headers=auth_headers).json()
    first_ids = [item["item_id"] for item in first["items"]]
    second_ids = [item["item_id"] for item in second["items"]]
    assert len(first_ids) == 3
    assert not set(first_ids) & set(second_ids)
    assert second["items"][0]["rank"] == 4


def test_repeated_request_is_identical(client, auth_headers):
    first = client.get("/api/v1/recommendations?size=6", headers=auth_headers).json()
    second = client.get("/api/v1/recommendations?size=6", headers=auth_headers).json()
    assert [(item["item_id"], item["score"]) for item in first["items"]] == \
           [(item["item_id"], item["score"]) for item in second["items"]]


def test_similar_items_for_known_item(client, auth_headers):
    item_id = client.get("/api/v1/items?size=1").json()["items"][0]["item_id"]
    response = client.get(f"/api/v1/items/{item_id}/similar?size=4", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["item_id"] == item_id
    assert 0 < len(body["items"]) <= 4
    assert all(item["item_id"] != item_id for item in body["items"])
    assert client.get("/api/v1/items/nope/similar").status_code == 404


def test_profile_endpoint(client, auth_headers):
    body = client.get("/api/v1/me/profile", headers=auth_headers).json()
    assert body["user_id"] == "U0001"
    assert body["categories"]
    assert abs(sum(body["categories"].values()) - 1.0) < 0.02
    assert body["activity_level"] > 0
