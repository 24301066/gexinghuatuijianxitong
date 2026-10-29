"""个性化推荐系统 · FastAPI application factory."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import Settings, load_settings
from .core.errors import ApiError, add_request_id_middleware, register_error_handlers
from .runtime import Runtime

__version__ = "0.1.0"


def _mount_frontend(app: FastAPI, dist: Path) -> None:
    index = dist / "index.html"
    assets = dist / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):  # noqa: ANN202 - FastAPI route
        if full_path.startswith(("api/", "docs", "redoc", "openapi")):
            raise ApiError(404, "接口不存在")
        if not index.is_file():
            return JSONResponse(status_code=503,
                                content={"code": "frontend_missing",
                                         "message": "前端资源未构建，先执行 web 的 npm run build"})
        candidate = dist / full_path
        if full_path and candidate.is_file() and candidate.resolve().is_relative_to(dist.resolve()):
            return FileResponse(candidate)
        return FileResponse(index)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(
        title="个性化推荐系统 API",
        version=__version__,
        description="电商个性化推荐演示系统：商品目录、行为采集、多路召回推荐与离线评估。",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    add_request_id_middleware(app)
    register_error_handlers(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    runtime = Runtime(settings)
    runtime.seed_if_empty()
    runtime.refresh(force=True)
    app.state.runtime = runtime

    from .api import routes  # imported late to avoid a circular import on __version__

    app.include_router(routes.router)

    dist = Path(settings.web_dist)
    if dist.is_dir():
        _mount_frontend(app, dist)
    else:
        @app.get("/", include_in_schema=False)
        def index() -> JSONResponse:  # noqa: ANN202
            return JSONResponse({"service": "gexinghuatuijianxitong",
                                 "version": __version__,
                                 "hint": "前端未构建；API 见 /docs"})

    return app


__all__ = ["create_app", "__version__"]
