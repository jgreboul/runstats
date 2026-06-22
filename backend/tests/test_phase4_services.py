from pathlib import Path

from runstats.bluetooth import FakeWatchProfile, FakeWatchProvider
from runstats.config import Settings
from runstats.db.models import Base
from runstats.db.session import (
    SessionFactory,
    create_session_factory,
    create_sqlite_engine,
)
from runstats.schemas import (
    DevicePairRequest,
    DeviceSettingsPatchRequest,
    ManualSyncRequest,
)
from runstats.services.device_service import DeviceService
from runstats.services.sync_service import SyncProgressStore, SyncService


def test_device_service_scans_pairs_updates_and_tests_connection(
    tmp_path: Path,
) -> None:
    session_factory = _session_factory(tmp_path, "devices.sqlite3")

    with session_factory() as session:
        service = DeviceService(session)
        scan = service.scan_for_watches()
        paired = service.pair_device(
            DevicePairRequest(
                bluetooth_device_id="fake-fr935-001",
                display_name="My Forerunner",
            )
        )
        known_scan = service.scan_for_watches()
        updated = service.update_settings(
            paired.id,
            DeviceSettingsPatchRequest(
                auto_sync_enabled=True,
                sync_interval_minutes=120,
                import_health_stats=False,
                preferred_units="imperial",
                historical_fit_import_folder="D:/Runs/FIT",
            ),
        )
        connection = service.test_connection(paired.id)
        capabilities = service.probe_capabilities(paired.id)

    assert any(device.name == "Garmin Forerunner 935" for device in scan.devices)
    assert scan.devices[0].is_known is False
    assert paired.name == "My Forerunner"
    assert paired.settings.preferred_units == "metric"
    assert paired.capabilities.supports_folder_import is True
    assert any(
        device.id == "fake-fr935-001" and device.is_known
        for device in known_scan.devices
    )
    assert updated.settings.auto_sync_enabled is True
    assert updated.settings.sync_interval_minutes == 120
    assert updated.settings.import_health_stats is False
    assert updated.settings.preferred_units == "imperial"
    assert updated.settings.historical_fit_import_folder == "D:/Runs/FIT"
    assert connection.success is True
    assert connection.status == "connected"
    assert connection.last_seen_at is not None
    assert capabilities.supports_ble_activity_export is False
    assert capabilities.supports_ble_health_export is False
    assert capabilities.supports_folder_import is True
    assert capabilities.probed_at is not None


def test_device_service_persists_fake_capability_matrices(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path, "capabilities.sqlite3")
    provider = FakeWatchProvider(
        (
            FakeWatchProfile(
                bluetooth_device_id="fake-fr-next",
                name="Garmin Forerunner Next",
                model="Forerunner Next",
                model_hint="Forerunner",
                rssi=-42,
                serial_number="FR-NEXT",
                firmware_version="1.0",
                supports_ble_activity_export=True,
                supports_ble_health_export=True,
                supports_folder_import=False,
                connection_succeeds=True,
                capability_notes="Direct BLE activity and health export detected.",
                service_uuids=("activity-export", "health-export"),
            ),
        )
    )

    with session_factory() as session:
        service = DeviceService(session, provider)
        paired = service.pair_device(
            DevicePairRequest(
                bluetooth_device_id="fake-fr-next",
                display_name=None,
            )
        )
        capabilities = service.probe_capabilities(paired.id)
        stored = service.get_capabilities(paired.id)

    assert capabilities.supports_ble_activity_export is True
    assert capabilities.supports_ble_health_export is True
    assert capabilities.supports_folder_import is False
    assert (
        capabilities.capability_notes
        == "Direct BLE activity and health export detected."
    )
    assert stored == capabilities


def test_device_service_returns_fake_connection_failure(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path, "offline-device.sqlite3")

    with session_factory() as session:
        service = DeviceService(session)
        offline = service.pair_device(
            DevicePairRequest(
                bluetooth_device_id="fake-fr935-offline",
                display_name=None,
            )
        )
        connection = service.test_connection(offline.id)

    assert connection.success is False
    assert connection.status == "failed"
    assert connection.error_code == "WATCH_CONNECTION_FAILED"


def test_sync_service_runs_successful_and_failed_fake_lifecycles(
    tmp_path: Path,
) -> None:
    session_factory = _session_factory(tmp_path, "sync.sqlite3")
    progress_store = SyncProgressStore()

    with session_factory() as session:
        device_service = DeviceService(session)
        online = device_service.pair_device(
            DevicePairRequest(
                bluetooth_device_id="fake-fr935-001",
                display_name=None,
            )
        )
        offline = device_service.pair_device(
            DevicePairRequest(
                bluetooth_device_id="fake-fr935-offline",
                display_name=None,
            )
        )

        sync_service = SyncService(session)
        running = sync_service.start_manual_sync(
            ManualSyncRequest(
                device_id=online.id,
                include_activities=False,
                include_health=True,
            ),
            progress_store,
        )
        plan = progress_store.get_plan(running.id)
        assert plan is not None
        completed = sync_service.finalize_manual_sync(running.id, plan)

        failed_running = sync_service.start_manual_sync(
            ManualSyncRequest(device_id=offline.id),
            progress_store,
        )
        failed_plan = progress_store.get_plan(failed_running.id)
        assert failed_plan is not None
        failed = sync_service.finalize_manual_sync(failed_running.id, failed_plan)

    assert running.status == "running"
    assert completed.status == "succeeded"
    assert completed.activities_imported == 0
    assert completed.health_records_imported == 5
    assert [event.stage for event in plan.events] == [
        "connecting",
        "importing_health",
        "completed",
    ]
    assert failed.status == "failed"
    assert failed.error_summary is not None


def _session_factory(tmp_path: Path, filename: str) -> SessionFactory:
    settings = Settings(database_path=tmp_path / filename)
    engine = create_sqlite_engine(settings)
    Base.metadata.create_all(bind=engine)
    return create_session_factory(engine)
