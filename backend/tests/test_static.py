"""Static hosting + SPA fallback for the packaged desktop build."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app import create_app

from .conftest import make_settings

INDEX_MARKER = "<!doctype html><title>推荐系统</title>"


def _dist(tmp_path: Path) -> Path:
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text(INDEX_MARKER, encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log('ok')", encoding="utf-8")
    (dist / "favicon.svg").write_text("<svg/>", encoding="utf-8")
    return dist


def test_root_serves_index(tmp_path):
    dist = _dist(tmp_path)
    settings = make_settings(tmp_path / "data", web_dist=dist)
    with TestClient(create_app(settings)) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert INDEX_MARKER in response.text
        assert client.get("/assets/app.js").status_code == 200
        assert client.get("/favicon.svg").status_code == 200


def test_deep_link_falls_back_to_index(tmp_path):
    dist = _dist(tmp_path)
    settings = make_settings(tmp_path / "data", web_dist=dist)
    with TestClient(create_app(settings)) as client:
        response = client.get("/items/I0001")
        assert response.status_code == 200
        assert INDEX_MARKER in response.text


def test_api_paths_are_not_swallowed_by_spa(tmp_path):
    dist = _dist(tmp_path)
    settings = make_settings(tmp_path / "data", web_dist=dist)
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/v1/nope")
        assert response.status_code == 404
        assert response.json()["code"] == "not_found"


def test_missing_frontend_returns_hint(tmp_path):
    settings = make_settings(tmp_path / "data", web_dist=tmp_path / "no-dist")
    with TestClient(create_app(settings)) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["hint"]
