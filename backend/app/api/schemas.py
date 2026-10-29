"""Pydantic schemas: these are also the source of docs/openapi.json."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ErrorOut(BaseModel):
    code: str
    message: str
    request_id: str


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)


class UserOut(BaseModel):
    user_id: str
    username: str
    role: str


class TokenOut(BaseModel):
    token: str
    expires_in: int
    user: UserOut


class ItemOut(BaseModel):
    item_id: str
    title: str
    category: str
    price: float
    tags: list[str]
    description: str


class ItemPageOut(BaseModel):
    items: list[ItemOut]
    total: int
    page: int
    size: int


class EventIn(BaseModel):
    item_id: str = Field(min_length=1, max_length=40)
    type: str = Field(pattern="^(view|cart|purchase|rating)$")
    rating: float | None = Field(default=None, ge=1, le=5)


class EventOut(BaseModel):
    event_id: int
    item_id: str
    type: str
    event_time: datetime
    duplicate: bool = False


class RecommendationItem(BaseModel):
    item_id: str
    title: str
    category: str
    price: float
    tags: str
    score: float
    rank: int
    reason: str
    sources: dict[str, float]


class RecommendationOut(BaseModel):
    request_id: str
    model_version: str
    cold_start: bool
    degraded: bool
    partial: bool
    total_candidates: int
    items: list[RecommendationItem]


class SimilarOut(BaseModel):
    item_id: str
    model_version: str
    degraded: bool
    items: list[RecommendationItem]


class ProfileOut(BaseModel):
    user_id: str
    categories: dict[str, float]
    avg_price: float
    activity_level: float
    history_size: int


class HealthOut(BaseModel):
    status: str
    version: str
    model_version: str
    items: int
    users: int
    events: int
    demo_data: bool


class AdminMetricsOut(BaseModel):
    items: int
    users: int
    events: int
    purchases: int
    model_version: str
    fitted_at: datetime | None
    top_categories: list[dict]


class RebuildOut(BaseModel):
    rebuilt: bool
    model_version: str
    events: int
