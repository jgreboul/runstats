from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError

from runstats.config import Settings
from runstats.db.models import (
    Activity,
    ActivityLap,
    ActivitySample,
    Base,
    Device,
    DeviceSettings,
)
from runstats.db.session import create_session_factory, create_sqlite_engine


def test_activity_source_is_unique_per_device(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)
    started_at = datetime(2026, 6, 1, 7, 0, tzinfo=UTC)

    with session_factory() as session:
        device = Device(
            id="device-1",
            name="Forerunner",
            model="Forerunner 935",
            bluetooth_address="ble-1",
            settings=DeviceSettings(),
        )
        session.add(device)
        session.add(
            _activity(
                activity_id="activity-1",
                device=device,
                source_activity_id="source-1",
                started_at=started_at,
            )
        )
        session.commit()

        session.add(
            _activity(
                activity_id="activity-2",
                device=device,
                source_activity_id="source-1",
                started_at=started_at,
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()


def test_activity_relationships_preserve_laps_and_samples(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)
    started_at = datetime(2026, 6, 1, 7, 0, tzinfo=UTC)

    with session_factory() as session:
        device = Device(
            id="device-1",
            name="Forerunner",
            model="Forerunner 935",
            bluetooth_address="ble-1",
        )
        activity = _activity(
            activity_id="activity-1",
            device=device,
            source_activity_id="source-1",
            started_at=started_at,
        )
        activity.laps = [
            ActivityLap(
                id="lap-1",
                lap_index=1,
                started_at=started_at,
                duration_seconds=300.0,
                distance_meters=1000.0,
            ),
            ActivityLap(
                id="lap-0",
                lap_index=0,
                started_at=started_at,
                duration_seconds=310.0,
                distance_meters=1000.0,
            ),
        ]
        activity.samples = [
            ActivitySample(
                sample_time=started_at,
                elapsed_seconds=60.0,
            ),
            ActivitySample(
                sample_time=started_at,
                elapsed_seconds=0.0,
            ),
        ]
        session.add(activity)
        session.commit()
        session.expire_all()

        stored = session.get(Activity, "activity-1")
        assert stored is not None
        lap_order = [lap.lap_index for lap in stored.laps]
        sample_order = [sample.elapsed_seconds for sample in stored.samples]

    assert lap_order == [0, 1]
    assert sample_order == [0.0, 60.0]


def _activity(
    *,
    activity_id: str,
    device: Device,
    source_activity_id: str,
    started_at: datetime,
) -> Activity:
    return Activity(
        id=activity_id,
        device=device,
        source_activity_id=source_activity_id,
        sport="running",
        name="Test Run",
        started_at=started_at,
        duration_seconds=1800.0,
        distance_meters=5000.0,
    )


def _session_factory(tmp_path: Path) -> object:
    settings = Settings(database_path=tmp_path / "models.sqlite3")
    engine = create_sqlite_engine(settings)
    Base.metadata.create_all(bind=engine)
    return create_session_factory(engine)
