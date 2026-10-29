"""HTTP routes, all under /api/v1."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import __version__
from ..core.errors import ApiError, request_id_of
from ..core.security import create_token, verify_password
from ..db.models import Event, Item, User, utcnow
from ..runtime import Runtime
from . import schemas
from .deps import current_user, get_db, get_runtime, require_admin

router = APIRouter(prefix="/api/v1")

DEDUPE_WINDOW_SECONDS = 30


def _item_out(item: Item) -> schemas.ItemOut:
    return schemas.ItemOut(item_id=item.item_id, title=item.title, category=item.category,
                           price=float(item.price), tags=item.tag_list(),
                           description=item.description or "")


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
                              items=[schemas.RecommendationItem(**row)
                                     for row in result["items"]])


@router.post("/events", response_model=schemas.EventOut, status_code=201, tags=["behaviour"])
def create_event(payload: schemas.EventIn, db: Session = Depends(get_db),
                 user: User = Depends(current_user),
                 runtime: Runtime = Depends(get_runtime)) -> schemas.EventOut:
    if db.get(Item, payload.item_id) is None:
        raise ApiError(404, f"商品 {payload.item_id} 不存在")

    now = utcnow()
    bucket = int(now.timestamp() // DEDUPE_WINDOW_SECONDS)
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
        items=[schemas.RecommendationItem(**row) for row in result["items"]],
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
