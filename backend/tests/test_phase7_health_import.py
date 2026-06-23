import json
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from runstats.bluetooth import FakeWatchProfile, FakeWatchProvider, WatchExportPayload
from runstats.config import Settings
from runstats.db.models import Base, HealthMetric, RawImport
from runstats.db.session import (
    SessionFactory,
    create_session_factory,
    create_sqlite_engine,
)
from runstats.importers import HealthPayloadParser
from runstats.main import create_app
from runstats.schemas import DevicePairRequest, ManualSyncRequest
from runstats.services.device_service import DeviceService
from runstats.services.health_import_service import HealthImportService
from runstats.services.sync_service import SyncProgressStore, SyncService


def test_health_payload_parser_normalizes_supported_metrics() -> None:
    payload = _payload(
        {
            "records": [
                {
                    "metric_type": "steps",
                    "start_time": "2026-06-01T00:00:00Z",
                    "end_time": "2026-06-02T00:00:00Z",
                    "value": 8420,
                    "unit": "steps",
                    "source_record_id": "steps-2026-06-01",
                },
                {
                    "metric_type": "sleep_duration",
                    "start_time": "2026-06-01T22:00:00Z",
                    "durationInSeconds": 28800,
                    "unit": "seconds",
                    "source_record_id": "sleep-2026-06-01",
                },
                {
                    "metric_type": "heart_rate_variability",
                    "start_time": "2026-06-02T06:00:00Z",
                    "value": 0.061,
                    "unit": "seconds",
                    "source_record_id": "hrv-2026-06-02",
                },
            ]
        }
    )

    parsed = HealthPayloadParser().parse(
        payload,
        sha256="abc",
        source_id="health.json",
    )

    assert [(record.metric_type, record.unit) for record in parsed.records] == [
        ("steps", "count"),
        ("sleep", "hours"),
        ("hrv", "ms"),
    ]
    assert parsed.records[1].value == 8.0
    assert parsed.records[2].value == 61.0
    assert parsed.warnings == []


def test_health_payload_parser_expands_daily_summary_and_reports_warnings() -> None:
    payload = _payload(
        {
            "dailySummaries": [
                {
                    "calendarDate": "2026-06-01",
                    "steps": 8000,
                    "restingHeartRateInBeatsPerMinute": 52,
                    "averageStressLevel": 31,
                    "summaryId": "daily-2026-06-01",
                }
            ],
            "records": [
                {
                    "metric_type": "not_supported",
                    "start_time": "2026-06-01T00:00:00Z",
                    "value": 1,
                }
            ],
        }
    )

    parsed = HealthPayloadParser().parse(
        payload,
        sha256="abc",
        source_id="summary.json",
    )

    assert {record.metric_type for record in parsed.records} == {
        "resting_hr",
        "steps",
        "stress",
    }
    assert parsed.records[0].start_time == datetime(2026, 6, 1, tzinfo=UTC)


def test_health_import_service_persists_partial_payload_and_duplicates(
    tmp_path: Path,
) -> None:
    settings, session_factory = _session_factory(tmp_path, "health-import.sqlite3")
    health_path = tmp_path / "health.json"
    health_path.write_bytes(
        _payload(
            {
                "records": [
                    {
                        "metric_type": "steps",
                        "start_time": "2026-06-01T00:00:00Z",
                        "end_time": "2026-06-02T00:00:00Z",
                        "value": 8420,
                        "unit": "count",
                        "source_record_id": "steps-2026-06-01",
                    },
                    {
                        "metric_type": "sleep",
                        "start_time": "2026-06-01T22:00:00Z",
                        "durationInSeconds": 25200,
                        "unit": "seconds",
                        "source_record_id": "sleep-2026-06-01",
                    },
                    {
                        "metric_type": "unsupported",
                        "start_time": "2026-06-01T00:00:00Z",
                        "value": 1,
                    },
                    {
                        "metric_type": "resting_hr",
                        "value": 52,
                        "unit": "bpm",
                    },
                ]
            }
        )
    )

    with session_factory() as session:
        device_id = _paired_device_id(session)
        service = HealthImportService(session, settings)
        result = service.import_health_file(device_id=device_id, file_path=health_path)
        duplicate_raw = service.import_health_file(
            device_id=device_id,
            file_path=health_path,
        )
        duplicate_record = service.import_health_payload(
            device_id=device_id,
            payload=_payload(
                {
                    "records": [
                        {
                            "metric_type": "steps",
                            "start_time": "2026-06-01T00:00:00Z",
                            "end_time": "2026-06-02T00:00:00Z",
                            "value": 8420,
                            "unit": "count",
                            "source_record_id": "steps-2026-06-01",
                        },
                        {
                            "metric_type": "resting_hr",
                            "start_time": "2026-06-01T00:00:00Z",
                            "value": 52,
                            "unit": "bpm",
                            "source_record_id": "rhr-2026-06-01",
                        },
                    ]
                }
            ),
            source_id="second-health.json",
        )
        health_count = session.scalar(select(func.count()).select_from(HealthMetric))
        raw_import = session.scalar(
            select(RawImport).where(RawImport.kind == "health_payload")
        )

    assert result.status == "created"
    assert result.records_created == 2
    assert result.records_skipped == 2
    assert result.archived is True
    assert len(result.warnings or []) == 2
    assert duplicate_raw.status == "skipped"
    assert duplicate_raw.message == "Duplicate raw health payload already archived."
    assert duplicate_record.status == "created"
    assert duplicate_record.records_created == 1
    assert duplicate_record.records_skipped == 1
    assert health_count == 3
    assert raw_import is not None
    assert Path(raw_import.storage_path).exists()


def test_sync_service_imports_direct_health_exports_when_supported(
    tmp_path: Path,
) -> None:
    settings, session_factory = _session_factory(tmp_path, "health-sync.sqlite3")
    provider = ExportingHealthProvider()
    progress_store = SyncProgressStore()

    with session_factory() as session:
        device_service = DeviceService(session, provider)
        paired = device_service.pair_device(
            DevicePairRequest(
                bluetooth_device_id="fake-fr-health",
                display_name=None,
            )
        )
        device_service.probe_capabilities(paired.id)

        sync_service = SyncService(session, provider, settings)
        running = sync_service.start_manual_sync(
            ManualSyncRequest(
                device_id=paired.id,
                include_activities=False,
                include_health=True,
            ),
            progress_store,
        )
        plan = progress_store.get_plan(running.id)
        assert plan is not None
        completed = sync_service.finalize_manual_sync(running.id, plan)
        health_count = session.scalar(select(func.count()).select_from(HealthMetric))
        raw_count = session.scalar(select(func.count()).select_from(RawImport))

    assert completed.status == "succeeded"
    assert completed.activities_imported == 0
    assert completed.health_records_imported == 2
    assert [event.stage for event in plan.events] == [
        "connecting",
        "importing_health",
        "completed",
    ]
    assert health_count == 2
    assert raw_count == 1


def test_sync_service_reports_unsupported_direct_health_export(
    tmp_path: Path,
) -> None:
    settings, session_factory = _session_factory(tmp_path, "health-unsupported.sqlite3")
    provider = FakeWatchProvider()
    progress_store = SyncProgressStore()

    with session_factory() as session:
        paired = DeviceService(session, provider).pair_device(
            DevicePairRequest(
                bluetooth_device_id="fake-fr935-001",
                display_name=None,
            )
        )
        sync_service = SyncService(session, provider, settings)
        running = sync_service.start_manual_sync(
            ManualSyncRequest(
                device_id=paired.id,
                include_activities=False,
                include_health=True,
            ),
            progress_store,
        )
        plan = progress_store.get_plan(running.id)
        assert plan is not None
        completed = sync_service.finalize_manual_sync(running.id, plan)

    assert completed.status == "failed"
    assert completed.health_records_imported == 0
    assert completed.error_summary is not None
    assert "Direct health export is unavailable" in completed.error_summary
    assert [event.stage for event in plan.events] == [
        "connecting",
        "health_export_unavailable",
    ]


def test_health_payload_import_api_persists_and_discovers_metrics(
    tmp_path: Path,
) -> None:
    app = _empty_app(tmp_path)
    health_path = tmp_path / "api-health.json"
    health_path.write_bytes(
        _payload(
            {
                "records": [
                    {
                        "metric_type": "body_battery",
                        "start_time": "2026-06-01T12:00:00Z",
                        "value": 74,
                        "unit": "score",
                        "source_record_id": "body-battery-2026-06-01",
                    }
                ]
            }
        )
    )

    with TestClient(app) as client:
        pair = client.post(
            "/api/devices/pair",
            json={"bluetooth_device_id": "fake-fr935-001"},
        )
        imported = client.post(
            "/api/imports/health-payload",
            json={
                "device_id": pair.json()["id"],
                "file_path": str(health_path),
            },
        )
        metrics = client.get("/api/health/metrics")

    assert imported.status_code == 200
    assert imported.json()["records_created"] == 1
    assert imported.json()["raw_files_archived"] == 1
    assert metrics.status_code == 200
    assert metrics.json()["metrics"][0]["metric_type"] == "body_battery"


class ExportingHealthProvider(FakeWatchProvider):
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

    def export_health(
        self,
        bluetooth_device_id: str,
        *,
        since: object | None = None,
    ) -> list[WatchExportPayload]:
        assert bluetooth_device_id == "fake-fr-health"
        _ = since
        return [
            WatchExportPayload(
                kind="health",
                source_id="watch-health.json",
                content_type="application/json",
                payload=_payload(
                    {
                        "records": [
                            {
                                "metric_type": "steps",
                                "start_time": "2026-06-01T00:00:00Z",
                                "end_time": "2026-06-02T00:00:00Z",
                                "value": 8420,
                                "unit": "count",
                                "source_record_id": "watch-steps-2026-06-01",
                            },
                            {
                                "metric_type": "resting_hr",
                                "start_time": "2026-06-01T00:00:00Z",
                                "value": 52,
                                "unit": "bpm",
                                "source_record_id": "watch-rhr-2026-06-01",
                            },
                        ]
                    }
                ),
            )
        ]


def _paired_device_id(session: Session) -> str:
    service = DeviceService(session)
    return service.pair_device(
        DevicePairRequest(
            bluetooth_device_id="fake-fr935-001",
            display_name=None,
        )
    ).id


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


def _empty_app(tmp_path: Path) -> FastAPI:
    settings = Settings(
        database_path=tmp_path / "phase7-api.sqlite3",
        raw_archive_path=tmp_path / "archive",
        watch_provider="fake",
    )
    app = create_app(settings)
    Base.metadata.create_all(bind=app.state.engine)
    return app


def _payload(payload: object) -> bytes:
    return json.dumps(payload).encode("utf-8")
