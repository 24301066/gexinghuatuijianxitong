"""Registration: new account creation, duplicate names and validation."""

from __future__ import annotations


def test_register_creates_user_and_returns_token(client):
    response = client.post("/api/v1/auth/register",
                           json={"username": "new_buyer", "password": "secret123"})
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["token"]
    assert body["user"]["username"] == "new_buyer"
    assert body["user"]["role"] == "user"

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {body['token']}"})
    assert me.status_code == 200
    assert me.json()["username"] == "new_buyer"


def test_register_rejects_duplicate_username(client):
    first = client.post("/api/v1/auth/register",
                        json={"username": "twin", "password": "secret123"})
    assert first.status_code == 201
    second = client.post("/api/v1/auth/register",
                         json={"username": "twin", "password": "secret123"})
    assert second.status_code == 409
    assert "占用" in second.json()["message"]


def test_register_validates_username_and_password(client):
    short = client.post("/api/v1/auth/register", json={"username": "ab", "password": "secret123"})
    assert short.status_code == 422
    weak = client.post("/api/v1/auth/register", json={"username": "abc", "password": "123"})
    assert weak.status_code == 422
    bad = client.post("/api/v1/auth/register", json={"username": "有中文", "password": "secret123"})
    assert bad.status_code == 422


def test_new_user_can_login_after_register(client):
    client.post("/api/v1/auth/register", json={"username": "login_me", "password": "pass1234"})
    login = client.post("/api/v1/auth/login",
                        json={"username": "login_me", "password": "pass1234"})
    assert login.status_code == 200
    assert login.json()["user"]["username"] == "login_me"
