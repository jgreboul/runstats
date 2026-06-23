import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from runstats.bluetooth import (
    FakeWatchProfile,
    FakeWatchProvider,
    WatchExportPayload,
    WatchProviderError,
)
from runstats.config import Settings
from runstats.db.models import Base, HealthMetric, SyncRun
from runstats.db.session import (
    SessionFactory,
    create_session_factory,
    create_sqlite_engine,
)
from runstats.main import create_app
from runstats.schemas import (
    DevicePairRequest,
    DeviceSettingsPatchRequest,
    ManualSyncRequest,
)
from runstats.services.device_service import DeviceService
from runstats.services.sync_scheduler import SyncScheduler
from runstats.services.sync_service import SyncProgressStore, SyncService


def test_incremental_sync_uses_last_success_and_does_not_duplicate(
    tmp_path: Path,
) -> None:
    settings, session_factory = _session_factory(tmp_path, "incremental.sqlite3")
    provider = IncrementalHealthProvider()
    progress_store = SyncProgressStore()
    clock = SequenceClock(datetime(2026, 6, 1, 8, 0, tzinfo=UTC))

    with session_factory() as session:
        device_id = _paired_health_device_id(session, provider)
        service = SyncService(session, provider, settings, clock=clock)

        first = service.start_manual_sync(
            ManualSyncRequest(
                device_id=device_id,
                include_activities=False,
                include_health=True,
            ),
            progress_store,
        )

        provider.fail_next_export = True
        failed = service.start_manual_sync(
            ManualSyncRequest(
                device_id=device_id,
                include_activities=False,
                include_health=True,
            ),
            progress_store,
        )

        third = service.start_manual_sync(
            ManualSyncRequest(
                device_id=device_id,
                include_activities=False,
                include_health=True,
            ),
            progress_store,
        )
        health_count = session.scalar(select(func.count()).select_from(HealthMetric))

    assert first.status == "succeeded"
    assert first.health_records_imported == 1
    assert failed.status == "failed"
    assert failed.error_code == "WATCH_EXPORT_FAILED"
    assert third.status == "succeeded"
    assert third.health_records_imported == 0
    assert health_count == 1
    assert provider.since_values[0] is None
    assert provider.since_values[1] == first.finished_at
    assert provider.since_values[2] == first.finished_at
    assert provider.since_values[2] != failed.finished_at


def test_scheduled_sync_respects_interval_and_skips_running_sync(
    tmp_path: Path,
) -> None:
    settings, session_factory = _session_factory(tmp_path, "scheduled.sqlite3")
    provider = IncrementalHealthProvider()
    progress_store = SyncProgressStore()
    started_at = datetime(2026, 6, 1, 8, 0, tzinfo=UTC)

    with session_factory() as session:
        device_id = _paired_health_device_id(session, provider)
        DeviceService(session, provider).update_settings(
            device_id,
            DeviceSettingsPatchRequest(
                auto_sync_enabled=True,
                sync_interval_minutes=60,
                import_activities=False,
                import_health_stats=True,
            ),
        )

    scheduler = SyncScheduler(
        session_factory=session_factory,
        provider=provider,
        runtime_settings=settings,
        progress_store=progress_store,
        clock=lambda: started_at,
    )

    first_due = scheduler.run_due_syncs(now=started_at)
    not_due = scheduler.run_due_syncs(now=started_at + timedelta(minutes=30))
    second_due = scheduler.run_due_syncs(now=started_at + timedelta(minutes=61))

    with session_factory() as session:
        run_count = session.scalar(select(func.count()).select_from(SyncRun))
        session.add(
            SyncRun(
                device_id=device_id,
                status="running",
                started_at=started_at + timedelta(hours=2, minutes=30),
            )
        )
        session.commit()

    skipped_running = scheduler.run_due_syncs(now=started_at + timedelta(hours=3))

    assert len(first_due) == 1
    assert len(not_due) == 0
    assert len(second_due) == 1
    assert run_count == 2
    assert skipped_running == []


def test_sync_api_reports_progress_and_retries_failed_sync(
    tmp_path: Path,
) -> None:
    app = _empty_app(tmp_path, watch_provider=IncrementalHealthProvider())

    with TestClient(app) as client:
        pair = client.post(
            "/api/devices/pair",
            json={"bluetooth_device_id": "fake-fr-health"},
        )
        device_id = pair.json()["id"]
        client.post(f"/api/devices/{device_id}/probe-capabilities")
        client.patch(
            f"/api/devices/{device_id}/settings",
            json={
                "import_activities": False,
                "import_health_stats": True,
            },
        )
        provider = app.state.watch_provider
        provider.fail_next_export = True

        created = client.post(
            "/api/sync-runs",
            json={
                "device_id": device_id,
                "include_activities": False,
                "include_health": True,
            },
        )
        sync_run_id = created.json()["id"]
        detail_before_stream = client.get(f"/api/sync-runs/{sync_run_id}")

        with client.websocket_connect(f"/api/sync-runs/{sync_run_id}/events") as ws:
            events = [ws.receive_json() for _ in range(3)]

        retry = client.post(f"/api/sync-runs/{sync_run_id}/retry")

    assert created.status_code == 201
    assert created.json()["status"] == "failed"
    assert created.json()["error_code"] == "WATCH_EXPORT_FAILED"
    assert detail_before_stream.json()["status"] == "failed"
    assert [event["stage"] for event in events] == [
        "connecting",
        "importing_health",
        "failed",
    ]
    assert events[-1]["error_code"] == "WATCH_EXPORT_FAILED"
    assert retry.status_code == 201
    assert retry.json()["status"] == "succeeded"
    assert retry.json()["health_records_imported"] == 1


class IncrementalHealthProvider(FakeWatchProvider):
    def __init__(self) -> None:
        super().__init__(
            (
                FakeWatchProfile(
                    bluetooth_device_id="fake-fr-health",
                    name="Garmin Forerunner Health",
                    model="Forerunner Health",
                    model_hint="Forerunner",
                    rssi=-45,
                    serial_number="FR-HEALTH",
                    firmware_version="1.0",
                    supports_ble_activity_export=False,
                    supports_ble_health_export=True,
                    supports_folder_import=True,
                    connection_succeeds=True,
                    capability_notes="Direct health export detected.",
                    service_uuids=("fake-garmin-health-export",),
                ),
            )
        )
        self.fail_next_export = False
        self.since_values: list[datetime | None] = []

    def export_health(
        self,
        bluetooth_device_id: str,
        *,
        since: datetime | None = None,
    ) -> list[WatchExportPayload]:
        assert bluetooth_device_id == "fake-fr-health"
        self.since_values.append(since)
        if self.fail_next_export:
            self.fail_next_export = False
            raise WatchProviderError(
                "WATCH_EXPORT_FAILED",
                "Watch health export failed. Keep the watch nearby and retry.",
                status_code=503,
            )
        return [
            WatchExportPayload(
                kind="health",
                source_id="watch-health-incremental.json",
                content_type="application/json",
                payload=json.dumps(
                    {
                        "records": [
                            {
                                "metric_type": "steps",
                                "start_time": "2026-06-01T00:00:00Z",
                                "end_time": "2026-06-02T00:00:00Z",
                                "value": 8420,
                                "unit": "count",
                                "source_record_id": "watch-steps-2026-06-01",
                            }
                        ]
                    }
                ).encode("utf-8"),
            )
        ]


class SequenceClock:
    def __init__(self, start: datetime) -> None:
        self.current = start

    def __call__(self) -> datetime:
        current = self.current
        self.current += timedelta(minutes=1)
        return current


def _paired_health_device_id(session: Session, provider: FakeWatchProvider) -> str:
    service = DeviceService(session, provider)
    paired = service.pair_device(
        DevicePairRequest(
            bluetooth_device_id="fake-fr-health",
            display_name=None,
        )
    )
    service.probe_capabilities(paired.id)
    return paired.id


def _session_factory(
    tmp_path: Path,
    filename: str,
) -> tuple[Settings, SessionFactory]:
    settings = Settings(
        database_path=tmp_path / filename,
        raw_archive_path=tmp_path / "archive",
        watch_provider="fake",
    )
    engine = create_sqlite_engine(settings)
    Base.metadata.create_all(bind=engine)
    return settings, create_session_factory(engine)


def _empty_app(
    tmp_path: Path,
    watch_provider: FakeWatchProvider,
) -> FastAPI:
    settings = Settings(
        database_path=tmp_path / "phase9-api.sqlite3",
        raw_archive_path=tmp_path / "archive",
        watch_provider="fake",
    )
    app = create_app(settings, watch_provider=watch_provider)
    Base.metadata.create_all(bind=app.state.engine)
    return app
