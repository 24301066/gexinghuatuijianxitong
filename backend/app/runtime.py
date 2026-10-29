"""Runtime wiring: database, seed data and the recommendation engine cache."""

from __future__ import annotations

import json
import threading

from sqlalchemy import func, select

from .config import Settings
from .db.models import Event, Item, User
from .db.seed import ensure_seeded
from .db.session import init_db, make_engine, make_session_factory
from .rec.engine import Recommender

DATASET_MARKER = "dataset.json"


class Runtime:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.engine = make_engine(settings.db_url)
        init_db(self.engine)
        self.session_factory = make_session_factory(self.engine)
        self.recommender = Recommender(settings.rec, settings.model_version())
        self._dirty = True
        self._lock = threading.RLock()
        self.seed_stats: dict | None = None

    # ------------------------------------------------------------- data

    def _marker_path(self):
        return self.settings.data_dir / DATASET_MARKER

    def seed_if_empty(self) -> dict | None:
        """Seed only when empty; the dataset marker survives restarts."""
        with self.session_factory() as session:
            self.seed_stats = ensure_seeded(session, self.settings.rec)
        marker = self._marker_path()
        if self.seed_stats:
            marker.write_text(json.dumps(self.seed_stats, ensure_ascii=False, indent=2),
                              encoding="utf-8")
        elif marker.exists():
            try:
                self.seed_stats = json.loads(marker.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                self.seed_stats = None
        return self.seed_stats

    def load_rows(self) -> tuple[list[dict], list[dict]]:
        with self.session_factory() as session:
            items = [
                {"item_id": row.item_id, "title": row.title, "category": row.category,
                 "price": float(row.price), "tags": row.tags or "",
                 "description": row.description or ""}
                for row in session.scalars(select(Item))
            ]
            events = [
                {"user_id": row.user_id, "item_id": row.item_id, "type": row.type,
                 "rating": row.rating, "event_time": row.event_time}
                for row in session.scalars(select(Event))
            ]
        events.sort(key=lambda event: event["event_time"])
        return items, events

    # ---------------------------------------------------------- engine

    def mark_dirty(self) -> None:
        self._dirty = True

    def refresh(self, force: bool = False) -> Recommender:
        with self._lock:
            if self._dirty or force:
                items, events = self.load_rows()
                self.recommender.fit(items, events)
                self._dirty = False
            return self.recommender

    # ----------------------------------------------------------- stats

    def counts(self) -> dict:
        with self.session_factory() as session:
            return {
                "items": session.scalar(select(func.count()).select_from(Item)) or 0,
                "users": session.scalar(select(func.count()).select_from(User)) or 0,
                "events": session.scalar(select(func.count()).select_from(Event)) or 0,
                "purchases": session.scalar(
                    select(func.count()).select_from(Event).where(Event.type == "purchase")) or 0,
            }
