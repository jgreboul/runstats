from pathlib import Path

from sqlalchemy import text

from runstats.config import Settings
from runstats.db.models import AppSettings, Base
from runstats.db.session import create_session_factory, create_sqlite_engine


def test_database_session_lifecycle_uses_isolated_sqlite(tmp_path: Path) -> None:
    settings = Settings(database_path=tmp_path / "isolated.sqlite3")
    engine = create_sqlite_engine(settings)
    Base.metadata.create_all(bind=engine)
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        session.add(
            AppSettings(
                id=1,
                raw_archive_path=str(tmp_path / "archive"),
            )
        )
        session.commit()

    with session_factory() as session:
        stored = session.get(AppSettings, 1)
        journal_mode = session.execute(text("PRAGMA journal_mode")).scalar_one()

    engine.dispose()

    assert stored is not None
    assert stored.raw_archive_path == str(tmp_path / "archive")
    assert str(journal_mode).lower() == "wal"
