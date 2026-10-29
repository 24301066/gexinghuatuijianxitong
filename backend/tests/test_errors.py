"""Error envelope + request id contract."""

from __future__ import annotations


def test_unknown_item_returns_404_with_request_id(client):
    response = client.get("/api/v1/items/nope")
    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "not_found"
    assert body["request_id"]
    assert response.headers["X-Request-ID"] == body["request_id"]


def test_size_out_of_range_returns_422(client, auth_headers):
    response = client.get("/api/v1/recommendations?size=500", headers=auth_headers)
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    assert "size" in body["message"]
    assert body["request_id"] == response.headers["X-Request-ID"]


def test_custom_request_id_is_echoed(client):
    response = client.get("/api/v1/health", headers={"X-Request-ID": "trace-123"})
    assert response.headers["X-Request-ID"] == "trace-123"


def test_unknown_api_route_is_json_404(client):
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"
