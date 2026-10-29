"""FastAPI dependencies: request runtime, DB session and authentication."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from ..core.errors import ApiError
from ..core.security import TokenError, decode_token
from ..db.models import User
from ..runtime import Runtime


def get_runtime(request: Request) -> Runtime:
    return request.app.state.runtime


def get_db(request: Request) -> Iterator[Session]:
    runtime: Runtime = request.app.state.runtime
    session = runtime.session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _bearer_token(request: Request) -> str:
    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise ApiError(401, "缺少或格式错误的 Authorization 头")
    return token


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    runtime: Runtime = request.app.state.runtime
    try:
        payload = decode_token(runtime.settings.secret, _bearer_token(request))
    except TokenError as exc:
        raise ApiError(401, f"登录状态无效：{exc}") from exc
    user = db.get(User, payload.get("sub"))
    if user is None:
        raise ApiError(401, "用户不存在或已失效")
    return user


def require_admin(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise ApiError(403, "需要管理员权限")
    return user
