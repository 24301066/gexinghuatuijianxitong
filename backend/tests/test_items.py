"""Catalog endpoints: pagination, filtering, detail."""

from __future__ import annotations


def test_list_items_paginates(client):
    response = client.get("/api/v1/items?page=1&size=5")
    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["size"] == 5
    assert body["total"] == 30
    assert len(body["items"]) == 5
    assert set(body["items"][0]) == {"item_id", "title", "category", "price", "tags",
                                     "description"}
    assert isinstance(body["items"][0]["tags"], list)


def test_category_filter_and_empty_category(client):
    first = client.get("/api/v1/items?size=1").json()["items"][0]
    filtered = client.get(f"/api/v1/items?category={first['category']}&size=50").json()
    assert filtered["total"] >= 1
    assert all(item["category"] == first["category"] for item in filtered["items"])

    empty = client.get("/api/v1/items?category=不存在的类目").json()
    assert empty["total"] == 0
    assert empty["items"] == []


def test_item_detail(client):
    item_id = client.get("/api/v1/items?size=1").json()["items"][0]["item_id"]
    response = client.get(f"/api/v1/items/{item_id}")
    assert response.status_code == 200
    assert response.json()["item_id"] == item_id
    assert client.get("/api/v1/items/nope").status_code == 404


def test_health_reports_seed_state(client):
    body = client.get("/api/v1/health").json()
    assert body["status"] == "ok"
    assert body["items"] == 30
    assert body["demo_data"] is True
    assert body["model_version"].startswith("rec-")


def test_second_start_keeps_seeded_data(tmp_path):
    from fastapi.testclient import TestClient

    from app import create_app

    from .conftest import make_settings

    settings = make_settings(tmp_path)
    with TestClient(create_app(settings)) as first_client:
        first = first_client.get("/api/v1/health").json()
    with TestClient(create_app(settings)) as second_client:
        second = second_client.get("/api/v1/health").json()

    assert second["events"] == first["events"]
    assert second["items"] == first["items"]
    assert second["demo_data"] is True
    assert (tmp_path / "dataset.json").is_file()
