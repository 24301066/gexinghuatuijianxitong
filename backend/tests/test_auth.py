"""Auth: login, 401 vs 403, admin-only endpoints."""

from __future__ import annotations


def test_login_returns_token_and_user(client):
    response = client.post("/api/v1/auth/login",
                           json={"username": "demo", "password": "demo1234"})
    assert response.status_code == 200
    body = response.json()
    assert body["token"]
    assert body["expires_in"] == 12 * 3600
    assert body["user"]["username"] == "demo"
    assert body["user"]["role"] == "user"


def test_wrong_password_is_401(client):
    response = client.post("/api/v1/auth/login",
                           json={"username": "demo", "password": "nope"})
    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


def test_unknown_user_is_401(client):
    response = client.post("/api/v1/auth/login",
                           json={"username": "ghost", "password": "demo1234"})
    assert response.status_code == 401


def test_recommendations_require_token(client):
    response = client.get("/api/v1/recommendations")
    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


def test_tampered_token_is_401(client):
    response = client.get("/api/v1/recommendations",
                          headers={"Authorization": "Bearer not.a.token"})
    assert response.status_code == 401


def test_normal_user_cannot_reach_admin(client, auth_headers):
    response = client.get("/api/v1/admin/metrics", headers=auth_headers)
    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"


def test_admin_can_reach_admin(client, admin_headers):
    response = client.get("/api/v1/admin/metrics", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["items"] > 0
    assert body["users"] > 0
    assert body["events"] > 0
    assert body["top_categories"]
