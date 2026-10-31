"""HTTP routes, all under /api/v1."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
from collections import Counter
from uuid import uuid4
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import __version__
from ..core.errors import ApiError, request_id_of
from ..core.security import create_token, decode_token, hash_password, verify_password
from ..db.models import (Address, CartItem, Dwell, Event, Favorite, Item, Merchant, Order, Post, Review, Search, User, VerificationCode, utcnow)
from ..media import covers
from ..runtime import Runtime
from . import schemas
from .deps import current_user, get_db, get_runtime, require_admin

router = APIRouter(prefix="/api/v1")

DEDUPE_WINDOW_SECONDS = 30
IMAGE_TYPES = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
               "webp": "image/webp"}
VIDEO_TYPES = {"mp4": "video/mp4", "webm": "video/webm"}


def _cover_url(kind: str, media_id: str) -> str:
    return f"/api/v1/media/{kind}/{media_id}"


def _item_out(item: Item) -> schemas.ItemOut:
    return schemas.ItemOut(item_id=item.item_id, title=item.title, category=item.category,
                           price=float(item.price), tags=item.tag_list(),
                           description=item.description or "",
                           cover_url=_cover_url("product", item.item_id))


def _asset_dir(runtime: Runtime, kind: str):
    folder = "products" if kind == "product" else "posts"
    return runtime.settings.data_dir / "media" / folder


def _find_asset(runtime: Runtime, kind: str, media_id: str, types: dict[str, str]):
    folder = _asset_dir(runtime, kind)
    for extension, mime in types.items():
        candidate = folder / f"{media_id}.{extension}"
        if candidate.is_file():
            return candidate, mime
    return None, None


def _post_out(post: Post, author_name: str, item: Item | None,
              runtime: Runtime) -> schemas.PostOut:
    video_path, _ = _find_asset(runtime, "post", post.post_id, VIDEO_TYPES)
    return schemas.PostOut(
        post_id=post.post_id, title=post.title, body=post.body or "",
        author_id=post.author_id, author_name=author_name,
        media_type=post.media_type, video_seconds=post.video_seconds,
        has_video=video_path is not None, likes=post.likes,
        tags=[tag for tag in (post.tags or "").split(",") if tag],
        cover_url=_cover_url("post", post.post_id),
        video_url=(f"/api/v1/media/post/{post.post_id}/video" if video_path else None),
        product=_item_out(item) if item is not None else None,
        created_at=post.created_at,
    )


def _rec_items(rows: list[dict]) -> list[schemas.RecommendationItem]:
    return [schemas.RecommendationItem(cover_url=_cover_url("product", row["item_id"]), **row)
            for row in rows]


def _load_post(session: Session, post_id: str, runtime: Runtime) -> schemas.PostOut:
    post = session.get(Post, post_id)
    if post is None:
        raise ApiError(404, f"帖子 {post_id} 不存在")
    author = session.get(User, post.author_id)
    item = session.get(Item, post.product_id) if post.product_id else None
    return _post_out(post, author.username if author else "匿名买家", item, runtime)


@router.get("/health", response_model=schemas.HealthOut, tags=["meta"])
def health(runtime: Runtime = Depends(get_runtime)) -> schemas.HealthOut:
    counts = runtime.counts()
    engine = runtime.recommender
    return schemas.HealthOut(
        status="ok" if engine.ready else "degraded",
        version=__version__,
        model_version=engine.model_version,
        items=counts["items"],
        users=counts["users"],
        events=counts["events"],
        posts=counts.get("posts", 0),
        demo_data=bool(runtime.seed_stats),
    )


@router.post("/auth/login", response_model=schemas.TokenOut, tags=["auth"])
def login(payload: schemas.LoginIn, db: Session = Depends(get_db),
          runtime: Runtime = Depends(get_runtime)) -> schemas.TokenOut:
    user = db.scalar(select(User).where(User.username == payload.username))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise ApiError(401, "用户名或密码错误")
    token = create_token(runtime.settings.secret, {"sub": user.user_id, "role": user.role})
    return schemas.TokenOut(token=token, expires_in=12 * 3600,
                            user=schemas.UserOut(user_id=user.user_id,
                                                 username=user.username, role=user.role))


@router.post("/auth/register", response_model=schemas.TokenOut, status_code=201, tags=["auth"])
def register(payload: schemas.RegisterIn, db: Session = Depends(get_db),
             runtime: Runtime = Depends(get_runtime)) -> schemas.TokenOut:
    if db.scalar(select(User).where(User.username == payload.username)) is not None:
        raise ApiError(409, "用户名已被占用，换一个试试")
    user = User(user_id=f"U{uuid4().hex[:12]}", username=payload.username,
                password_hash=hash_password(payload.password), role="user",
                created_at=utcnow())
    db.add(user)
    db.flush()
    token = create_token(runtime.settings.secret, {"sub": user.user_id, "role": user.role})
    return schemas.TokenOut(token=token, expires_in=12 * 3600,
                            user=schemas.UserOut(user_id=user.user_id,
                                                 username=user.username, role=user.role))


@router.get("/auth/me", response_model=schemas.UserOut, tags=["auth"])
def me(user: User = Depends(current_user)) -> schemas.UserOut:
    return schemas.UserOut(user_id=user.user_id, username=user.username, role=user.role)


@router.get("/items", response_model=schemas.ItemPageOut, tags=["catalog"])
def list_items(category: str | None = None,
               page: int = Query(1, ge=1),
               size: int = Query(20, ge=1, le=50),
               db: Session = Depends(get_db)) -> schemas.ItemPageOut:
    filters = []
    if category:
        filters.append(Item.category == category)
    total = db.scalar(select(func.count()).select_from(Item).where(*filters)) or 0
    rows = db.scalars(select(Item).where(*filters).order_by(Item.item_id)
                      .offset((page - 1) * size).limit(size)).all()
    return schemas.ItemPageOut(items=[_item_out(row) for row in rows], total=total,
                               page=page, size=size)


@router.get("/items/{item_id}", response_model=schemas.ItemOut, tags=["catalog"])
def get_item(item_id: str, db: Session = Depends(get_db)) -> schemas.ItemOut:
    item = db.get(Item, item_id)
    if item is None:
        raise ApiError(404, f"商品 {item_id} 不存在")
    return _item_out(item)


@router.get("/items/{item_id}/similar", response_model=schemas.SimilarOut, tags=["recommend"])
def similar(item_id: str, size: int = Query(8, ge=1, le=50),
            db: Session = Depends(get_db), runtime: Runtime = Depends(get_runtime),
            ) -> schemas.SimilarOut:
    if db.get(Item, item_id) is None:
        raise ApiError(404, f"商品 {item_id} 不存在")
    engine = runtime.refresh()
    result = engine.similar(item_id, size)
    return schemas.SimilarOut(item_id=item_id,
                              model_version=result["model_version"],
                              degraded=result["degraded"],
                              items=_rec_items(result["items"]))


@router.get("/posts", response_model=schemas.PostPageOut, tags=["ugc"])
def list_posts(product_id: str | None = None,
               author_id: str | None = None,
               page: int = Query(1, ge=1),
               size: int = Query(12, ge=1, le=50),
               db: Session = Depends(get_db),
               runtime: Runtime = Depends(get_runtime)) -> schemas.PostPageOut:
    filters = []
    if product_id:
        filters.append(Post.product_id == product_id)
    if author_id:
        filters.append(Post.author_id == author_id)
    total = db.scalar(select(func.count()).select_from(Post).where(*filters)) or 0
    rows = db.scalars(select(Post).where(*filters).order_by(Post.created_at.desc(),
                                                            Post.post_id)
                      .offset((page - 1) * size).limit(size)).all()
    author_names = {
        user.user_id: user.username
        for user in db.scalars(select(User).where(User.user_id.in_({r.author_id for r in rows})))
    } if rows else {}
    items = {
        item.item_id: item
        for item in db.scalars(select(Item).where(Item.item_id.in_({r.product_id for r in rows})))
    } if rows else {}
    return schemas.PostPageOut(
        posts=[_post_out(row, author_names.get(row.author_id, "匿名买家"),
                         items.get(row.product_id), runtime) for row in rows],
        total=total, page=page, size=size)


@router.get("/posts/{post_id}", response_model=schemas.PostOut, tags=["ugc"])
def get_post(post_id: str, db: Session = Depends(get_db),
             runtime: Runtime = Depends(get_runtime)) -> schemas.PostOut:
    return _load_post(db, post_id, runtime)


@router.get("/authors/{author_id}", response_model=schemas.AuthorOut, tags=["ugc"])
def get_author(author_id: str, db: Session = Depends(get_db),
               runtime: Runtime = Depends(get_runtime)) -> schemas.AuthorOut:
    author = db.get(User, author_id)
    if author is None:
        raise ApiError(404, f"作者 {author_id} 不存在")
    rows = db.scalars(select(Post).where(Post.author_id == author_id)
                      .order_by(Post.created_at.desc()).limit(30)).all()
    items = {
        item.item_id: item
        for item in db.scalars(select(Item).where(
            Item.item_id.in_({row.product_id for row in rows})))
    } if rows else {}
    posts = [_post_out(row, author.username, items.get(row.product_id), runtime)
             for row in rows]
    categories = sorted({items[row.product_id].category
                         for row in rows if row.product_id in items})
    return schemas.AuthorOut(user_id=author.user_id, username=author.username,
                             role=author.role, post_count=len(rows),
                             total_likes=sum(row.likes for row in rows),
                             categories=categories, posts=posts)


@router.get("/feed", response_model=schemas.FeedOut, tags=["ugc"])
def feed(size: int = Query(8, ge=1, le=20),
         user: User = Depends(current_user),
         db: Session = Depends(get_db),
         runtime: Runtime = Depends(get_runtime)) -> schemas.FeedOut:
    rows = db.scalars(select(Post).order_by(Post.created_at.desc(), Post.post_id)
                      .limit(size + 1)).all()
    author_names = {
        candidate.user_id: candidate.username
        for candidate in db.scalars(select(User).where(
            User.user_id.in_({r.author_id for r in rows})))
    } if rows else {}
    items = {
        item.item_id: item
        for item in db.scalars(select(Item).where(Item.item_id.in_({r.product_id for r in rows})))
    } if rows else {}
    posts = [_post_out(row, author_names.get(row.author_id, "匿名买家"),
                       items.get(row.product_id), runtime) for row in rows]
    hero = posts[0] if posts else None
    try:
        result = runtime.refresh().recommend(user.user_id, size)
        recommended = _rec_items(result["items"])
    except Exception:  # noqa: BLE001 - the feed should still render without the model
        recommended = []
    return schemas.FeedOut(hero=hero, posts=posts[1:], items=recommended)


@router.get("/search", response_model=schemas.SearchOut, tags=["ugc"])
def search(q: str = Query(min_length=1, max_length=60),
           user: User = Depends(current_user),
           db: Session = Depends(get_db),
           runtime: Runtime = Depends(get_runtime)) -> schemas.SearchOut:
    keyword = q.strip()
    pattern = f"%{keyword}%"
    items = db.scalars(select(Item).where(
        Item.title.ilike(pattern) | Item.tags.ilike(pattern) | Item.category.ilike(pattern))
        .order_by(Item.item_id).limit(20)).all()
    posts = db.scalars(select(Post).where(
        Post.title.ilike(pattern) | Post.body.ilike(pattern) | Post.tags.ilike(pattern))
        .order_by(Post.created_at.desc()).limit(12)).all()
    names = {
        candidate.user_id: candidate.username
        for candidate in db.scalars(select(User).where(
            User.user_id.in_({r.author_id for r in posts})))
    } if posts else {}
    product_map = {row.item_id: row for row in items}
    for post in posts:
        if post.product_id not in product_map:
            linked = db.get(Item, post.product_id)
            if linked is not None:
                product_map[linked.item_id] = linked
    try:
        result = runtime.refresh().recommend(user.user_id, 8)
        recommended = _rec_items(result["items"])
    except Exception:  # noqa: BLE001
        recommended = []
    return schemas.SearchOut(
        query=keyword,
        items=[_item_out(row) for row in items],
        posts=[_post_out(row, names.get(row.author_id, "匿名买家"),
                         product_map.get(row.product_id), runtime) for row in posts],
        recommended=recommended)


@router.get("/media/post/{post_id}/video", tags=["ugc"])
def post_video(post_id: str, runtime: Runtime = Depends(get_runtime)):
    path, mime = _find_asset(runtime, "post", post_id, VIDEO_TYPES)
    if path is None:
        raise ApiError(404, "该帖子没有本地视频文件")
    return FileResponse(path, media_type=mime,
                        headers={"Cache-Control": "public, max-age=3600"})


@router.get("/media/{kind}/{media_id}", tags=["ugc"])
def media(kind: str, media_id: str, db: Session = Depends(get_db),
          runtime: Runtime = Depends(get_runtime)):
    if kind not in {"product", "post"}:
        raise ApiError(404, f"未知媒体类型 {kind}")
    path, mime = _find_asset(runtime, kind, media_id, IMAGE_TYPES)
    if path is not None:
        return FileResponse(path, media_type=mime,
                            headers={"Cache-Control": "public, max-age=3600"})
    if kind == "product":
        item = db.get(Item, media_id)
        if item is None:
            raise ApiError(404, f"商品 {media_id} 不存在")
        svg = covers.product_cover(item.item_id, item.title, item.category,
                                   float(item.price))
    else:
        post = db.get(Post, media_id)
        if post is None:
            raise ApiError(404, f"帖子 {media_id} 不存在")
        item = db.get(Item, post.product_id)
        theme = item.category if item is not None else "生活"
        svg = covers.post_cover(post.post_id, post.title, post.media_type,
                                post.video_seconds, theme)
    return Response(content=svg, media_type="image/svg+xml",
                    headers={"Cache-Control": "public, max-age=3600"})


@router.post("/events", response_model=schemas.EventOut, status_code=201, tags=["behaviour"])
def create_event(payload: schemas.EventIn, db: Session = Depends(get_db),
                 user: User = Depends(current_user),
                 runtime: Runtime = Depends(get_runtime)) -> schemas.EventOut:
    now = utcnow()
    bucket = int(now.timestamp() // DEDUPE_WINDOW_SECONDS)

    if payload.type == "search":
        keyword = (payload.keyword or "").strip()
        if not keyword:
            raise ApiError(422, "search 事件需要 keyword")
        key = f"{user.user_id}:search:{keyword}:{bucket}"
        existing = db.scalar(select(Search).where(Search.user_id == user.user_id,
                                                  Search.keyword == keyword,
                                                  Search.created_at >= now - timedelta(
                                                      seconds=DEDUPE_WINDOW_SECONDS)))
        if existing is not None:
            return schemas.EventOut(event_id=existing.search_id, type="search",
                                    event_time=existing.created_at, duplicate=True)
        row = Search(user_id=user.user_id, keyword=keyword, created_at=now)
        db.add(row)
        db.flush()
        runtime.mark_dirty()
        del key
        return schemas.EventOut(event_id=row.search_id, type="search",
                                event_time=row.created_at, duplicate=False)

    if payload.type == "post_dwell":
        if not payload.post_id:
            raise ApiError(422, "post_dwell 事件需要 post_id")
        post = db.get(Post, payload.post_id)
        if post is None:
            raise ApiError(404, f"帖子 {payload.post_id} 不存在")
        seconds = float(payload.seconds or 0.0)
        seconds = min(max(seconds, 1.0), 600.0)
        row = Dwell(user_id=user.user_id, post_id=post.post_id, seconds=seconds,
                    created_at=now)
        db.add(row)
        db.flush()
        runtime.mark_dirty()
        return schemas.EventOut(event_id=row.dwell_id, type="post_dwell",
                                event_time=row.created_at, duplicate=False)

    if not payload.item_id:
        raise ApiError(422, f"{payload.type} 事件需要 item_id")
    if db.get(Item, payload.item_id) is None:
        raise ApiError(404, f"商品 {payload.item_id} 不存在")

    key = f"{user.user_id}:{payload.item_id}:{payload.type}:{bucket}"
    existing = db.scalar(select(Event).where(Event.idempotency_key == key))
    if existing is not None:
        return schemas.EventOut(event_id=existing.event_id, item_id=existing.item_id,
                                type=existing.type, event_time=existing.event_time,
                                duplicate=True)

    event = Event(user_id=user.user_id, item_id=payload.item_id, type=payload.type,
                  rating=payload.rating, event_time=now, idempotency_key=key)
    db.add(event)
    db.flush()
    runtime.mark_dirty()
    return schemas.EventOut(event_id=event.event_id, item_id=event.item_id,
                            type=event.type, event_time=event.event_time, duplicate=False)


@router.get("/recommendations", response_model=schemas.RecommendationOut, tags=["recommend"])
def recommendations(request: Request,
                    size: int = Query(10, ge=1, le=50),
                    page: int = Query(1, ge=1),
                    user: User = Depends(current_user),
                    runtime: Runtime = Depends(get_runtime)) -> schemas.RecommendationOut:
    try:
        result = runtime.refresh().recommend(user.user_id, size, page)
    except Exception as exc:  # noqa: BLE001 - degrade instead of failing the page
        result = {"items": [], "cold_start": True, "partial": True, "degraded": True,
                  "model_version": runtime.settings.model_version(), "total_candidates": 0,
                  "error": str(exc)}
    return schemas.RecommendationOut(
        request_id=request_id_of(request),
        model_version=result["model_version"],
        cold_start=result["cold_start"],
        degraded=result["degraded"],
        partial=result["partial"],
        total_candidates=result.get("total_candidates", 0),
        items=_rec_items(result["items"]),
    )


@router.get("/me/profile", response_model=schemas.ProfileOut, tags=["behaviour"])
def my_profile(user: User = Depends(current_user),
               runtime: Runtime = Depends(get_runtime)) -> schemas.ProfileOut:
    profile = runtime.refresh().profile(user.user_id)
    return schemas.ProfileOut(user_id=user.user_id,
                              categories=profile["categories"],
                              avg_price=profile["avg_price"],
                              activity_level=profile["activity_level"],
                              history_size=profile["history_size"])


@router.get("/me/insights", response_model=schemas.InsightsOut, tags=["behaviour"])
def my_insights(user: User = Depends(current_user),
                db: Session = Depends(get_db),
                runtime: Runtime = Depends(get_runtime)) -> schemas.InsightsOut:
    engine = runtime.refresh()
    profile = engine.profile(user.user_id)
    searches = db.scalars(select(Search).where(Search.user_id == user.user_id)
                          .order_by(Search.created_at.desc()).limit(10)).all()
    dwell_rows = db.scalars(select(Dwell).where(Dwell.user_id == user.user_id)
                            .order_by(Dwell.created_at.desc()).limit(40)).all()
    seen: set[str] = set()
    dwells: list[schemas.DwellHitOut] = []
    for row in dwell_rows:
        if row.post_id in seen:
            continue
        seen.add(row.post_id)
        post = db.get(Post, row.post_id)
        if post is None:
            continue
        dwells.append(schemas.DwellHitOut(post_id=post.post_id, title=post.title,
                                          seconds=float(row.seconds),
                                          cover_url=_cover_url("post", post.post_id),
                                          created_at=row.created_at))
        if len(dwells) >= 10:
            break
    try:
        liked = _rec_items(engine.recommend(user.user_id, 6)["items"])
    except Exception:  # noqa: BLE001
        liked = []
    return schemas.InsightsOut(
        user_id=user.user_id, categories=profile["categories"],
        avg_price=profile["avg_price"], activity_level=profile["activity_level"],
        recent_searches=[schemas.SearchHitOut(keyword=row.keyword,
                                              created_at=row.created_at)
                         for row in searches],
        recent_dwells=dwells, liked_items=liked)


@router.get("/admin/metrics", response_model=schemas.AdminMetricsOut, tags=["admin"])
def admin_metrics(db: Session = Depends(get_db),
                  _: User = Depends(require_admin),
                  runtime: Runtime = Depends(get_runtime)) -> schemas.AdminMetricsOut:
    counts = runtime.counts()
    rows = db.execute(select(Item.category, func.count(Event.event_id))
                      .join(Event, Event.item_id == Item.item_id)
                      .group_by(Item.category)
                      .order_by(func.count(Event.event_id).desc())).all()
    return schemas.AdminMetricsOut(
        items=counts["items"], users=counts["users"], events=counts["events"],
        posts=counts.get("posts", 0),
        purchases=counts["purchases"], model_version=runtime.recommender.model_version,
        fitted_at=runtime.recommender.fitted_at,
        top_categories=[{"category": name, "events": count} for name, count in rows],
    )


@router.post("/admin/model/rebuild", response_model=schemas.RebuildOut, tags=["admin"])
def rebuild_model(db: Session = Depends(get_db), _: User = Depends(require_admin),
                  runtime: Runtime = Depends(get_runtime)) -> schemas.RebuildOut:
    engine = runtime.refresh(force=True)
    total = db.scalar(select(func.count()).select_from(Event)) or 0
    return schemas.RebuildOut(rebuilt=True, model_version=engine.model_version, events=total)

# ------------------------------------------------------------------ shop API


def _cart_row(item: Item, qty: int, checked: bool) -> schemas.CartRowOut:
    return schemas.CartRowOut(item_id=item.item_id, title=item.title,
                              price=float(item.price),
                              cover_url=_cover_url("product", item.item_id),
                              category=item.category, qty=qty, checked=checked)


def _favorite_row(item: Item) -> schemas.FavoriteRowOut:
    return schemas.FavoriteRowOut(item_id=item.item_id, title=item.title,
                                  price=float(item.price),
                                  cover_url=_cover_url("product", item.item_id),
                                  category=item.category)


def _address_out(row: Address) -> schemas.AddressOut:
    return schemas.AddressOut(id=row.address_id, name=row.name, phone=row.phone,
                              region=row.region, detail=row.detail,
                              is_default=bool(row.is_default))


@router.get("/cart", response_model=list[schemas.CartRowOut], tags=["shop"])
def get_cart(db: Session = Depends(get_db),
             user: User = Depends(current_user)) -> list[schemas.CartRowOut]:
    rows = db.scalars(select(CartItem).where(CartItem.user_id == user.user_id)
                      .order_by(CartItem.created_at)).all()
    items = {
        item.item_id: item
        for item in db.scalars(select(Item).where(
            Item.item_id.in_({row.item_id for row in rows})))
    } if rows else {}
    return [_cart_row(items[row.item_id], row.qty, bool(row.checked))
            for row in rows if row.item_id in items]


@router.post("/cart", response_model=list[schemas.CartRowOut], tags=["shop"])
def add_to_cart(payload: schemas.CartIn, db: Session = Depends(get_db),
                user: User = Depends(current_user)) -> list[schemas.CartRowOut]:
    item = db.get(Item, payload.item_id)
    if item is None:
        raise ApiError(404, f"商品 {payload.item_id} 不存在")
    row = db.scalar(select(CartItem).where(CartItem.user_id == user.user_id,
                                           CartItem.item_id == payload.item_id))
    if row is None:
        db.add(CartItem(user_id=user.user_id, item_id=payload.item_id,
                        qty=min(payload.qty, 99), checked=True))
    else:
        row.qty = min(int(row.qty) + payload.qty, 99)
        row.checked = True
    db.flush()
    return get_cart(db, user)


@router.patch("/cart/{item_id}", response_model=list[schemas.CartRowOut], tags=["shop"])
def patch_cart(item_id: str, payload: schemas.CartPatch, db: Session = Depends(get_db),
               user: User = Depends(current_user)) -> list[schemas.CartRowOut]:
    row = db.scalar(select(CartItem).where(CartItem.user_id == user.user_id,
                                           CartItem.item_id == item_id))
    if row is None:
        raise ApiError(404, "购物车里没有这个商品")
    if payload.qty is not None:
        row.qty = payload.qty
    if payload.checked is not None:
        row.checked = payload.checked
    db.flush()
    return get_cart(db, user)


@router.delete("/cart/{item_id}", response_model=list[schemas.CartRowOut], tags=["shop"])
def delete_cart(item_id: str, db: Session = Depends(get_db),
                user: User = Depends(current_user)) -> list[schemas.CartRowOut]:
    row = db.scalar(select(CartItem).where(CartItem.user_id == user.user_id,
                                           CartItem.item_id == item_id))
    if row is not None:
        db.delete(row)
        db.flush()
    return get_cart(db, user)


@router.post("/cart/check-all", response_model=list[schemas.CartRowOut], tags=["shop"])
def check_all_cart(checked: bool = Query(True), db: Session = Depends(get_db),
                   user: User = Depends(current_user)) -> list[schemas.CartRowOut]:
    for row in db.scalars(select(CartItem).where(CartItem.user_id == user.user_id)):
        row.checked = checked
    db.flush()
    return get_cart(db, user)


@router.get("/favorites", response_model=list[schemas.FavoriteRowOut], tags=["shop"])
def get_favorites(db: Session = Depends(get_db),
                  user: User = Depends(current_user)) -> list[schemas.FavoriteRowOut]:
    rows = db.scalars(select(Favorite).where(Favorite.user_id == user.user_id)
                      .order_by(Favorite.created_at.desc())).all()
    items = {
        item.item_id: item
        for item in db.scalars(select(Item).where(
            Item.item_id.in_({row.item_id for row in rows})))
    } if rows else {}
    return [_favorite_row(items[row.item_id]) for row in rows if row.item_id in items]


@router.post("/favorites/{item_id}", status_code=201, tags=["shop"])
def add_favorite(item_id: str, db: Session = Depends(get_db),
                 user: User = Depends(current_user)) -> dict:
    if db.get(Item, item_id) is None:
        raise ApiError(404, f"商品 {item_id} 不存在")
    exists = db.scalar(select(Favorite).where(Favorite.user_id == user.user_id,
                                               Favorite.item_id == item_id))
    if exists is None:
        db.add(Favorite(user_id=user.user_id, item_id=item_id))
        db.flush()
    return {"item_id": item_id, "favorited": True}


@router.delete("/favorites/{item_id}", tags=["shop"])
def remove_favorite(item_id: str, db: Session = Depends(get_db),
                    user: User = Depends(current_user)) -> dict:
    row = db.scalar(select(Favorite).where(Favorite.user_id == user.user_id,
                                           Favorite.item_id == item_id))
    if row is not None:
        db.delete(row)
        db.flush()
    return {"item_id": item_id, "favorited": False}


@router.get("/addresses", response_model=list[schemas.AddressOut], tags=["shop"])
def get_addresses(db: Session = Depends(get_db),
                  user: User = Depends(current_user)) -> list[schemas.AddressOut]:
    rows = db.scalars(select(Address).where(Address.user_id == user.user_id)
                      .order_by(Address.is_default.desc(), Address.created_at)).all()
    return [_address_out(row) for row in rows]


@router.post("/addresses", response_model=schemas.AddressOut, status_code=201, tags=["shop"])
def create_address(payload: schemas.AddressIn, db: Session = Depends(get_db),
                   user: User = Depends(current_user)) -> schemas.AddressOut:
    rows = db.scalars(select(Address).where(Address.user_id == user.user_id)).all()
    make_default = payload.is_default or not rows
    address = Address(address_id=f"A{uuid4().hex[:12]}", user_id=user.user_id,
                      name=payload.name, phone=payload.phone, region=payload.region,
                      detail=payload.detail, is_default=make_default)
    if make_default:
        for row in rows:
            row.is_default = False
    db.add(address)
    db.flush()
    return _address_out(address)


@router.patch("/addresses/{address_id}", response_model=schemas.AddressOut, tags=["shop"])
def update_address(address_id: str, payload: schemas.AddressIn,
                   db: Session = Depends(get_db),
                   user: User = Depends(current_user)) -> schemas.AddressOut:
    row = db.scalar(select(Address).where(Address.address_id == address_id,
                                          Address.user_id == user.user_id))
    if row is None:
        raise ApiError(404, "地址不存在")
    row.name = payload.name
    row.phone = payload.phone
    row.region = payload.region
    row.detail = payload.detail
    if payload.is_default:
        for other in db.scalars(select(Address).where(Address.user_id == user.user_id)):
            other.is_default = other.address_id == address_id
    db.flush()
    return _address_out(row)


@router.delete("/addresses/{address_id}", tags=["shop"])
def delete_address(address_id: str, db: Session = Depends(get_db),
                   user: User = Depends(current_user)) -> dict:
    row = db.scalar(select(Address).where(Address.address_id == address_id,
                                          Address.user_id == user.user_id))
    if row is not None:
        was_default = bool(row.is_default)
        db.delete(row)
        db.flush()
        if was_default:
            rest = db.scalars(select(Address).where(Address.user_id == user.user_id)).all()
            if rest:
                rest[0].is_default = True
                db.flush()
    return {"deleted": address_id}


@router.post("/addresses/{address_id}/default", response_model=list[schemas.AddressOut],
             tags=["shop"])
def set_default_address(address_id: str, db: Session = Depends(get_db),
                        user: User = Depends(current_user)) -> list[schemas.AddressOut]:
    for row in db.scalars(select(Address).where(Address.user_id == user.user_id)):
        row.is_default = row.address_id == address_id
    db.flush()
    return get_addresses(db, user)


def _order_out(row: Order) -> schemas.OrderOut:
    items = json.loads(row.items_json or "[]")
    address = json.loads(row.address_json or "{}")
    return schemas.OrderOut(
        id=row.order_id, status=row.status, payment=row.payment,
        total=float(row.total),
        items=[schemas.CartRowOut(**item) for item in items],
        address=schemas.AddressOut(**address) if address.get("id") else None,
        created_at=row.created_at,
    )


@router.get("/orders", response_model=list[schemas.OrderOut], tags=["shop"])
def get_orders(status: str | None = None, db: Session = Depends(get_db),
               user: User = Depends(current_user)) -> list[schemas.OrderOut]:
    query = select(Order).where(Order.user_id == user.user_id)
    if status and status != "all":
        query = query.where(Order.status == status)
    rows = db.scalars(query.order_by(Order.created_at.desc())).all()
    return [_order_out(row) for row in rows]


@router.post("/orders", response_model=schemas.OrderOut, status_code=201, tags=["shop"])
def create_order(payload: schemas.OrderIn, db: Session = Depends(get_db),
                 user: User = Depends(current_user)) -> schemas.OrderOut:
    address = db.scalar(select(Address).where(Address.address_id == payload.address_id,
                                              Address.user_id == user.user_id))
    if address is None:
        raise ApiError(404, "收货地址不存在")
    rows = db.scalars(select(CartItem).where(CartItem.user_id == user.user_id,
                                             CartItem.checked.is_(True))).all()
    if not rows:
        raise ApiError(422, "购物车里没有勾选商品")
    items = []
    total = 0.0
    for row in rows:
        item = db.get(Item, row.item_id)
        if item is None:
            continue
        total += float(item.price) * int(row.qty)
        items.append(schemas.CartRowOut(item_id=item.item_id, title=item.title,
                                        price=float(item.price),
                                        cover_url=_cover_url("product", item.item_id),
                                        category=item.category, qty=int(row.qty),
                                        checked=True).model_dump())
    order = Order(order_id=f"GT{int(utcnow().timestamp())}{uuid4().hex[:6]}".upper(),
                  user_id=user.user_id, status="pending_payment",
                  payment=payload.payment, total=total,
                  items_json=json.dumps(items, ensure_ascii=False),
                  address_json=json.dumps(_address_out(address).model_dump(),
                                          ensure_ascii=False))
    db.add(order)
    for row in rows:
        db.delete(row)
    db.flush()
    return _order_out(order)


@router.post("/orders/{order_id}/{action}", response_model=schemas.OrderOut, tags=["shop"])
def update_order(order_id: str, action: str, db: Session = Depends(get_db),
                 user: User = Depends(current_user)) -> schemas.OrderOut:
    order = db.scalar(select(Order).where(Order.order_id == order_id,
                                          Order.user_id == user.user_id))
    if order is None:
        raise ApiError(404, "订单不存在")
    transitions = {"pay": "pending_shipment", "ship": "pending_receipt",
                   "receive": "pending_review", "review": "completed",
                   "cancel": "cancelled", "aftersale": "aftersale"}
    if action not in transitions:
        raise ApiError(422, f"未知操作 {action}")
    order.status = transitions[action]
    db.flush()
    return _order_out(order)

# --------------------------------------------------------- phone / SMS / OAuth

SMS_COOLDOWN_SECONDS = 60
SMS_TTL_SECONDS = 300
SMS_MAX_ATTEMPTS = 5


def _code_hash(phone: str, code: str) -> str:
    return hashlib.sha256(f"{phone}:{code}".encode()).hexdigest()


def _sms_dev_mode() -> bool:
    return os.environ.get("SMS_DEV_MODE", "1") != "0"


def _issue_sms_code(db: Session, phone: str, purpose: str) -> str:
    now = utcnow()
    recent = db.scalar(select(VerificationCode).where(
        VerificationCode.phone == phone,
        VerificationCode.purpose == purpose,
        VerificationCode.created_at > now - timedelta(seconds=SMS_COOLDOWN_SECONDS)))
    if recent is not None:
        raise ApiError(429, f"验证码发送过于频繁，请 {SMS_COOLDOWN_SECONDS} 秒后再试")
    code = f"{secrets.randbelow(1_000_000):06d}"
    db.add(VerificationCode(phone=phone, purpose=purpose,
                            code_hash=_code_hash(phone, code),
                            expires_at=now + timedelta(seconds=SMS_TTL_SECONDS)))
    db.flush()
    return code


def _consume_sms_code(db: Session, phone: str, code: str, purpose: str) -> None:
    now = utcnow()
    row = db.scalar(select(VerificationCode)
                    .where(VerificationCode.phone == phone,
                           VerificationCode.purpose == purpose)
                    .order_by(VerificationCode.created_at.desc()))
    if row is None:
        raise ApiError(400, "请先获取验证码")
    if row.expires_at < now:
        raise ApiError(400, "验证码已过期，请重新获取")
    if row.attempts >= SMS_MAX_ATTEMPTS:
        raise ApiError(429, "验证码错误次数过多，请重新获取")
    if row.code_hash != _code_hash(phone, code.strip()):
        row.attempts += 1
        db.flush()
        raise ApiError(401, "验证码不正确")
    db.delete(row)
    db.flush()


def _token_for(runtime: Runtime, user: User) -> schemas.TokenOut:
    token = create_token(runtime.settings.secret, {"sub": user.user_id, "role": user.role})
    return schemas.TokenOut(token=token, expires_in=12 * 3600,
                            user=schemas.UserOut(user_id=user.user_id,
                                                 username=user.username, role=user.role))


@router.post("/auth/sms/send", response_model=schemas.SmsSendOut, tags=["auth"])
def send_sms_code(payload: schemas.SmsSendIn, db: Session = Depends(get_db)) -> schemas.SmsSendOut:
    code = _issue_sms_code(db, payload.phone, payload.purpose)
    dev = _sms_dev_mode()
    # 真实环境这里调用短信服务商；演示模式把验证码直接返回给前端展示
    return schemas.SmsSendOut(ttl=SMS_TTL_SECONDS, dev_code=code if dev else None,
                              message="演示模式：验证码已生成" if dev else "验证码已发送")


@router.post("/auth/register/phone", response_model=schemas.TokenOut, status_code=201,
             tags=["auth"])
def register_with_phone(payload: schemas.PhoneRegisterIn, db: Session = Depends(get_db),
                        runtime: Runtime = Depends(get_runtime)) -> schemas.TokenOut:
    _consume_sms_code(db, payload.phone, payload.code, "register")
    if db.scalar(select(User).where(User.username == payload.username)) is not None:
        raise ApiError(409, "用户名已被占用，换一个试试")
    if db.scalar(select(User).where(User.phone == payload.phone)) is not None:
        raise ApiError(409, "该手机号已注册，可直接用验证码登录")
    user = User(user_id=f"U{uuid4().hex[:12]}", username=payload.username,
                password_hash=hash_password(payload.password), role="user",
                phone=payload.phone, phone_verified=True, provider="phone",
                created_at=utcnow())
    db.add(user)
    db.flush()
    return _token_for(runtime, user)


@router.post("/auth/login/phone", response_model=schemas.TokenOut, tags=["auth"])
def login_with_phone(payload: schemas.PhoneLoginIn, db: Session = Depends(get_db),
                     runtime: Runtime = Depends(get_runtime)) -> schemas.TokenOut:
    _consume_sms_code(db, payload.phone, payload.code, "login")
    user = db.scalar(select(User).where(User.phone == payload.phone))
    if user is None:
        raise ApiError(404, "该手机号还没有注册，请先注册")
    return _token_for(runtime, user)


@router.post("/auth/oauth/{provider}", response_model=schemas.OAuthOut, tags=["auth"])
def oauth_login(provider: str, runtime: Runtime = Depends(get_runtime)) -> schemas.OAuthOut:
    if provider not in {"wechat", "qq"}:
        raise ApiError(422, "只支持 wechat / qq")
    nickname = "微信用户" if provider == "wechat" else "QQ 用户"
    bind_token = create_token(runtime.settings.secret,
                              {"sub": f"oauth:{provider}:{uuid4().hex[:10]}",
                               "provider": provider, "purpose": "bind"}, ttl=600)
    return schemas.OAuthOut(provider=provider, bind_token=bind_token, nickname=nickname)


@router.post("/auth/bind-phone", response_model=schemas.TokenOut, status_code=201, tags=["auth"])
def bind_phone(payload: schemas.BindPhoneIn, db: Session = Depends(get_db),
               runtime: Runtime = Depends(get_runtime)) -> schemas.TokenOut:
    try:
        claims = decode_token(runtime.settings.secret, payload.bind_token)
    except Exception:  # noqa: BLE001
        raise ApiError(401, "绑定会话已失效，请重新授权")
    if claims.get("purpose") != "bind":
        raise ApiError(401, "绑定会话无效")
    _consume_sms_code(db, payload.phone, payload.code, "bind")
    provider = str(claims.get("provider") or "wechat")
    user = db.scalar(select(User).where(User.phone == payload.phone))
    if user is None:
        username = payload.username or f"{provider}_{uuid4().hex[:6]}"
        while db.scalar(select(User).where(User.username == username)) is not None:
            username = f"{provider}_{uuid4().hex[:6]}"
        user = User(user_id=f"U{uuid4().hex[:12]}", username=username,
                    password_hash=hash_password(uuid4().hex), role="user",
                    phone=payload.phone, phone_verified=True, provider=provider,
                    created_at=utcnow())
        db.add(user)
        db.flush()
    else:
        user.phone_verified = True
        user.provider = provider
        db.flush()
    return _token_for(runtime, user)

def _merchant_out(db: Session, merchant: Merchant) -> schemas.MerchantOut:
    count = db.scalar(select(func.count()).select_from(Item)
                      .where(Item.category == merchant.category)) or 0
    return schemas.MerchantOut(merchant_id=merchant.merchant_id, name=merchant.name,
                               category=merchant.category,
                               description=merchant.description or "",
                               rating=float(merchant.rating), followers=merchant.followers,
                               item_count=count,
                               cover_url="")


def _reviews_for(db: Session, item_id: str, limit: int = 20) -> list[schemas.ReviewOut]:
    rows = db.scalars(select(Review).where(Review.item_id == item_id)
                      .order_by(Review.created_at.desc()).limit(limit)).all()
    names = {
        user.user_id: user.username
        for user in db.scalars(select(User).where(
            User.user_id.in_({row.user_id for row in rows})))
    } if rows else {}
    return [schemas.ReviewOut(review_id=row.review_id,
                              user_name=names.get(row.user_id, "匿名买家"),
                              rating=row.rating, content=row.content or "",
                              created_at=row.created_at) for row in rows]


def _rating_of(db: Session, item_id: str) -> tuple[float, int]:
    average, count = db.execute(select(func.avg(Review.rating), func.count(Review.review_id))
                                .where(Review.item_id == item_id)).one()
    return (round(float(average), 2) if average else 0.0, int(count or 0))


@router.get("/items/{item_id}/reviews", response_model=schemas.ReviewSummaryOut,
            tags=["catalog"])
def item_reviews(item_id: str, limit: int = Query(20, ge=1, le=100),
                 db: Session = Depends(get_db)) -> schemas.ReviewSummaryOut:
    if db.get(Item, item_id) is None:
        raise ApiError(404, f"商品 {item_id} 不存在")
    average, count = _rating_of(db, item_id)
    return schemas.ReviewSummaryOut(item_id=item_id, average=average, count=count,
                                    reviews=_reviews_for(db, item_id, limit))


@router.get("/items/{item_id}/detail", response_model=schemas.ItemDetailOut, tags=["catalog"])
def item_detail(item_id: str, db: Session = Depends(get_db)) -> schemas.ItemDetailOut:
    item = db.get(Item, item_id)
    if item is None:
        raise ApiError(404, f"商品 {item_id} 不存在")
    merchant = db.scalar(select(Merchant).where(Merchant.category == item.category))
    average, count = _rating_of(db, item_id)
    return schemas.ItemDetailOut(item=_item_out(item),
                                 merchant=_merchant_out(db, merchant) if merchant else None,
                                 rating=average, review_count=count,
                                 reviews=_reviews_for(db, item_id, 20))


@router.get("/merchants", response_model=list[schemas.MerchantOut], tags=["catalog"])
def list_merchants(db: Session = Depends(get_db)) -> list[schemas.MerchantOut]:
    rows = db.scalars(select(Merchant).order_by(Merchant.rating.desc())).all()
    return [_merchant_out(db, row) for row in rows]


@router.get("/merchants/{merchant_id}", response_model=schemas.ShopOut, tags=["catalog"])
def merchant_shop(merchant_id: str, size: int = Query(60, ge=1, le=200),
                  db: Session = Depends(get_db)) -> schemas.ShopOut:
    merchant = db.get(Merchant, merchant_id)
    if merchant is None:
        raise ApiError(404, "店铺不存在")
    rows = db.scalars(select(Item).where(Item.category == merchant.category)
                      .order_by(Item.item_id).limit(size)).all()
    return schemas.ShopOut(merchant=_merchant_out(db, merchant),
                           items=[_item_out(row) for row in rows])
