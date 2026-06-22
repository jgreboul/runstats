"""Sync history APIs."""

from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, WebSocket
from sqlalchemy.orm import Session

from runstats.bluetooth import WatchProvider
from runstats.config import Settings
from runstats.db.session import get_db_session
from runstats.schemas import ManualSyncRequest, SyncRunListResponse, SyncRunResponse
from runstats.services.sync_service import SyncProgressStore, SyncService

router = APIRouter(prefix="/sync-runs", tags=["sync"])
SessionDep = Annotated[Session, Depends(get_db_session)]


@router.post("", response_model=SyncRunResponse, status_code=201)
def start_manual_sync(
    sync_request: ManualSyncRequest,
    request: Request,
    session: SessionDep,
) -> SyncRunResponse:
    """Start a fake manual sync run."""

    progress_store: SyncProgressStore = request.app.state.sync_progress_store
    watch_provider: WatchProvider = request.app.state.watch_provider
    runtime_settings: Settings = request.app.state.settings
    return SyncService(
        session,
        watch_provider,
        runtime_settings,
    ).start_manual_sync(sync_request, progress_store)


@router.get("", response_model=SyncRunListResponse)
def list_sync_runs(
    session: SessionDep,
    device_id: str | None = None,
    status: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> SyncRunListResponse:
    """Return recent sync runs."""

    return SyncService(session).list_sync_runs(
        device_id=device_id,
        status=status,
        limit=limit,
        offset=offset,
    )


@router.get("/{sync_run_id}", response_model=SyncRunResponse)
def get_sync_run(sync_run_id: str, session: SessionDep) -> SyncRunResponse:
    """Return one sync run."""

    return SyncService(session).get_sync_run(sync_run_id)


@router.websocket("/{sync_run_id}/events")
async def stream_sync_events(websocket: WebSocket, sync_run_id: str) -> None:
    """Stream fake progress events for a sync run."""

    await websocket.accept()
    progress_store: SyncProgressStore = websocket.app.state.sync_progress_store
    session_factory = websocket.app.state.session_factory
    plan = progress_store.get_plan(sync_run_id)

    if plan is not None:
        with session_factory() as session:
            SyncService(session).finalize_manual_sync(sync_run_id, plan)
        events = plan.events
    else:
        with session_factory() as session:
            events = [SyncService(session).completion_event_for_run(sync_run_id)]

    for event in events:
        await websocket.send_json(event.model_dump(mode="json"))
        await asyncio.sleep(0)
