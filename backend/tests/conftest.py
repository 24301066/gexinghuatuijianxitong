"""Shared test fixtures: an isolated app instance with a small demo dataset."""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app import create_app  # noqa: E402
from app.config import Settings, load_rec_config  # noqa: E402
from app.db.session import sqlite_url  # noqa: E402

REC_CONFIG_PATH = BACKEND / "config" / "rec.yaml"


def make_settings(data_dir: Path, web_dist: Path | None = None) -> Settings:
    rec = copy.deepcopy(load_rec_config(REC_CONFIG_PATH))
    rec["data"]["demo"] = {"users": 12, "items": 30, "events": 240}
    rec["eval"] = {"cutoffs": [3, 5], "split_ratio": 0.8,
                   "strategies": ["popular", "hybrid"]}
    return Settings(
        data_dir=data_dir,
        rec_config_path=REC_CONFIG_PATH,
        env="test",
        secret="test-secret",
        db_url=sqlite_url(data_dir / "app.db"),
        rec=rec,
        web_dist=web_dist or (data_dir / "webdist"),
    )


@pytest.fixture()
def settings(tmp_path: Path) -> Settings:
    return make_settings(tmp_path)


@pytest.fixture()
def app(settings: Settings):
    return create_app(settings)


@pytest.fixture()
def client(app) -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post("/api/v1/auth/login",
                           json={"username": "demo", "password": "demo1234"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}


@pytest.fixture()
def admin_headers(client: TestClient) -> dict[str, str]:
    response = client.post("/api/v1/auth/login",
                           json={"username": "admin", "password": "demo1234"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}
