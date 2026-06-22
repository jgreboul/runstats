from pathlib import Path

from sqlalchemy import func, select

from runstats.bluetooth import FakeWatchProvider, WatchExportPayload
from runstats.config import Settings
from runstats.db.models import Activity, Base, RawImport
from runstats.db.session import (
    SessionFactory,
    create_session_factory,
    create_sqlite_engine,
)
from runstats.schemas import DevicePairRequest, ManualSyncRequest
from runstats.services.device_service import DeviceService
from runstats.services.sync_service import SyncProgressStore, SyncService
from tests.fit_fixtures import build_activity_fit


def test_sync_service_imports_direct_activity_exports_when_supported(
    tmp_path: Path,
) -> None:
    settings, session_factory = _session_factory(tmp_path, "direct-export.sqlite3")
    provider = ExportingActivityProvider()
    progress_store = SyncProgressStore()

    with session_factory() as session:
        device_service = DeviceService(session, provider)
        paired = device_service.pair_device(
            DevicePairRequest(
                bluetooth_device_id="fake-fr965-002",
                display_name=None,
            )
        )
        device_service.probe_capabilities(paired.id)

        sync_service = SyncService(session, provider, settings)
        running = sync_service.start_manual_sync(
            ManualSyncRequest(
                device_id=paired.id,
                include_activities=True,
                include_health=False,
            ),
            progress_store,
        )
        plan = progress_store.get_plan(running.id)
        assert plan is not None
        completed = sync_service.finalize_manual_sync(running.id, plan)
        activity_count = session.scalar(select(func.count()).select_from(Activity))
        raw_count = session.scalar(select(func.count()).select_from(RawImport))

    assert completed.status == "succeeded"
    assert completed.activities_imported == 1
    assert completed.health_records_imported == 0
    assert [event.stage for event in plan.events] == [
        "connecting",
        "importing_activities",
        "completed",
    ]
    assert activity_count == 1
    assert raw_count == 1


def test_sync_service_reports_unsupported_direct_activity_export(
    tmp_path: Path,
) -> None:
    settings, session_factory = _session_factory(tmp_path, "unsupported.sqlite3")
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
                include_activities=True,
                include_health=False,
            ),
            progress_store,
        )
        plan = progress_store.get_plan(running.id)
        assert plan is not None
        completed = sync_service.finalize_manual_sync(running.id, plan)

    assert completed.status == "failed"
    assert completed.activities_imported == 0
    assert completed.error_summary is not None
    assert "folder-based FIT import" in completed.error_summary
    assert [event.stage for event in plan.events] == [
        "connecting",
        "activity_export_unavailable",
    ]


class ExportingActivityProvider(FakeWatchProvider):
    def export_activities(self, bluetooth_device_id: str) -> list[WatchExportPayload]:
        assert bluetooth_device_id == "fake-fr965-002"
        return [
            WatchExportPayload(
                kind="activity",
                source_id="watch-export-10k.fit",
                content_type="application/vnd.ant.fit",
                payload=build_activity_fit(),
            )
        ]


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
