"""Seed the demo dataset. Run as ``python -m app.db.seed`` or via tools/seed_demo.py."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import load_settings
from ..core.security import hash_password
from . import demo_data
from .models import Dwell, Event, Item, Post, Search, User, utcnow
from .session import init_db, make_engine, make_session_factory


def _stats(items: int, users: int, events: int, posts: int, searches: int,
           dwells: int, fingerprint: str) -> dict:
    return {
        "items": items,
        "users": users,
        "events": events,
        "posts": posts,
        "searches": searches,
        "dwells": dwells,
        "fingerprint": fingerprint,
        "generated_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(
            timespec="seconds"),
        "demo": True,
    }


def seed_demo(session: Session, *, seed: int | None = None, users: int = 200,
              items: int = 400, events: int = 12000, posts: int = 60) -> dict:
    config_seed = seed if seed is not None else 20261029
    rng = np.random.default_rng(config_seed)
    now = utcnow()

    item_rows = demo_data.build_items(rng, items)
    password_hash = hash_password(demo_data.DEMO_PASSWORD)
    user_rows = demo_data.build_users(rng, users, password_hash, now)
    event_rows = demo_data.build_events(rng, user_rows, item_rows, events, now)
    post_rows = demo_data.build_posts(rng, item_rows, user_rows, posts, now)
    search_rows = demo_data.build_searches(rng, user_rows, item_rows, 4, now)
    dwell_rows = demo_data.build_dwells(rng, user_rows, post_rows, 4, now)

    session.add_all(Item(**row) for row in item_rows)
    session.add_all(User(**row) for row in user_rows)
    session.flush()
    session.add_all(Event(**row) for row in event_rows)
    session.add_all(Post(**row) for row in post_rows)
    session.add_all(Search(**row) for row in search_rows)
    session.add_all(Dwell(**row) for row in dwell_rows)
    session.commit()

    return _stats(len(item_rows), len(user_rows), len(event_rows), len(post_rows),
                  len(search_rows), len(dwell_rows),
                  demo_data.dataset_fingerprint(item_rows, user_rows, event_rows))


def seed_content(session: Session, rec_config: dict) -> dict | None:
    """Add UGC content to a database that already has catalog + events."""
    if session.scalar(select(func.count()).select_from(Post)):
        return None
    demo = (rec_config.get("data") or {}).get("demo") or {}
    rng = np.random.default_rng(int(rec_config.get("seed", 20261029)) + 7)
    now = utcnow()

    items = [
        {"item_id": row.item_id, "title": row.title, "category": row.category,
         "price": float(row.price), "tags": row.tags or ""}
        for row in session.scalars(select(Item))
    ]
    users = [
        {"user_id": row.user_id, "role": row.role}
        for row in session.scalars(select(User))
    ]
    if not items or not users:
        return None

    post_rows = demo_data.build_posts(rng, items, users, int(demo.get("posts", 60)), now)
    search_rows = demo_data.build_searches(rng, users, items, 4, now)
    dwell_rows = demo_data.build_dwells(rng, users, post_rows, 4, now)
    session.add_all(Post(**row) for row in post_rows)
    session.add_all(Search(**row) for row in search_rows)
    session.add_all(Dwell(**row) for row in dwell_rows)
    session.commit()
    return {"posts": len(post_rows), "searches": len(search_rows),
            "dwells": len(dwell_rows)}


def ensure_seeded(session: Session, rec_config: dict) -> dict | None:
    """Seed the catalog when empty, and UGC content when the catalog already exists."""
    demo = (rec_config.get("data") or {}).get("demo") or {}
    existing = session.scalar(select(func.count()).select_from(Item)) or 0
    if existing:
        return seed_content(session, rec_config)
    return seed_demo(
        session,
        seed=int(rec_config.get("seed", 20261029)),
        users=int(demo.get("users", 200)),
        items=int(demo.get("items", 400)),
        events=int(demo.get("events", 12000)),
        posts=int(demo.get("posts", 60)),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成/检查演示数据集")
    parser.add_argument("--data-dir", type=Path, default=None)
    parser.add_argument("--force", action="store_true", help="清空现有数据后重新生成")
    parser.add_argument("--users", type=int, default=None)
    parser.add_argument("--items", type=int, default=None)
    parser.add_argument("--events", type=int, default=None)
    parser.add_argument("--posts", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args(argv)

    settings = load_settings(args.data_dir)
    engine = make_engine(settings.db_url)
    init_db(engine)
    factory = make_session_factory(engine)

    demo = (settings.rec.get("data") or {}).get("demo") or {}
    with factory() as session:
        if args.force:
            for model in (Dwell, Search, Post, Event, Item, User):
                session.query(model).delete()
            session.commit()
        stats = seed_demo(
            session,
            seed=args.seed if args.seed is not None else int(settings.rec.get("seed", 20261029)),
            users=args.users or int(demo.get("users", 200)),
            items=args.items or int(demo.get("items", 400)),
            events=args.events or int(demo.get("events", 12000)),
            posts=args.posts or int(demo.get("posts", 60)),
        )
    print(f"seeded items={stats['items']} users={stats['users']} events={stats['events']} "
          f"posts={stats['posts']} searches={stats['searches']} dwells={stats['dwells']} "
          f"fingerprint={stats['fingerprint']}")
    print(f"database: {settings.db_path}")
    print(f"demo accounts: admin/{demo_data.DEMO_PASSWORD}, demo/{demo_data.DEMO_PASSWORD}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
