"""Runtime wiring: database, seed data and the recommendation engine cache."""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.exc import DatabaseError, OperationalError

from .config import Settings
from .db.models import Dwell, Event, Item, Post, Search, User
from .db.seed import ensure_seeded
from .db.session import init_db, make_engine, make_session_factory
from .rec.engine import Recommender

DATASET_MARKER = "dataset.json"


CORRUPTION_HINTS = ("not a database", "malformed", "disk image", "encrypted")


def _looks_corrupt(exc: DatabaseError) -> bool:
    message = f"{exc.orig if exc.orig is not None else exc}".lower()
    return any(hint in message for hint in CORRUPTION_HINTS)


def retry_sqlite(operation: Callable, attempts: int = 4, delay: float = 0.6):
    """Retry transient SQLite failures (locked / busy / disk I/O) with backoff."""
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            return operation()
        except OperationalError as exc:
            last_error = exc
            time.sleep(delay * (attempt + 1))
    raise last_error  # type: ignore[misc]


class Runtime:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.quarantined: Path | None = None
        self._preflight_db()
        self.engine = make_engine(settings.db_url)
        self.session_factory = make_session_factory(self.engine)
        self._open_database()
        self.recommender = Recommender(settings.rec, settings.model_version())
        self._dirty = True
        self._lock = threading.RLock()
        self.seed_stats: dict | None = None

    # ------------------------------------------------------------- data

    SQLITE_HEADER = b"SQLite format 3\x00"

    def _preflight_db(self) -> None:
        """Clear stale journals and move an obviously corrupt database aside."""
        if not self.settings.db_url.startswith("sqlite"):
            return
        db_path = self.settings.db_path
        if not db_path.exists() or db_path.stat().st_size == 0:
            self._clear_journals(db_path)
            return
        self._clear_journals(db_path)
        try:
            header = db_path.open("rb").read(16)
        except OSError:
            return
        if header != self.SQLITE_HEADER:
            self.quarantined = self._quarantine_db()

    @staticmethod
    def _clear_journals(db_path: Path) -> None:
        """A journal left behind by a killed process blocks the next transaction."""
        for suffix in ("-journal", "-wal", "-shm"):
            sidecar = db_path.with_name(db_path.name + suffix)
            if sidecar.exists():
                try:
                    sidecar.unlink()
                except OSError:
                    pass

    def _open_database(self) -> None:
        """Create the schema; quarantine a corrupted file discovered later."""
        try:
            retry_sqlite(lambda: init_db(self.engine))
        except DatabaseError as exc:
            if self.quarantined is not None or not _looks_corrupt(exc):
                raise
            self.engine.dispose()
            self.quarantined = self._quarantine_db()
            if self.quarantined is None:
                raise
            self.engine = make_engine(self.settings.db_url)
            self.session_factory = make_session_factory(self.engine)
            retry_sqlite(lambda: init_db(self.engine))

    def _quarantine_db(self) -> Path | None:
        db_path = self.settings.db_path
        if not db_path.exists():
            return None
        stamp = time.strftime("%Y%m%d%H%M%S")
        target = db_path.with_name(f"app.db.broken-{stamp}")
        try:
            db_path.replace(target)
            for suffix in ("-wal", "-shm"):
                sidecar = db_path.with_name(db_path.name + suffix)
                if sidecar.exists():
                    sidecar.replace(target.with_name(target.name + suffix))
            return target
        except OSError:
            return None

    def _marker_path(self):
        return self.settings.data_dir / DATASET_MARKER

    def seed_if_empty(self) -> dict | None:
        """Seed only when empty; the dataset marker survives restarts."""

        def _seed() -> dict | None:
            with self.session_factory() as session:
                return ensure_seeded(session, self.settings.rec)

        self.seed_stats = retry_sqlite(_seed)
        marker = self._marker_path()
        if self.seed_stats:
            try:
                marker.write_text(json.dumps(self.seed_stats, ensure_ascii=False, indent=2),
                                  encoding="utf-8")
            except OSError:
                pass
        elif marker.exists():
            try:
                self.seed_stats = json.loads(marker.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                self.seed_stats = None
        return self.seed_stats

    def load_rows(self) -> tuple[list[dict], list[dict], list[dict], list[dict], list[dict]]:
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
            posts = [
                {"post_id": row.post_id, "title": row.title, "body": row.body,
                 "author_id": row.author_id, "media_type": row.media_type,
                 "video_seconds": row.video_seconds, "product_id": row.product_id,
                 "likes": row.likes, "tags": row.tags or "",
                 "created_at": row.created_at}
                for row in session.scalars(select(Post))
            ]
            searches = [
                {"user_id": row.user_id, "keyword": row.keyword,
                 "created_at": row.created_at}
                for row in session.scalars(select(Search))
            ]
            dwells = [
                {"user_id": row.user_id, "post_id": row.post_id,
                 "seconds": float(row.seconds), "created_at": row.created_at}
                for row in session.scalars(select(Dwell))
            ]
        events.sort(key=lambda event: event["event_time"])
        searches.sort(key=lambda row: row["created_at"])
        dwells.sort(key=lambda row: row["created_at"])
        return items, events, posts, searches, dwells

    # ---------------------------------------------------------- engine

    def mark_dirty(self) -> None:
        self._dirty = True

    def refresh(self, force: bool = False) -> Recommender:
        with self._lock:
            if self._dirty or force:
                def _fit() -> None:
                    items, events, posts, searches, dwells = self.load_rows()
                    self.recommender.fit(items, events, posts=posts, dwells=dwells,
                                         searches=searches)

                retry_sqlite(_fit)
                self._dirty = False
            return self.recommender

    # ----------------------------------------------------------- stats

    def counts(self) -> dict:
        with self.session_factory() as session:
            return {
                "items": session.scalar(select(func.count()).select_from(Item)) or 0,
                "users": session.scalar(select(func.count()).select_from(User)) or 0,
                "events": session.scalar(select(func.count()).select_from(Event)) or 0,
                "posts": session.scalar(select(func.count()).select_from(Post)) or 0,
                "searches": session.scalar(select(func.count()).select_from(Search)) or 0,
                "purchases": session.scalar(
                    select(func.count()).select_from(Event).where(Event.type == "purchase")) or 0,
            }
