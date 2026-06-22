from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from runstats.config import Settings
from runstats.db.models import Base
from runstats.main import create_app
from tests.fit_fixtures import build_activity_fit


def test_fit_folder_import_api_imports_and_lists_activities(
    tmp_path: Path,
) -> None:
    app = _empty_app(tmp_path)
    import_folder = tmp_path / "fit-files"
    import_folder.mkdir()
    (import_folder / "morning-10k.fit").write_bytes(build_activity_fit())
    (import_folder / "broken.fit").write_bytes(b"not a fit file")

    with TestClient(app) as client:
        pair = client.post(
            "/api/devices/pair",
            json={"bluetooth_device_id": "fake-fr935-001"},
        )
        device_id = pair.json()["id"]
        imported = client.post(
            "/api/imports/fit-folder",
            json={
                "device_id": device_id,
                "folder_path": str(import_folder),
                "recursive": True,
            },
        )
        activities = client.get("/api/activities")

    assert imported.status_code == 200
    assert imported.json()["created"] == 1
    assert imported.json()["skipped"] == 0
    assert imported.json()["failed"] == 1
    assert imported.json()["raw_files_archived"] == 1
    assert len(imported.json()["files"]) == 2
    assert activities.status_code == 200
    assert activities.json()["total"] == 1
    assert activities.json()["items"][0]["name"] == "morning-10k"


def test_fit_folder_import_api_rejects_missing_folder(tmp_path: Path) -> None:
    app = _empty_app(tmp_path)

    with TestClient(app) as client:
        pair = client.post(
            "/api/devices/pair",
            json={"bluetooth_device_id": "fake-fr935-001"},
        )
        response = client.post(
            "/api/imports/fit-folder",
            json={
                "device_id": pair.json()["id"],
                "folder_path": str(tmp_path / "missing"),
                "recursive": True,
            },
        )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "FIT_FOLDER_NOT_FOUND"


def _empty_app(tmp_path: Path) -> FastAPI:
    settings = Settings(
        database_path=tmp_path / "phase6-api.sqlite3",
        raw_archive_path=tmp_path / "archive",
        watch_provider="fake",
    )
    app = create_app(settings)
    Base.metadata.create_all(bind=app.state.engine)
    return app
