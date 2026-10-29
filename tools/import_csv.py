"""Import catalog/events from CSV (all-or-nothing).

    python tools/import_csv.py items data/items.csv --data-dir .data
    python tools/import_csv.py events data/events.csv --data-dir .data
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.config import load_settings  # noqa: E402
from app.db.importer import CsvImportError, import_file  # noqa: E402
from app.db.session import init_db, make_engine, make_session_factory  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="从 CSV 导入商品或行为")
    parser.add_argument("kind", choices=["items", "events"])
    parser.add_argument("csv", type=Path)
    parser.add_argument("--data-dir", type=Path, default=None)
    args = parser.parse_args(argv)

    settings = load_settings(args.data_dir)
    engine = make_engine(settings.db_url)
    init_db(engine)
    factory = make_session_factory(engine)

    with factory() as session:
        try:
            result = import_file(session, args.csv, args.kind)
        except CsvImportError as exc:
            print(f"导入失败：{exc}")
            for error in exc.errors:
                print(f"  第 {error['line']} 行 [{error['field']}] {error['message']}")
            return 1
        session.commit()
    print(f"导入完成：{result}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
