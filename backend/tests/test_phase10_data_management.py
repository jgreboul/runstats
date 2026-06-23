from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from runstats.bluetooth import FakeWatchProvider
from runstats.config import Settings
from runstats.db.models import (
    Activity,
    Base,
    ChatMessage,
    ChatSession,
    Device,
    HealthMetric,
    RawImport,
)
from runstats.db.seed import SEED_DEVICE_ID, seed_development_data
from runstats.db.session import (
    SessionFactory,
    create_session_factory,
    create_sqlite_engine,
)
from runstats.main import create_app
from runstats.schemas import DataExportRequest
from runstats.services.data_management_service import DataManagementService


def test_data_export_excludes_chat_and_raw_files_by_default(
    tmp_path: Path,
) -> None:
    session_factory = _seeded_session_factory(tmp_path)

    with session_factory() as session:
        counts_before = _counts(session)
        export = DataManagementService(session).export_data(DataExportRequest())
        counts_after = _counts(session)

    assert export.format_version == "runstats.local-data.v1"
    assert export.include_chat_history is False
    assert export.include_raw_files is False
    assert export.counts.activities == 3
    assert export.counts.health_metrics == 12
    assert export.counts.chat_sessions == 0
    assert export.chat_sessions == []
    assert export.raw_files == []
    assert export.activities[0].laps
    assert export.activities[0].samples
    assert counts_after == counts_before


def test_data_export_includes_raw_files_and_chat_only_when_requested(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "archive"
    session_factory = _seeded_session_factory(tmp_path, archive_path)
    raw_payload = b"raw-fit-bytes"
    archived_file = archive_path / "2026-06-01-morning-5k.fit"
    archived_file.parent.mkdir(parents=True, exist_ok=True)
    archived_file.write_bytes(raw_payload)

    with session_factory() as session:
        export = DataManagementService(session).export_data(
            DataExportRequest(include_raw_files=True, include_chat_history=True)
        )

    assert export.include_chat_history is True
    assert export.include_raw_files is True
    assert export.counts.chat_sessions == 1
    assert export.counts.chat_messages == 2
    assert export.chat_sessions[0].messages[0].content.startswith("How much")
    included_files = [raw_file for raw_file in export.raw_files if raw_file.included]
    assert len(included_files) == 1
    assert included_files[0].content_base64 == "cmF3LWZpdC1ieXRlcw=="
    assert export.counts.raw_files == 1


def test_data_management_deletes_chat_history_and_device_imported_data(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "archive"
    session_factory = _seeded_session_factory(tmp_path, archive_path)
    archived_file = archive_path / "2026-06-01-morning-5k.fit"
    archived_file.parent.mkdir(parents=True, exist_ok=True)
    archived_file.write_bytes(b"raw-fit-bytes")

    with session_factory() as session:
        service = DataManagementService(session)
        chat_deleted = service.delete_chat_history()
        data_deleted = service.delete_imported_data_for_device(SEED_DEVICE_ID)

        assert session.get(Device, SEED_DEVICE_ID) is not None
        assert _count(session, Activity) == 0
        assert _count(session, HealthMetric) == 0
        assert _count(session, RawImport) == 0
        assert _count(session, ChatSession) == 0
        assert _count(session, ChatMessage) == 0

    assert chat_deleted.deleted_chat_sessions == 1
    assert chat_deleted.deleted_chat_messages == 2
    assert data_deleted.deleted_activities == 3
    assert data_deleted.deleted_activity_laps >= 6
    assert data_deleted.deleted_activity_samples == 18
    assert data_deleted.deleted_health_metrics == 12
    assert data_deleted.deleted_raw_imports == 3
    assert data_deleted.deleted_raw_files == 1
    assert archived_file.exists() is False


def test_data_management_api_exports_and_deletes(tmp_path: Path) -> None:
    app = _seeded_app(tmp_path)

    with TestClient(app) as client:
        export = client.post(
            "/api/data-management/export",
            json={"include_raw_files": False, "include_chat_history": False},
        )
        chat_deleted = client.delete("/api/data-management/chat-history")
        device_deleted = client.delete(
            f"/api/data-management/devices/{SEED_DEVICE_ID}/imported-data"
        )
        missing = client.delete(
            "/api/data-management/devices/not-real/imported-data"
        )

    assert export.status_code == 200
    assert export.json()["counts"]["activities"] == 3
    assert export.json()["chat_sessions"] == []
    assert chat_deleted.status_code == 200
    assert chat_deleted.json()["deleted_chat_sessions"] == 1
    assert device_deleted.status_code == 200
    assert device_deleted.json()["deleted_health_metrics"] == 12
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "DEVICE_NOT_FOUND"


def _seeded_app(tmp_path: Path) -> FastAPI:
    settings = Settings(
        database_path=tmp_path / "api.sqlite3",
        raw_archive_path=tmp_path / "archive",
        watch_provider="fake",
        frontend_dist_path=tmp_path / "missing-dist",
    )
    app = create_app(settings, watch_provider=FakeWatchProvider())
    Base.metadata.create_all(bind=app.state.engine)
    session_factory = app.state.session_factory
    with session_factory() as session:
        seed_development_data(session, settings.raw_archive_path)
    return app


def _seeded_session_factory(
    tmp_path: Path,
    raw_archive_path: Path | None = None,
) -> SessionFactory:
    settings = Settings(
        database_path=tmp_path / "seeded.sqlite3",
        raw_archive_path=raw_archive_path or tmp_path / "archive",
        frontend_dist_path=tmp_path / "missing-dist",
    )
    engine = create_sqlite_engine(settings)
    Base.metadata.create_all(bind=engine)
    session_factory = create_session_factory(engine)
    with session_factory() as session:
        seed_development_data(session, settings.raw_archive_path)
    return session_factory


def _counts(session: object) -> dict[str, int]:
    return {
        "activities": _count(session, Activity),
        "health_metrics": _count(session, HealthMetric),
        "raw_imports": _count(session, RawImport),
        "chat_sessions": _count(session, ChatSession),
        "chat_messages": _count(session, ChatMessage),
    }


def _count(session: object, model: type[Base]) -> int:
    count = session.scalar(select(func.count()).select_from(model))
    return int(count or 0)
