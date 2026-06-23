"""Background scheduling for configured automatic sync."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from runstats.api.errors import RunStatsError
from runstats.bluetooth import WatchProvider
from runstats.config import Settings
from runstats.db.models import Device, DeviceSettings, SyncRun
from runstats.db.session import SessionFactory
from runstats.schemas import SyncRunResponse
from runstats.services.sync_service import SyncProgressStore, SyncService


class SyncScheduler:
    """Run due automatic syncs from persisted device settings."""

    def __init__(
        self,
        *,
        session_factory: SessionFactory,
        provider: WatchProvider,
        runtime_settings: Settings,
        progress_store: SyncProgressStore,
        clock: Callable[[], datetime] | None = None,
        poll_interval_seconds: float = 60.0,
    ) -> None:
        self.session_factory = session_factory
        self.provider = provider
        self.runtime_settings = runtime_settings
        self.progress_store = progress_store
        self.clock = clock or (lambda: datetime.now(UTC))
        self.poll_interval_seconds = poll_interval_seconds
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start the background scheduler loop."""

        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        """Stop the background scheduler loop."""

        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    def run_due_syncs(self, *, now: datetime | None = None) -> list[SyncRunResponse]:
        """Run every enabled device whose sync interval has elapsed."""

        resolved_now = _coerce_utc(now or self.clock())
        results: list[SyncRunResponse] = []
        with self.session_factory() as session:
            devices = list(
                session.scalars(
                    select(Device)
                    .join(DeviceSettings)
                    .where(DeviceSettings.auto_sync_enabled.is_(True))
                    .order_by(Device.id)
                ).all()
            )
            service = SyncService(
                session,
                self.provider,
                self.runtime_settings,
                clock=lambda: resolved_now,
            )
            for device in devices:
                if device.settings is None:
                    continue
                if not (
                    device.settings.import_activities
                    or device.settings.import_health_stats
                ):
                    continue
                if not _sync_due(session, device, resolved_now):
                    continue
                try:
                    results.append(
                        service.start_scheduled_sync(device.id, self.progress_store)
                    )
                except RunStatsError as exc:
                    if exc.code == "SYNC_ALREADY_RUNNING":
                        continue
                    raise
        return results

    async def _run_loop(self) -> None:
        while True:
            await asyncio.sleep(self.poll_interval_seconds)
            await asyncio.to_thread(self.run_due_syncs)


def _sync_due(session: Session, device: Device, now: datetime) -> bool:
    latest_run = _latest_run(session, device.id)
    if latest_run is None:
        return True
    if latest_run.status == "running":
        return False
    settings = device.settings
    if settings is None:
        return False
    started_at = _coerce_utc(latest_run.started_at)
    next_due_at = started_at + timedelta(minutes=settings.sync_interval_minutes)
    return next_due_at <= now


def _latest_run(session: Session, device_id: str) -> SyncRun | None:
    return session.scalar(
        select(SyncRun)
        .where(SyncRun.device_id == device_id)
        .order_by(SyncRun.started_at.desc())
        .limit(1)
    )


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
