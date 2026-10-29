"""Thin CLI wrapper so the dataset can be (re)generated from the repo root."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.db.seed import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
