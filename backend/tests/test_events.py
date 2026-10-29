"""Behaviour events: persistence, dedupe window, validation."""

from __future__ import annotations


def _event_count(client, admin_headers) -> int:
    return client.get("/api/v1/admin/metrics", headers=admin_headers).json()["events"]


def test_event_is_persisted(client, auth_headers, admin_headers):
    item_id = client.get("/api/v1/items?size=1").json()["items"][0]["item_id"]
    before = _event_count(client, admin_headers)
    response = client.post("/api/v1/events",
                           json={"item_id": item_id, "type": "view"}, headers=auth_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["duplicate"] is False
    assert body["event_id"] > 0
    assert body["event_time"]
    assert _event_count(client, admin_headers) == before + 1


def test_duplicate_event_within_window_is_ignored(client, auth_headers, admin_headers):
    item_id = client.get("/api/v1/items?size=1").json()["items"][0]["item_id"]
    first = client.post("/api/v1/events",
                        json={"item_id": item_id, "type": "cart"}, headers=auth_headers).json()
    before = _event_count(client, admin_headers)
    second = client.post("/api/v1/events",
                         json={"item_id": item_id, "type": "cart"}, headers=auth_headers).json()
    assert second["duplicate"] is True
    assert second["event_id"] == first["event_id"]
    assert _event_count(client, admin_headers) == before


def test_unknown_item_is_rejected(client, auth_headers):
    response = client.post("/api/v1/events",
                           json={"item_id": "I9999", "type": "view"}, headers=auth_headers)
    assert response.status_code == 404


def test_invalid_type_is_422(client, auth_headers):
    response = client.post("/api/v1/events",
                           json={"item_id": "I0001", "type": "like"}, headers=auth_headers)
    assert response.status_code == 422


def test_event_requires_auth(client):
    assert client.post("/api/v1/events",
                       json={"item_id": "I0001", "type": "view"}).status_code == 401


def test_rating_event_updates_profile(client, auth_headers):
    item_id = client.get("/api/v1/items?size=1").json()["items"][0]["item_id"]
    response = client.post("/api/v1/events",
                           json={"item_id": item_id, "type": "rating", "rating": 5},
                           headers=auth_headers)
    assert response.status_code == 201
    profile = client.get("/api/v1/me/profile", headers=auth_headers).json()
    assert profile["user_id"]
    assert profile["history_size"] >= 1
