"""Seed the demo dataset. Run as ``python -m app.db.seed`` or via tools/seed_demo.py."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import load_settings
from ..core.security import hash_password
from . import demo_data
from .models import Event, Item, User, utcnow
from .session import init_db, make_engine, make_session_factory


def seed_demo(session: Session, *, seed: int | None = None, users: int = 200,
              items: int = 400, events: int = 12000) -> dict:
    config_seed = seed if seed is not None else 20261029
    rng = __import__("numpy").random.default_rng(config_seed)
    now = utcnow()

    item_rows = demo_data.build_items(rng, items)
    password_hash = hash_password(demo_data.DEMO_PASSWORD)
    user_rows = demo_data.build_users(rng, users, password_hash, now)
    event_rows = demo_data.build_events(rng, user_rows, item_rows, events, now)

    session.add_all(Item(**row) for row in item_rows)
    session.add_all(User(**row) for row in user_rows)
    session.flush()
    session.add_all(Event(**row) for row in event_rows)
    session.commit()

    return {
        "items": len(item_rows),
        "users": len(user_rows),
        "events": len(event_rows),
        "fingerprint": demo_data.dataset_fingerprint(item_rows, user_rows, event_rows),
        "generated_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(
            timespec="seconds"),
        "demo": True,
    }


def ensure_seeded(session: Session, rec_config: dict) -> dict | None:
    """Seed only when the catalog is empty; never touches existing data."""
    existing = session.scalar(select(func.count()).select_from(Item)) or 0
    if existing:
        return None
    demo = (rec_config.get("data") or {}).get("demo") or {}
    return seed_demo(
        session,
        seed=int(rec_config.get("seed", 20261029)),
        users=int(demo.get("users", 200)),
        items=int(demo.get("items", 400)),
        events=int(demo.get("events", 12000)),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成/检查演示数据集")
    parser.add_argument("--data-dir", type=Path, default=None)
    parser.add_argument("--force", action="store_true", help="清空现有数据后重新生成")
    parser.add_argument("--users", type=int, default=None)
    parser.add_argument("--items", type=int, default=None)
    parser.add_argument("--events", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args(argv)

    settings = load_settings(args.data_dir)
    engine = make_engine(settings.db_url)
    init_db(engine)
    factory = make_session_factory(engine)

    demo = (settings.rec.get("data") or {}).get("demo") or {}
    with factory() as session:
        if args.force:
            session.query(Event).delete()
            session.query(Item).delete()
            session.query(User).delete()
            session.commit()
        stats = seed_demo(
            session,
            seed=args.seed if args.seed is not None else int(settings.rec.get("seed", 20261029)),
            users=args.users or int(demo.get("users", 200)),
            items=args.items or int(demo.get("items", 400)),
            events=args.events or int(demo.get("events", 12000)),
        )
    print(f"seeded items={stats['items']} users={stats['users']} events={stats['events']} "
          f"fingerprint={stats['fingerprint']}")
    print(f"database: {settings.db_path}")
    print(f"demo accounts: admin/{demo_data.DEMO_PASSWORD}, demo/{demo_data.DEMO_PASSWORD}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
