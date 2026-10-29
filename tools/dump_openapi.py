"""Dump the OpenAPI document so the API contract is reviewable in git.

    python tools/dump_openapi.py            # writes docs/openapi.json
    python tools/dump_openapi.py --check    # fails when the file is out of date
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

from app import create_app  # noqa: E402
from app.config import Settings  # noqa: E402
from app.db.session import sqlite_url  # noqa: E402

TARGET = REPO / "docs" / "openapi.json"


def build_document() -> dict:
    """Build OpenAPI against a throwaway data dir so the repo is untouched."""
    scratch = Path(tempfile.mkdtemp(prefix="openapi-", dir=str(REPO / ".tmp")))
    settings = Settings(
        data_dir=scratch,
        rec_config_path=REPO / "backend" / "config" / "rec.yaml",
        secret="openapi-dump",
        db_url=sqlite_url(scratch / "openapi.db"),
        rec=__import__("app.config", fromlist=["load_rec_config"]).load_rec_config(
            REPO / "backend" / "config" / "rec.yaml"),
        web_dist=scratch / "webdist",
    )
    app = create_app(settings)
    document = app.openapi()
    app.state.runtime.engine.dispose()
    return document


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="导出 OpenAPI 契约")
    parser.add_argument("--check", action="store_true", help="只校验，不写文件")
    args = parser.parse_args(argv)

    document = build_document()
    text = json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"

    if args.check:
        if not TARGET.is_file():
            print(f"缺少 {TARGET}，先运行 python tools/dump_openapi.py")
            return 1
        current = TARGET.read_text(encoding="utf-8")
        if current != text:
            print(f"{TARGET} 与代码不一致，重新运行 python tools/dump_openapi.py")
            return 1
        print(f"{TARGET.name} 与代码一致")
        return 0

    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(text, encoding="utf-8", newline="\n")
    paths = sorted(document.get("paths", {}))
    print(f"已写入 {TARGET}（{len(paths)} 个路径）")
    for path in paths:
        print(f"  {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
