from pathlib import Path

from runstats.config import Settings, sqlite_database_url


def test_settings_loads_database_path_from_environment(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "env-runstats.sqlite3"
    monkeypatch.setenv("RUNSTATS_DATABASE_PATH", str(database_path))

    settings = Settings()

    assert settings.database_path == database_path
    assert settings.database_url == sqlite_database_url(database_path)


def test_settings_loads_watch_provider_from_environment(monkeypatch: object) -> None:
    monkeypatch.setenv("RUNSTATS_WATCH_PROVIDER", "fake")

    settings = Settings()

    assert settings.watch_provider == "fake"


def test_settings_creates_local_directories(tmp_path: Path) -> None:
    settings = Settings(
        database_path=tmp_path / "nested" / "runstats.sqlite3",
        raw_archive_path=tmp_path / "archive" / "raw-imports",
    )

    settings.ensure_local_directories()

    assert settings.database_path.parent.is_dir()
    assert settings.raw_archive_path.is_dir()
