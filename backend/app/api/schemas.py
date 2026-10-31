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


class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=20, pattern=r"^[A-Za-z0-9_]+$")
    password: str = Field(min_length=6, max_length=64)


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
    cover_url: str = ""


class ItemPageOut(BaseModel):
    items: list[ItemOut]
    total: int
    page: int
    size: int


class EventIn(BaseModel):
    type: str = Field(pattern="^(view|cart|purchase|rating|search|post_dwell)$")
    item_id: str | None = Field(default=None, max_length=40)
    rating: float | None = Field(default=None, ge=1, le=5)
    keyword: str | None = Field(default=None, max_length=120)
    post_id: str | None = Field(default=None, max_length=40)
    seconds: float | None = Field(default=None, ge=0, le=3600)


class EventOut(BaseModel):
    event_id: int
    item_id: str | None = None
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
    cover_url: str = ""


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


class PostOut(BaseModel):
    post_id: str
    title: str
    body: str
    author_id: str
    author_name: str
    media_type: str
    video_seconds: int
    has_video: bool = False
    likes: int
    tags: list[str]
    cover_url: str
    video_url: str | None = None
    product: ItemOut | None = None
    created_at: datetime


class PostPageOut(BaseModel):
    posts: list[PostOut]
    total: int
    page: int
    size: int


class AuthorOut(BaseModel):
    user_id: str
    username: str
    role: str
    post_count: int
    total_likes: int
    categories: list[str]
    posts: list[PostOut]


class FeedOut(BaseModel):
    hero: PostOut | None = None
    posts: list[PostOut]
    items: list[RecommendationItem]


class SearchOut(BaseModel):
    query: str
    items: list[ItemOut]
    posts: list[PostOut]
    recommended: list[RecommendationItem]


class SearchHitOut(BaseModel):
    keyword: str
    created_at: datetime


class DwellHitOut(BaseModel):
    post_id: str
    title: str
    seconds: float
    cover_url: str
    created_at: datetime


class InsightsOut(BaseModel):
    user_id: str
    categories: dict[str, float]
    avg_price: float
    activity_level: float
    recent_searches: list[SearchHitOut]
    recent_dwells: list[DwellHitOut]
    liked_items: list[RecommendationItem]


class HealthOut(BaseModel):
    status: str
    version: str
    model_version: str
    items: int
    users: int
    events: int
    posts: int = 0
    demo_data: bool


class AdminMetricsOut(BaseModel):
    items: int
    users: int
    events: int
    posts: int = 0
    purchases: int
    model_version: str
    fitted_at: datetime | None
    top_categories: list[dict]


class RebuildOut(BaseModel):
    rebuilt: bool
    model_version: str
    events: int

class CartIn(BaseModel):
    item_id: str = Field(min_length=1, max_length=40)
    qty: int = Field(default=1, ge=1, le=99)


class CartPatch(BaseModel):
    qty: int | None = Field(default=None, ge=1, le=99)
    checked: bool | None = None


class CartRowOut(BaseModel):
    item_id: str
    title: str
    price: float
    cover_url: str
    category: str
    qty: int
    checked: bool


class FavoriteRowOut(BaseModel):
    item_id: str
    title: str
    price: float
    cover_url: str
    category: str


class AddressIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    phone: str = Field(min_length=5, max_length=30)
    region: str = Field(min_length=1, max_length=160)
    detail: str = Field(min_length=1, max_length=200)
    is_default: bool = False


class AddressOut(BaseModel):
    id: str
    name: str
    phone: str
    region: str
    detail: str
    is_default: bool


class OrderIn(BaseModel):
    address_id: str = Field(min_length=1, max_length=40)
    payment: str = Field(default="微信支付", max_length=30)


class OrderOut(BaseModel):
    id: str
    status: str
    payment: str
    total: float
    items: list[CartRowOut]
    address: AddressOut | None = None
    created_at: datetime

class SmsSendIn(BaseModel):
    phone: str = Field(pattern=r"^1[3-9]\d{9}$")
    purpose: str = Field(default="register", pattern="^(register|login|bind)$")


class SmsSendOut(BaseModel):
    ttl: int
    dev_code: str | None = None
    message: str = "验证码已发送"


class PhoneRegisterIn(BaseModel):
    phone: str = Field(pattern=r"^1[3-9]\d{9}$")
    code: str = Field(min_length=4, max_length=8)
    username: str = Field(min_length=3, max_length=20, pattern=r"^[A-Za-z0-9_]+$")
    password: str = Field(min_length=6, max_length=64)


class PhoneLoginIn(BaseModel):
    phone: str = Field(pattern=r"^1[3-9]\d{9}$")
    code: str = Field(min_length=4, max_length=8)


class OAuthIn(BaseModel):
    provider: str = Field(pattern="^(wechat|qq)$")


class OAuthOut(BaseModel):
    provider: str
    bind_token: str
    nickname: str
    needs_phone: bool = True


class BindPhoneIn(BaseModel):
    bind_token: str = Field(min_length=10)
    phone: str = Field(pattern=r"^1[3-9]\d{9}$")
    code: str = Field(min_length=4, max_length=8)
    username: str | None = Field(default=None, min_length=3, max_length=20,
                                 pattern=r"^[A-Za-z0-9_]+$")

class MerchantOut(BaseModel):
    merchant_id: str
    name: str
    category: str
    description: str
    rating: float
    followers: int
    item_count: int = 0
    cover_url: str = ""


class ReviewOut(BaseModel):
    review_id: int
    user_name: str
    rating: int
    content: str
    created_at: datetime


class ReviewSummaryOut(BaseModel):
    item_id: str
    average: float
    count: int
    reviews: list[ReviewOut]


class ItemDetailOut(BaseModel):
    item: ItemOut
    merchant: MerchantOut | None = None
    rating: float
    review_count: int
    reviews: list[ReviewOut]


class ShopOut(BaseModel):
    merchant: MerchantOut
    items: list[ItemOut]
