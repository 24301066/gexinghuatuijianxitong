"""HTTP routes, all under /api/v1."""

from __future__ import annotations

from collections import Counter
from uuid import uuid4
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import __version__
from ..core.errors import ApiError, request_id_of
from ..core.security import create_token, hash_password, verify_password
from ..db.models import Dwell, Event, Item, Post, Search, User, utcnow
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
