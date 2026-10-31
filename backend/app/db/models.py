"""SQLAlchemy models: catalog, users and behaviour events."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String, Text
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


class Post(Base):
    """买家安利内容：图文或短视频（短视频只有封面 + 时长，播放依赖本地文件）。"""

    __tablename__ = "posts"

    post_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    author_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), nullable=False,
                                           index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    media_type: Mapped[str] = mapped_column(String(12), nullable=False, default="image")
    video_seconds: Mapped[int] = mapped_column(default=0)
    product_id: Mapped[str] = mapped_column(ForeignKey("items.item_id"), nullable=False,
                                            index=True)
    likes: Mapped[int] = mapped_column(default=0)
    tags: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow,
                                                 index=True)


class Search(Base):
    """用户搜索词（关键词偏好的来源）。"""

    __tablename__ = "searches"

    search_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), nullable=False,
                                         index=True)
    keyword: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow,
                                                 index=True)


class Dwell(Base):
    """用户在安利帖子上的停留时长（秒）。"""

    __tablename__ = "dwells"

    dwell_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), nullable=False,
                                         index=True)
    post_id: Mapped[str] = mapped_column(ForeignKey("posts.post_id"), nullable=False,
                                         index=True)
    seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow,
                                                 index=True)

class CartItem(Base):
    """服务端购物车：同一用户同一商品只有一行，重复加入累加数量。"""

    __tablename__ = "cart_items"

    cart_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), nullable=False,
                                         index=True)
    item_id: Mapped[str] = mapped_column(ForeignKey("items.item_id"), nullable=False)
    qty: Mapped[int] = mapped_column(default=1)
    checked: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)


class Favorite(Base):
    __tablename__ = "favorites"

    favorite_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), nullable=False,
                                         index=True)
    item_id: Mapped[str] = mapped_column(ForeignKey("items.item_id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)


class Address(Base):
    __tablename__ = "addresses"

    address_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), nullable=False,
                                         index=True)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    phone: Mapped[str] = mapped_column(String(30), nullable=False)
    region: Mapped[str] = mapped_column(String(160), nullable=False)
    detail: Mapped[str] = mapped_column(String(200), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)


class Order(Base):
    __tablename__ = "orders"

    order_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), nullable=False,
                                         index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending_payment")
    payment: Mapped[str] = mapped_column(String(30), nullable=False, default="")
    total: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    items_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    address_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow,
                                                 index=True)
