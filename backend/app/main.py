"""``python -m app.main`` starts the API in browser development mode."""

from __future__ import annotations

import os

import uvicorn

from . import create_app


def main() -> int:
    host = os.environ.get("APP_HOST", "127.0.0.1")
    port = int(os.environ.get("APP_PORT", "8000"))
    uvicorn.run(create_app(), host=host, port=port, workers=1, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
