"""Sync run lifecycle, progress, and retry services."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from runstats.api.errors import RunStatsError
from runstats.bluetooth import FakeWatchProvider, WatchProvider, WatchProviderError
from runstats.config import Settings, get_settings
from runstats.db.models import Device, SyncRun
from runstats.schemas import (
    ManualSyncRequest,
    SyncProgressEvent,
    SyncRunListResponse,
    SyncRunResponse,
)
from runstats.services.health_import_service import HealthImportService
from runstats.services.import_service import ActivityImportService

SAFE_ERROR_MAX_LENGTH = 240
DOCUMENTED_SYNC_ERROR_CODES = frozenset(
    {
        "BLUETOOTH_UNAVAILABLE",
        "WATCH_NOT_FOUND",
        "WATCH_CONNECTION_FAILED",
        "WATCH_EXPORT_FAILED",
        "IMPORT_PARSE_FAILED",
        "DATABASE_WRITE_FAILED",
        "SYNC_ALREADY_RUNNING",
    }
)
PROVIDER_ERROR_CODE_MAP = {
    "WATCH_NOT_DISCOVERED": "WATCH_NOT_FOUND",
    "WATCH_EXPORT_UNSUPPORTED": "WATCH_EXPORT_FAILED",
}


@dataclass(frozen=True)
class SyncRunPlan:
    """Progress and final result for one sync run."""

    events: list[SyncProgressEvent]
    final_status: str
    activities_imported: int
    health_records_imported: int
    error_code: str | None
    error_message: str | None


class SyncProgressStore:
    """In-memory progress event history for recently observed sync runs."""

    def __init__(self) -> None:
        self._plans: dict[str, SyncRunPlan] = {}
        self._events: dict[str, list[SyncProgressEvent]] = {}

    def set_plan(self, sync_run_id: str, plan: SyncRunPlan) -> None:
        """Store a completed progress plan."""

        self._plans[sync_run_id] = plan
        self._events[sync_run_id] = list(plan.events)

    def get_plan(self, sync_run_id: str) -> SyncRunPlan | None:
        """Return a stored progress plan if one exists."""

        return self._plans.get(sync_run_id)

    def set_events(
        self,
        sync_run_id: str,
        events: list[SyncProgressEvent],
    ) -> None:
        """Store progress events for websocket observers."""

        self._events[sync_run_id] = list(events)

    def get_events(self, sync_run_id: str) -> list[SyncProgressEvent]:
        """Return stored progress events for one sync run."""

        return list(self._events.get(sync_run_id, []))


class SyncService:
    """Read sync history and execute manual or scheduled syncs."""

    def __init__(
        self,
        session: Session,
        provider: WatchProvider | None = None,
        runtime_settings: Settings | None = None,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.session = session
        self.provider = provider or FakeWatchProvider()
        self.runtime_settings = runtime_settings or get_settings()
        self.clock = clock or (lambda: datetime.now(UTC))

    def start_manual_sync(
        self,
        request: ManualSyncRequest,
        progress_store: SyncProgressStore,
    ) -> SyncRunResponse:
        """Execute a manual sync and persist observable progress."""

        device = self._get_device(request.device_id)
        settings = device.settings
        include_activities = request.include_activities and (
            settings is None or settings.import_activities
        )
        include_health = request.include_health and (
            settings is None or settings.import_health_stats
        )
        return self._run_sync(
            device,
            progress_store,
            include_activities=include_activities,
            include_health=include_health,
        )

    def start_scheduled_sync(
        self,
        device_id: str,
        progress_store: SyncProgressStore,
    ) -> SyncRunResponse:
        """Execute a scheduled sync using the device's persisted settings."""

        device = self._get_device(device_id)
        settings = device.settings
        include_activities = settings is None or settings.import_activities
        include_health = settings is None or settings.import_health_stats
        return self._run_sync(
            device,
            progress_store,
            include_activities=include_activities,
            include_health=include_health,
        )

    def retry_sync(
        self,
        sync_run_id: str,
        progress_store: SyncProgressStore,
    ) -> SyncRunResponse:
        """Retry a failed sync using the current device import settings."""

        previous = self.session.get(SyncRun, sync_run_id)
        if previous is None:
            raise RunStatsError(
                "SYNC_RUN_NOT_FOUND",
                "Sync run not found.",
                details={"sync_run_id": sync_run_id},
                status_code=404,
            )
        if previous.status != "failed":
            raise RunStatsError(
                "SYNC_RUN_NOT_RETRYABLE",
                "Only failed sync runs can be retried.",
                details={"sync_run_id": sync_run_id},
                status_code=409,
            )
        return self.start_scheduled_sync(previous.device_id, progress_store)

    def finalize_manual_sync(
        self,
        sync_run_id: str,
        plan: SyncRunPlan,
    ) -> SyncRunResponse:
        """Apply a stored sync plan's final state to a running sync run."""

        return self._finish_sync_run(sync_run_id, plan)

    def list_sync_runs(
        self,
        *,
        device_id: str | None = None,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> SyncRunListResponse:
        """Return recent sync runs."""

        total_query = select(func.count()).select_from(SyncRun)
        query = select(SyncRun)
        if device_id is not None:
            total_query = total_query.where(SyncRun.device_id == device_id)
            query = query.where(SyncRun.device_id == device_id)
        if status is not None:
            total_query = total_query.where(SyncRun.status == status)
            query = query.where(SyncRun.status == status)

        total = int(self.session.scalar(total_query) or 0)
        runs = list(
            self.session.scalars(
                query.order_by(SyncRun.started_at.desc(), SyncRun.id)
                .limit(limit)
                .offset(offset)
            ).all()
        )
        return SyncRunListResponse(
            items=[_sync_run_response(run) for run in runs],
            total=total,
            limit=limit,
            offset=offset,
        )

    def get_sync_run(self, sync_run_id: str) -> SyncRunResponse:
        """Return one sync run."""

        run = self.session.get(SyncRun, sync_run_id)
        if run is None:
            raise RunStatsError(
                "SYNC_RUN_NOT_FOUND",
                "Sync run not found.",
                details={"sync_run_id": sync_run_id},
                status_code=404,
            )
        return _sync_run_response(run)

    def completion_event_for_run(self, sync_run_id: str) -> SyncProgressEvent:
        """Build a single terminal event from persisted sync history."""

        run = self.session.get(SyncRun, sync_run_id)
        if run is None:
            raise RunStatsError(
                "SYNC_RUN_NOT_FOUND",
                "Sync run not found.",
                details={"sync_run_id": sync_run_id},
                status_code=404,
            )

        if run.status == "failed":
            return SyncProgressEvent(
                sync_run_id=sync_run_id,
                type="failed",
                stage="failed",
                message=safe_error_summary(run.error_message) or "Sync failed.",
                percent=100,
                error_code=run.error_code,
            )

        if run.status == "running":
            return SyncProgressEvent(
                sync_run_id=sync_run_id,
                type="progress",
                stage="running",
                message="Sync is still running.",
                percent=50,
            )

        return SyncProgressEvent(
            sync_run_id=sync_run_id,
            type="completed",
            stage="completed",
            message="Sync completed.",
            percent=100,
        )

    def has_running_sync(self, device_id: str) -> bool:
        """Return whether a device already has a running sync."""

        return (
            self.session.scalar(
                select(SyncRun.id)
                .where(SyncRun.device_id == device_id, SyncRun.status == "running")
                .limit(1)
            )
            is not None
        )

    def last_successful_sync_at(self, device_id: str) -> datetime | None:
        """Return the latest completed successful sync marker for a device."""

        return self.session.scalar(
            select(SyncRun.finished_at)
            .where(
                SyncRun.device_id == device_id,
                SyncRun.status == "succeeded",
                SyncRun.finished_at.is_not(None),
            )
            .order_by(SyncRun.finished_at.desc())
            .limit(1)
        )

    def _run_sync(
        self,
        device: Device,
        progress_store: SyncProgressStore,
        *,
        include_activities: bool,
        include_health: bool,
    ) -> SyncRunResponse:
        self._ensure_no_running_sync(device.id)
        if not include_activities and not include_health:
            raise RunStatsError(
                "SYNC_REQUEST_EMPTY",
                "At least one import type must be enabled for sync.",
                details={"device_id": device.id},
                status_code=422,
            )

        since = self.last_successful_sync_at(device.id)
        run = SyncRun(
            device_id=device.id,
            status="running",
            started_at=self._now(),
            finished_at=None,
            activities_imported=0,
            health_records_imported=0,
            error_code=None,
            error_message=None,
        )
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)

        plan = self._build_sync_plan(
            run.id,
            device,
            include_activities=include_activities,
            include_health=include_health,
            since=since,
        )
        progress_store.set_plan(run.id, plan)
        return self._finish_sync_run(run.id, plan)

    def _ensure_no_running_sync(self, device_id: str) -> None:
        running_id = self.session.scalar(
            select(SyncRun.id)
            .where(SyncRun.device_id == device_id, SyncRun.status == "running")
            .limit(1)
        )
        if running_id is not None:
            raise RunStatsError(
                "SYNC_ALREADY_RUNNING",
                "A sync is already running for this device.",
                details={"device_id": device_id, "sync_run_id": running_id},
                status_code=409,
            )

    def _finish_sync_run(
        self,
        sync_run_id: str,
        plan: SyncRunPlan,
    ) -> SyncRunResponse:
        run = self.session.get(SyncRun, sync_run_id)
        if run is None:
            raise RunStatsError(
                "SYNC_RUN_NOT_FOUND",
                "Sync run not found.",
                details={"sync_run_id": sync_run_id},
                status_code=404,
            )

        if run.status == "running":
            run.status = plan.final_status
            run.finished_at = self._now()
            run.activities_imported = plan.activities_imported
            run.health_records_imported = plan.health_records_imported
            run.error_code = plan.error_code
            run.error_message = plan.error_message
            self.session.commit()
            self.session.refresh(run)
        return _sync_run_response(run)

    def _get_device(self, device_id: str) -> Device:
        device = self.session.get(Device, device_id)
        if device is None:
            raise RunStatsError(
                "DEVICE_NOT_FOUND",
                "Device not found.",
                details={"device_id": device_id},
                status_code=404,
            )
        return device

    def _build_sync_plan(
        self,
        sync_run_id: str,
        device: Device,
        *,
        include_activities: bool,
        include_health: bool,
        since: datetime | None,
    ) -> SyncRunPlan:
        events = [
            SyncProgressEvent(
                sync_run_id=sync_run_id,
                type="progress",
                stage="connecting",
                message=_sync_start_message(since),
                percent=15,
            )
        ]

        try:
            connection = self.provider.test_connection(device.bluetooth_address)
        except WatchProviderError as exc:
            return _failed_plan(
                sync_run_id,
                events,
                code=_documented_error_code(exc.code, "WATCH_CONNECTION_FAILED"),
                message=exc.message,
            )

        if not connection.connected:
            return _failed_plan(
                sync_run_id,
                events,
                code=_documented_error_code(
                    connection.error_code,
                    "WATCH_CONNECTION_FAILED",
                ),
                message=(
                    "Watch connection failed during sync. Keep the watch nearby "
                    "and retry."
                ),
            )

        activities_imported = 0
        health_records_imported = 0

        if include_activities:
            if (
                device.capabilities is None
                or not device.capabilities.supports_ble_activity_export
            ):
                return _failed_plan(
                    sync_run_id,
                    events,
                    code="WATCH_EXPORT_FAILED",
                    message=(
                        "Direct activity export is unavailable for this watch. "
                        "Use folder-based FIT import for activity history."
                    ),
                    stage="activity_export_unavailable",
                )

            events.append(
                SyncProgressEvent(
                    sync_run_id=sync_run_id,
                    type="progress",
                    stage="importing_activities",
                    message="Importing activity exports from watch.",
                    percent=55,
                )
            )
            try:
                payloads = self.provider.export_activities(
                    device.bluetooth_address,
                    since=since,
                )
            except WatchProviderError as exc:
                return _failed_plan(
                    sync_run_id,
                    events,
                    code=_documented_error_code(exc.code, "WATCH_EXPORT_FAILED"),
                    message=exc.message,
                )

            activity_summary = ActivityImportService(
                self.session,
                self.runtime_settings,
            ).import_watch_activity_exports(
                device_id=device.id,
                payloads=payloads,
            )
            activities_imported = activity_summary.created
            if activity_summary.failed > 0:
                return _failed_plan(
                    sync_run_id,
                    events,
                    code=_import_error_code(
                        [result.message for result in activity_summary.files]
                    ),
                    message=(
                        "One or more direct activity exports could not be imported. "
                        f"Created {activity_summary.created}, skipped "
                        f"{activity_summary.skipped}, failed "
                        f"{activity_summary.failed}."
                    ),
                    activities_imported=activities_imported,
                )

        if include_health:
            if (
                device.capabilities is None
                or not device.capabilities.supports_ble_health_export
            ):
                return _failed_plan(
                    sync_run_id,
                    events,
                    code="WATCH_EXPORT_FAILED",
                    message=(
                        "Direct health export is unavailable for this watch. "
                        "Use supported health payload imports until another Garmin "
                        "health adapter is configured."
                    ),
                    stage="health_export_unavailable",
                    activities_imported=activities_imported,
                )

            events.append(
                SyncProgressEvent(
                    sync_run_id=sync_run_id,
                    type="progress",
                    stage="importing_health",
                    message="Importing health exports from watch.",
                    percent=82,
                )
            )
            try:
                payloads = self.provider.export_health(
                    device.bluetooth_address,
                    since=since,
                )
            except WatchProviderError as exc:
                return _failed_plan(
                    sync_run_id,
                    events,
                    code=_documented_error_code(exc.code, "WATCH_EXPORT_FAILED"),
                    message=exc.message,
                    activities_imported=activities_imported,
                )

            health_summary = HealthImportService(
                self.session,
                self.runtime_settings,
            ).import_watch_health_exports(
                device_id=device.id,
                payloads=payloads,
            )
            health_records_imported = health_summary.records_created
            if health_summary.payloads_failed > 0:
                return _failed_plan(
                    sync_run_id,
                    events,
                    code=_import_error_code(
                        [result.message for result in health_summary.payloads]
                    ),
                    message=(
                        "One or more direct health exports could not be imported. "
                        f"Created {health_summary.records_created}, skipped "
                        f"{health_summary.records_skipped}, failed "
                        f"{health_summary.payloads_failed}."
                    ),
                    activities_imported=activities_imported,
                    health_records_imported=health_records_imported,
                )

        events.append(
            SyncProgressEvent(
                sync_run_id=sync_run_id,
                type="completed",
                stage="completed",
                message="Sync completed successfully.",
                percent=100,
            )
        )
        return SyncRunPlan(
            events=events,
            final_status="succeeded",
            activities_imported=activities_imported,
            health_records_imported=health_records_imported,
            error_code=None,
            error_message=None,
        )

    def _now(self) -> datetime:
        return self.clock()


def _failed_plan(
    sync_run_id: str,
    events: list[SyncProgressEvent],
    *,
    code: str,
    message: str,
    stage: str = "failed",
    activities_imported: int = 0,
    health_records_imported: int = 0,
) -> SyncRunPlan:
    safe_message = safe_error_summary(message) or "Sync failed."
    events.append(
        SyncProgressEvent(
            sync_run_id=sync_run_id,
            type="failed",
            stage=stage,
            message=safe_message,
            percent=100,
            error_code=code,
        )
    )
    return SyncRunPlan(
        events=events,
        final_status="failed",
        activities_imported=activities_imported,
        health_records_imported=health_records_imported,
        error_code=code,
        error_message=safe_message,
    )


def _sync_run_response(run: SyncRun) -> SyncRunResponse:
    return SyncRunResponse(
        id=run.id,
        device_id=run.device_id,
        status=run.status,
        started_at=run.started_at,
        finished_at=run.finished_at,
        duration_seconds=_duration_seconds(run),
        activities_imported=run.activities_imported,
        health_records_imported=run.health_records_imported,
        error_code=run.error_code,
        error_summary=safe_error_summary(run.error_message),
    )


def _duration_seconds(run: SyncRun) -> float | None:
    if run.finished_at is None:
        return None
    return (run.finished_at - run.started_at).total_seconds()


def _sync_start_message(since: datetime | None) -> str:
    if since is None:
        return "Connecting to watch for initial sync."
    return f"Connecting to watch for changes since {since.isoformat()}."


def _documented_error_code(
    code: str | None,
    fallback: str,
) -> str:
    if code is None:
        return fallback
    normalized = PROVIDER_ERROR_CODE_MAP.get(code, code)
    if normalized in DOCUMENTED_SYNC_ERROR_CODES:
        return normalized
    return fallback


def _import_error_code(messages: list[str]) -> str:
    if any("persist" in message.lower() for message in messages):
        return "DATABASE_WRITE_FAILED"
    return "IMPORT_PARSE_FAILED"


def safe_error_summary(error_message: str | None) -> str | None:
    """Return a short, user-safe sync failure summary."""

    if not error_message:
        return None
    collapsed = " ".join(error_message.split())
    if "traceback" in collapsed.lower() or "stack trace" in collapsed.lower():
        collapsed = "A sync failure occurred. Check local logs for technical detail."
    if len(collapsed) > SAFE_ERROR_MAX_LENGTH:
        return f"{collapsed[: SAFE_ERROR_MAX_LENGTH - 3].rstrip()}..."
    return collapsed
