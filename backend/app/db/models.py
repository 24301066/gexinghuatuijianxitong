"""SQLAlchemy models: catalog, users and behaviour events."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    """Naive UTC timestamp (SQLite stores naive datetimes)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class Item(Base):
    __tablename__ = "items"

    item_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    tags: Mapped[str] = mapped_column(Text, nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    def tag_list(self) -> list[str]:
        return [tag for tag in (self.tags or "").split(",") if tag]


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    username: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="user")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)


class Event(Base):
    __tablename__ = "events"

    event_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), nullable=False, index=True)
    item_id: Mapped[str] = mapped_column(ForeignKey("items.item_id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    event_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(120), nullable=True, unique=True)

    __table_args__ = (
        Index("ix_events_user_item_type", "user_id", "item_id", "type"),
        Index("ix_events_time", "event_time"),
    )
