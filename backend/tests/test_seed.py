from pathlib import Path

from sqlalchemy import func, select

from runstats.config import Settings
from runstats.db.models import Activity, Base, Device, HealthMetric
from runstats.db.seed import SEED_DEVICE_ID, seed_development_data
from runstats.db.session import create_session_factory, create_sqlite_engine


def test_seed_development_data_generates_required_records(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)

    with session_factory() as session:
        summary = seed_development_data(session, tmp_path / "archive")
        seeded_device = session.get(Device, SEED_DEVICE_ID)

    assert seeded_device is not None
    assert seeded_device.model == "Forerunner 935"
    assert summary.devices == 1
    assert summary.activities == 3
    assert summary.activity_laps >= 6
    assert summary.activity_samples == 18
    assert summary.health_metrics == 12
    assert summary.raw_imports == 3
    assert summary.sync_runs == 3
    assert summary.chat_sessions == 1
    assert summary.chat_messages == 2


def test_seeded_database_can_answer_summary_queries(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)

    with session_factory() as session:
        seed_development_data(session, tmp_path / "archive")
        total_distance = session.scalar(select(func.sum(Activity.distance_meters)))
        activity_count = session.scalar(select(func.count()).select_from(Activity))
        health_metric_types = set(
            session.scalars(select(HealthMetric.metric_type).distinct()).all()
        )

    assert total_distance == 25220.0
    assert activity_count == 3
    assert health_metric_types == {"steps", "resting_hr", "hrv", "sleep"}


def _session_factory(tmp_path: Path) -> object:
    settings = Settings(database_path=tmp_path / "seed.sqlite3")
    engine = create_sqlite_engine(settings)
    Base.metadata.create_all(bind=engine)
    return create_session_factory(engine)
