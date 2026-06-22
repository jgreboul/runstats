from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from runstats.bluetooth import FakeWatchProvider, WatchDiscovery, WatchProviderError
from runstats.config import Settings
from runstats.db.models import Base
from runstats.main import create_app


def test_device_api_scan_pair_list_settings_and_connection(tmp_path: Path) -> None:
    app = _empty_app(tmp_path)

    with TestClient(app) as client:
        scan = client.post("/api/devices/scan", json={"scan_seconds": 5})
        pair = client.post(
            "/api/devices/pair",
            json={
                "bluetooth_device_id": "fake-fr935-001",
                "display_name": "Kitchen Sink Forerunner",
            },
        )
        device_id = pair.json()["id"]
        listed = client.get("/api/devices")
        settings = client.patch(
            f"/api/devices/{device_id}/settings",
            json={
                "auto_sync_enabled": True,
                "sync_interval_minutes": 90,
                "import_activities": True,
                "import_health_stats": False,
                "preferred_units": "imperial",
                "historical_fit_import_folder": "D:/Runs/FIT",
            },
        )
        connection = client.post(f"/api/devices/{device_id}/test-connection")
        probe = client.post(f"/api/devices/{device_id}/probe-capabilities")
        capabilities = client.get(f"/api/devices/{device_id}/capabilities")
        missing = client.patch("/api/devices/not-real/settings", json={})

    assert scan.status_code == 200
    assert any(
        device["name"] == "Garmin Forerunner 935"
        for device in scan.json()["devices"]
    )
    assert pair.status_code == 200
    assert pair.json()["name"] == "Kitchen Sink Forerunner"
    assert pair.json()["capabilities"]["supports_folder_import"] is True
    assert listed.status_code == 200
    assert listed.json()["items"][0]["id"] == device_id
    assert settings.status_code == 200
    assert settings.json()["settings"]["auto_sync_enabled"] is True
    assert settings.json()["settings"]["import_health_stats"] is False
    assert settings.json()["settings"]["preferred_units"] == "imperial"
    assert (
        settings.json()["settings"]["historical_fit_import_folder"] == "D:/Runs/FIT"
    )
    assert connection.status_code == 200
    assert connection.json()["success"] is True
    assert probe.status_code == 200
    assert probe.json()["supports_folder_import"] is True
    assert probe.json()["probed_at"] is not None
    assert capabilities.status_code == 200
    assert capabilities.json() == probe.json()
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "DEVICE_NOT_FOUND"


def test_device_api_connection_failure_from_fake_provider(tmp_path: Path) -> None:
    app = _empty_app(tmp_path)

    with TestClient(app) as client:
        pair = client.post(
            "/api/devices/pair",
            json={"bluetooth_device_id": "fake-fr935-offline"},
        )
        connection = client.post(
            f"/api/devices/{pair.json()['id']}/test-connection"
        )

    assert pair.status_code == 200
    assert connection.status_code == 200
    assert connection.json()["success"] is False
    assert connection.json()["error_code"] == "WATCH_CONNECTION_FAILED"


def test_device_api_maps_provider_scan_errors(tmp_path: Path) -> None:
    app = _empty_app(tmp_path, watch_provider=UnavailableScanProvider())

    with TestClient(app) as client:
        response = client.post("/api/devices/scan", json={"scan_seconds": 5})

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "BLUETOOTH_UNAVAILABLE"
    assert (
        response.json()["error"]["message"]
        == "Bluetooth adapter is unavailable."
    )


def test_sync_api_starts_manual_sync_and_streams_progress(tmp_path: Path) -> None:
    app = _empty_app(tmp_path)

    with TestClient(app) as client:
        pair = client.post(
            "/api/devices/pair",
            json={"bluetooth_device_id": "fake-fr935-001"},
        )
        device_id = pair.json()["id"]
        created = client.post(
            "/api/sync-runs",
            json={
                "device_id": device_id,
                "include_activities": False,
                "include_health": True,
            },
        )
        sync_run_id = created.json()["id"]
        with client.websocket_connect(f"/api/sync-runs/{sync_run_id}/events") as ws:
            events = [ws.receive_json() for _ in range(3)]
        detail = client.get(f"/api/sync-runs/{sync_run_id}")

    assert created.status_code == 201
    assert created.json()["status"] == "running"
    assert [event["stage"] for event in events] == [
        "connecting",
        "importing_health",
        "completed",
    ]
    assert events[-1]["type"] == "completed"
    assert detail.status_code == 200
    assert detail.json()["status"] == "succeeded"
    assert detail.json()["activities_imported"] == 0
    assert detail.json()["health_records_imported"] == 5


class UnavailableScanProvider(FakeWatchProvider):
    def scan(self, timeout_seconds: int = 10) -> list[WatchDiscovery]:
        _ = timeout_seconds
        raise WatchProviderError(
            "BLUETOOTH_UNAVAILABLE",
            "Bluetooth adapter is unavailable.",
            status_code=503,
        )


def _empty_app(
    tmp_path: Path,
    watch_provider: FakeWatchProvider | None = None,
) -> FastAPI:
    settings = Settings(
        database_path=tmp_path / "phase4-api.sqlite3",
        raw_archive_path=tmp_path / "archive",
        watch_provider="fake",
    )
    app = create_app(settings, watch_provider=watch_provider)
    Base.metadata.create_all(bind=app.state.engine)
    return app
