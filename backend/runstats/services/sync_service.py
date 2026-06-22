"""Sync run read and fake lifecycle services."""

from __future__ import annotations

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
from runstats.services.import_service import ActivityImportService

SAFE_ERROR_MAX_LENGTH = 240


@dataclass(frozen=True)
class SyncRunPlan:
    """Fake progress and final result for one manual sync run."""

    events: list[SyncProgressEvent]
    final_status: str
    activities_imported: int
    health_records_imported: int
    error_message: str | None


class SyncProgressStore:
    """In-memory fake progress plans for active sync runs."""

    def __init__(self) -> None:
        self._plans: dict[str, SyncRunPlan] = {}

    def set_plan(self, sync_run_id: str, plan: SyncRunPlan) -> None:
        """Store a fake progress plan."""

        self._plans[sync_run_id] = plan

    def get_plan(self, sync_run_id: str) -> SyncRunPlan | None:
        """Return a stored fake progress plan if one exists."""

        return self._plans.get(sync_run_id)


class SyncService:
    """Read sync history and run fake manual syncs."""

    def __init__(
        self,
        session: Session,
        provider: WatchProvider | None = None,
        runtime_settings: Settings | None = None,
    ) -> None:
        self.session = session
        self.provider = provider or FakeWatchProvider()
        self.runtime_settings = runtime_settings or get_settings()

    def start_manual_sync(
        self,
        request: ManualSyncRequest,
        progress_store: SyncProgressStore,
    ) -> SyncRunResponse:
        """Create a fake manual sync run and queue progress events."""

        device = self.session.get(Device, request.device_id)
        if device is None:
            raise RunStatsError(
                "DEVICE_NOT_FOUND",
                "Device not found.",
                details={"device_id": request.device_id},
                status_code=404,
            )

        now = datetime.now(UTC)
        run = SyncRun(
            device=device,
            status="running",
            started_at=now,
            finished_at=None,
            activities_imported=0,
            health_records_imported=0,
            error_message=None,
        )
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)
        progress_store.set_plan(run.id, self._build_sync_plan(run.id, device, request))
        return _sync_run_response(run)

    def finalize_manual_sync(
        self,
        sync_run_id: str,
        plan: SyncRunPlan,
    ) -> SyncRunResponse:
        """Apply a fake sync plan's final state to a sync run."""

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
            run.finished_at = datetime.now(UTC)
            run.activities_imported = plan.activities_imported
            run.health_records_imported = plan.health_records_imported
            run.error_message = plan.error_message
            self.session.commit()
            self.session.refresh(run)
        return _sync_run_response(run)

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

    def _build_sync_plan(
        self,
        sync_run_id: str,
        device: Device,
        request: ManualSyncRequest,
    ) -> SyncRunPlan:
        settings = device.settings
        include_activities = request.include_activities and (
            settings is None or settings.import_activities
        )
        include_health = request.include_health and (
            settings is None or settings.import_health_stats
        )
        events = [
            SyncProgressEvent(
                sync_run_id=sync_run_id,
                type="progress",
                stage="connecting",
                message="Connecting to watch.",
                percent=15,
            )
        ]

        if not self.provider.test_connection(device.bluetooth_address).connected:
            message = (
                "Watch connection failed during sync. Keep the watch nearby and retry."
            )
            events.append(
                SyncProgressEvent(
                    sync_run_id=sync_run_id,
                    type="failed",
                    stage="failed",
                    message=message,
                    percent=100,
                )
            )
            return SyncRunPlan(
                events=events,
                final_status="failed",
                activities_imported=0,
                health_records_imported=0,
                error_message=message,
            )

        activities_imported = 0
        health_records_imported = 5 if include_health else 0

        if include_activities:
            if (
                device.capabilities is None
                or not device.capabilities.supports_ble_activity_export
            ):
                message = (
                    "Direct activity export is unavailable for this watch. "
                    "Use folder-based FIT import for activity history."
                )
                events.append(
                    SyncProgressEvent(
                        sync_run_id=sync_run_id,
                        type="failed",
                        stage="activity_export_unavailable",
                        message=message,
                        percent=100,
                    )
                )
                return SyncRunPlan(
                    events=events,
                    final_status="failed",
                    activities_imported=0,
                    health_records_imported=0,
                    error_message=message,
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
                payloads = self.provider.export_activities(device.bluetooth_address)
            except WatchProviderError as exc:
                message = safe_error_summary(exc.message) or "Activity export failed."
                events.append(
                    SyncProgressEvent(
                        sync_run_id=sync_run_id,
                        type="failed",
                        stage="failed",
                        message=message,
                        percent=100,
                    )
                )
                return SyncRunPlan(
                    events=events,
                    final_status="failed",
                    activities_imported=0,
                    health_records_imported=0,
                    error_message=message,
                )

            summary = ActivityImportService(
                self.session,
                self.runtime_settings,
            ).import_watch_activity_exports(
                device_id=device.id,
                payloads=payloads,
            )
            activities_imported = summary.created
            if summary.failed > 0:
                message = (
                    "One or more direct activity exports could not be imported. "
                    f"Created {summary.created}, skipped {summary.skipped}, "
                    f"failed {summary.failed}."
                )
                events.append(
                    SyncProgressEvent(
                        sync_run_id=sync_run_id,
                        type="failed",
                        stage="failed",
                        message=message,
                        percent=100,
                    )
                )
                return SyncRunPlan(
                    events=events,
                    final_status="failed",
                    activities_imported=activities_imported,
                    health_records_imported=0,
                    error_message=message,
                )
        if include_health:
            events.append(
                SyncProgressEvent(
                    sync_run_id=sync_run_id,
                    type="progress",
                    stage="importing_health",
                    message="Mock imported 5 health records.",
                    percent=82,
                )
            )

        events.append(
            SyncProgressEvent(
                sync_run_id=sync_run_id,
                type="completed",
                stage="completed",
                message="Mock sync completed successfully.",
                percent=100,
            )
        )
        return SyncRunPlan(
            events=events,
            final_status="succeeded",
            activities_imported=activities_imported,
            health_records_imported=health_records_imported,
            error_message=None,
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
        error_summary=safe_error_summary(run.error_message),
    )


def _duration_seconds(run: SyncRun) -> float | None:
    if run.finished_at is None:
        return None
    return (run.finished_at - run.started_at).total_seconds()


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
