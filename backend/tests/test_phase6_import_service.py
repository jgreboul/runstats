from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from runstats.config import Settings
from runstats.db.models import Activity, AppSettings, Base, RawImport
from runstats.db.session import (
    SessionFactory,
    create_session_factory,
    create_sqlite_engine,
)
from runstats.importers import ParsedActivity
from runstats.schemas import DevicePairRequest
from runstats.services.device_service import DeviceService
from runstats.services.import_service import ActivityImportService
from tests.fit_fixtures import build_activity_fit


def test_activity_import_service_archives_and_persists_fit_file(
    tmp_path: Path,
) -> None:
    settings, session_factory = _session_factory(tmp_path, "import.sqlite3")
    fit_path = tmp_path / "activity.fit"
    fit_path.write_bytes(build_activity_fit())

    with session_factory() as session:
        device_id = _paired_device_id(session)
        result = ActivityImportService(session, settings).import_fit_file(
            device_id=device_id,
            file_path=fit_path,
        )
        duplicate = ActivityImportService(session, settings).import_fit_file(
            device_id=device_id,
            file_path=fit_path,
        )

        activity = session.scalar(select(Activity))
        raw_import = session.scalar(select(RawImport))
        activity_count = session.scalar(select(func.count()).select_from(Activity))
        lap_count = len(activity.laps) if activity is not None else 0
        sample_count = len(activity.samples) if activity is not None else 0

    assert result.status == "created"
    assert result.archived is True
    assert result.raw_import_id is not None
    assert duplicate.status == "skipped"
    assert duplicate.message == "Duplicate raw FIT payload already archived."
    assert activity is not None
    assert activity.name == "activity"
    assert activity.distance_meters == 10_000.0
    assert lap_count == 2
    assert sample_count == 3
    assert raw_import is not None
    assert Path(raw_import.storage_path).exists()
    assert Path(raw_import.storage_path).read_bytes() == fit_path.read_bytes()
    assert activity_count == 1


def test_activity_import_service_uses_persisted_archive_path(
    tmp_path: Path,
) -> None:
    settings, session_factory = _session_factory(tmp_path, "settings-archive.sqlite3")
    configured_archive = tmp_path / "configured-archive"
    fit_path = tmp_path / "activity.fit"
    fit_path.write_bytes(build_activity_fit())

    with session_factory() as session:
        device_id = _paired_device_id(session)
        session.add(
            AppSettings(
                id=1,
                raw_archive_path=str(configured_archive),
                chat_provider="local",
                local_chat_provider="ollama",
                hosted_chat_provider=None,
                chat_retention_policy="retain_until_deleted",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
        session.commit()

        result = ActivityImportService(session, settings).import_fit_file(
            device_id=device_id,
            file_path=fit_path,
        )
        raw_import = session.scalar(select(RawImport))

    assert result.status == "created"
    assert raw_import is not None
    assert Path(raw_import.storage_path).is_relative_to(configured_archive)


def test_activity_import_service_skips_signature_duplicate_without_native_id(
    tmp_path: Path,
) -> None:
    settings, session_factory = _session_factory(tmp_path, "signature.sqlite3")
    first_fit = tmp_path / "first.fit"
    second_fit = tmp_path / "second.fit"
    first_fit.write_bytes(build_activity_fit(include_optional=True))
    second_fit.write_bytes(build_activity_fit(include_optional=False))

    with session_factory() as session:
        device_id = _paired_device_id(session)
        service = ActivityImportService(session, settings)
        first = service.import_fit_file(device_id=device_id, file_path=first_fit)
        second = service.import_fit_file(device_id=device_id, file_path=second_fit)
        activity_count = session.scalar(select(func.count()).select_from(Activity))
        raw_count = session.scalar(select(func.count()).select_from(RawImport))

    assert first.status == "created"
    assert second.status == "skipped"
    assert second.message == "Duplicate activity already imported."
    assert activity_count == 1
    assert raw_count == 1


def test_activity_import_service_rolls_back_failed_activity_write(
    tmp_path: Path,
) -> None:
    settings, session_factory = _session_factory(tmp_path, "rollback.sqlite3")

    with session_factory() as session:
        device_id = _paired_device_id(session)
        result = ActivityImportService(
            session,
            settings,
            parser=InvalidActivityParser(),
        ).import_fit_payload(
            device_id=device_id,
            payload=b"valid enough for invalid parser",
            source_id="invalid.fit",
        )
        activity_count = session.scalar(select(func.count()).select_from(Activity))
        raw_count = session.scalar(select(func.count()).select_from(RawImport))
        archived_files = list(settings.raw_archive_path.rglob("*.fit"))

    assert result.status == "failed"
    assert result.message == "Activity import could not be persisted."
    assert activity_count == 0
    assert raw_count == 0
    assert archived_files == []


class InvalidActivityParser:
    def parse(
        self,
        payload: bytes,
        *,
        sha256: str,
        source_id: str,
        source_name: str | None = None,
    ) -> ParsedActivity:
        _ = payload
        _ = source_name
        return ParsedActivity(
            source_activity_id=f"invalid:{sha256}",
            source_activity_id_kind="checksum",
            sport="running",
            name="Invalid Activity",
            started_at=datetime(2026, 6, 1, tzinfo=UTC),
            duration_seconds=None,
            distance_meters=10_000.0,
            calories=None,
            avg_heart_rate=None,
            max_heart_rate=None,
            avg_cadence=None,
            avg_pace_seconds_per_km=None,
            elevation_gain_meters=None,
            training_effect=None,
            laps=[],
            samples=[],
        )


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
