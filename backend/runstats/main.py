"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from starlette import status

from runstats.api.activities import router as activities_router
from runstats.api.chat import router as chat_router
from runstats.api.data_management import router as data_management_router
from runstats.api.devices import router as devices_router
from runstats.api.errors import register_error_handlers
from runstats.api.health import router as health_router
from runstats.api.healthcheck import router as healthcheck_router
from runstats.api.imports import router as imports_router
from runstats.api.settings import router as settings_router
from runstats.api.sync import router as sync_router
from runstats.bluetooth import WatchProvider, create_watch_provider
from runstats.chat import ChatResponseProvider
from runstats.config import Settings, get_settings
from runstats.db.session import create_session_factory, create_sqlite_engine
from runstats.services.sync_scheduler import SyncScheduler
from runstats.services.sync_service import SyncProgressStore


def create_app(
    settings: Settings | None = None,
    watch_provider: WatchProvider | None = None,
    chat_response_provider: ChatResponseProvider | None = None,
) -> FastAPI:
    """Create and configure the RunStats FastAPI application."""

    resolved_settings = settings or get_settings()
    engine = create_sqlite_engine(resolved_settings)
    session_factory = create_session_factory(engine)
    resolved_watch_provider = watch_provider or create_watch_provider(
        resolved_settings.watch_provider
    )
    sync_progress_store = SyncProgressStore()
    sync_scheduler = SyncScheduler(
        session_factory=session_factory,
        provider=resolved_watch_provider,
        runtime_settings=resolved_settings,
        progress_store=sync_progress_store,
        poll_interval_seconds=resolved_settings.sync_scheduler_poll_seconds,
    )

    @asynccontextmanager
    async def lifespan(app_instance: FastAPI) -> AsyncIterator[None]:
        app_instance.state.settings = resolved_settings
        app_instance.state.engine = engine
        app_instance.state.session_factory = session_factory
        app_instance.state.sync_progress_store = sync_progress_store
        app_instance.state.sync_scheduler = sync_scheduler
        app_instance.state.watch_provider = resolved_watch_provider
        app_instance.state.chat_response_provider = chat_response_provider
        await sync_scheduler.start()
        try:
            yield
        finally:
            await sync_scheduler.stop()
            engine.dispose()

    app = FastAPI(title="RunStats API", version="0.1.0", lifespan=lifespan)
    app.state.settings = resolved_settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.sync_progress_store = sync_progress_store
    app.state.sync_scheduler = sync_scheduler
    app.state.watch_provider = resolved_watch_provider
    app.state.chat_response_provider = chat_response_provider

    register_error_handlers(app)
    app.include_router(activities_router, prefix="/api")
    app.include_router(chat_router, prefix="/api")
    app.include_router(data_management_router, prefix="/api")
    app.include_router(devices_router, prefix="/api")
    app.include_router(health_router, prefix="/api")
    app.include_router(healthcheck_router, prefix="/api")
    app.include_router(imports_router, prefix="/api")
    app.include_router(settings_router, prefix="/api")
    app.include_router(sync_router, prefix="/api")
    _register_frontend_routes(app, resolved_settings)
    return app


def _register_frontend_routes(app: FastAPI, settings: Settings) -> None:
    frontend_dist_path = settings.frontend_dist_path.expanduser()
    index_path = frontend_dist_path / "index.html"
    if not index_path.is_file():
        return

    resolved_dist_path = frontend_dist_path.resolve()

    @app.get("/", include_in_schema=False)
    def serve_frontend_root() -> FileResponse:
        return FileResponse(index_path)

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend_path(full_path: str) -> FileResponse:
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        requested_path = (resolved_dist_path / full_path).resolve()
        if not _is_relative_to(requested_path, resolved_dist_path):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        if requested_path.is_file():
            return FileResponse(requested_path)
        return FileResponse(index_path)


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


app = create_app()
