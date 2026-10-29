"""Sanity check: the packaged/served frontend is reachable through FastAPI.

    python tools/check_frontend.py [--data-dir .tmp/appdata]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

from app import create_app  # noqa: E402
from app.config import load_settings  # noqa: E402

ASSET_RE = re.compile(r"/assets/[A-Za-z0-9_.\-]+")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=REPO / ".tmp" / "appdata")
    args = parser.parse_args(argv)

    dist = REPO / "web" / "dist" / "index.html"
    if not dist.is_file():
        print("web/dist 不存在，先执行 web 的 npm run build")
        return 1

    settings = load_settings(args.data_dir)
    with TestClient(create_app(settings)) as client:
        index = client.get("/")
        assert index.status_code == 200, index.status_code
        assert '<div id="app">' in index.text, "index.html 内容不对"
        print(f"GET /            -> {index.status_code} ({len(index.text)} bytes)")

        assets = sorted(set(ASSET_RE.findall(index.text)))
        assert assets, "index.html 没有引用任何 /assets 资源"
        for asset in assets:
            response = client.get(asset)
            assert response.status_code == 200, f"{asset} -> {response.status_code}"
            print(f"GET {asset:<34} -> {response.status_code} ({len(response.content)} bytes)")

        for path in ("/items/I0001", "/about", "/login"):
            response = client.get(path)
            assert response.status_code == 200 and '<div id="app">' in response.text
            print(f"SPA {path:<16} -> {response.status_code}")

        health = client.get("/api/v1/health").json()
        print(f"health           -> {health['status']} items={health['items']} "
              f"model={health['model_version']}")
    print("前端静态资源与 SPA 回退检查通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
