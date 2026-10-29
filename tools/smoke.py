"""End-to-end smoke test: seed -> login -> recommend -> report event -> recommend again.

    python tools/smoke.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

from app import create_app  # noqa: E402
from app.config import Settings, load_rec_config  # noqa: E402
from app.db.session import sqlite_url  # noqa: E402

STEPS: list[str] = []


def step(name: str) -> None:
    STEPS.append(name)
    print(f"[{len(STEPS)}] {name}")


def main() -> int:
    workdir = Path(tempfile.mkdtemp(prefix="smoke-", dir=str(REPO / ".tmp")))
    rec = load_rec_config(REPO / "backend" / "config" / "rec.yaml")
    rec["data"]["demo"] = {"users": 20, "items": 40, "events": 500}
    settings = Settings(
        data_dir=workdir,
        rec_config_path=REPO / "backend" / "config" / "rec.yaml",
        secret="smoke-secret",
        db_url=sqlite_url(workdir / "app.db"),
        rec=rec,
        web_dist=workdir / "webdist",
    )

    with TestClient(create_app(settings)) as client:
        step("种子数据 + 引擎拟合")
        health = client.get("/api/v1/health").json()
        assert health["status"] == "ok", health
        assert health["demo_data"] is True
        print(f"    health: items={health['items']} users={health['users']} "
              f"events={health['events']} model={health['model_version']}")

        step("登录 demo 账号")
        login = client.post("/api/v1/auth/login",
                            json={"username": "demo", "password": "demo1234"})
        assert login.status_code == 200, login.text
        headers = {"Authorization": f"Bearer {login.json()['token']}"}

        step("拉取推荐（size=5）")
        first = client.get("/api/v1/recommendations?size=5", headers=headers)
        assert first.status_code == 200, first.text
        body = first.json()
        assert body["items"], body
        assert all(item["reason"] for item in body["items"])
        print(f"    cold_start={body['cold_start']} items="
              f"{[item['item_id'] for item in body['items']]}")

        step("上报浏览行为")
        target = body["items"][0]["item_id"]
        event = client.post("/api/v1/events", json={"item_id": target, "type": "view"},
                            headers=headers)
        assert event.status_code == 201, event.text
        print(f"    event_id={event.json()['event_id']} duplicate={event.json()['duplicate']}")

        step("再拉一次推荐（应触发引擎刷新）")
        second = client.get("/api/v1/recommendations?size=5", headers=headers)
        assert second.status_code == 200, second.text
        assert second.json()["items"]
        print(f"    items={[item['item_id'] for item in second.json()['items']]}")

        step("商品详情相似推荐")
        similar = client.get(f"/api/v1/items/{target}/similar?size=3", headers=headers)
        assert similar.status_code == 200 and similar.json()["items"], similar.text
        print(f"    similar={[item['item_id'] for item in similar.json()['items']]}")

        step("画像与健康检查")
        profile = client.get("/api/v1/me/profile", headers=headers).json()
        assert profile["history_size"] >= 1
        print(f"    profile: activity={profile['activity_level']} "
              f"categories={list(profile['categories'])[:3]}")

    print(f"\n全部 {len(STEPS)} 步通过。临时数据目录：{workdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
