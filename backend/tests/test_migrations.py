from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from runstats.config import Settings


def test_initial_migration_creates_all_tables(tmp_path: Path) -> None:
    settings = Settings(database_path=tmp_path / "migrated.sqlite3")
    alembic_config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    alembic_config.attributes["database_url"] = settings.database_url

    command.upgrade(alembic_config, "head")

    engine = create_engine(settings.database_url)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    device_settings_columns = {
        column["name"] for column in inspector.get_columns("device_settings")
    }
    sync_run_columns = {
        column["name"] for column in inspector.get_columns("sync_runs")
    }
    engine.dispose()

    assert {
        "devices",
        "device_settings",
        "device_capabilities",
        "app_settings",
        "sync_runs",
        "activities",
        "activity_laps",
        "activity_samples",
        "health_metrics",
        "raw_imports",
        "chat_sessions",
        "chat_messages",
    }.issubset(tables)
    assert "historical_fit_import_folder" in device_settings_columns
    assert "error_code" in sync_run_columns
