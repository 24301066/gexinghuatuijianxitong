"""Engine/session helpers."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base


def make_engine(db_url: str) -> Engine:
    connect_args: dict = {}
    if db_url.startswith("sqlite"):
        # 30s busy timeout: antivirus or a second handle can briefly lock the file
        # right after it is created (first run), which would otherwise surface as
        # "database is locked" during seeding.
        connect_args = {"check_same_thread": False, "timeout": 30}
    return create_engine(db_url, connect_args=connect_args, future=True)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def init_db(engine: Engine) -> None:
    Base.metadata.create_all(engine)
    _ensure_user_columns(engine)


def _ensure_user_columns(engine: Engine) -> None:
    """SQLite 的 create_all 不会给已有表加列，这里做一次轻量迁移。"""
    wanted = {
        "phone": "VARCHAR(20)",
        "phone_verified": "BOOLEAN DEFAULT 0",
        "provider": "VARCHAR(20) DEFAULT 'password'",
    }
    with engine.begin() as conn:
        existing = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(users)")}
        if not existing:
            return
        for column, ddl in wanted.items():
            if column not in existing:
                conn.exec_driver_sql(f"ALTER TABLE users ADD COLUMN {column} {ddl}")


def sqlite_url(path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{path.as_posix()}"
