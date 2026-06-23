from pathlib import Path

from runstats.config import Settings, repository_root, sqlite_database_url


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


def test_settings_loads_frontend_dist_path_from_environment(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    frontend_dist_path = tmp_path / "dist"
    monkeypatch.setenv("RUNSTATS_FRONTEND_DIST_PATH", str(frontend_dist_path))

    settings = Settings()

    assert settings.frontend_dist_path == frontend_dist_path


def test_settings_loads_values_from_root_env_file(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    env_file = tmp_path / ".env"
    database_path = tmp_path / "real-device.sqlite3"
    env_file.write_text(
        "\n".join(
            [
                f"RUNSTATS_DATABASE_PATH={database_path}",
                "RUNSTATS_WATCH_PROVIDER=bleak",
                "RUNSTATS_LOCAL_CHAT_MODEL=gemma2",
            ]
        ),
    )
    (tmp_path / "backend").mkdir(exist_ok=True)
    monkeypatch.chdir(tmp_path / "backend")

    settings = Settings()

    assert settings.database_path == database_path
    assert settings.watch_provider == "bleak"
    assert settings.local_chat_model == "gemma2"


def test_settings_resolves_relative_paths_from_repository_root() -> None:
    settings = Settings(
        database_path=Path("data/relative.sqlite3"),
        raw_archive_path=Path("data/archive/relative"),
        frontend_dist_path=Path("frontend/dist"),
    )

    assert settings.database_path == repository_root() / "data" / "relative.sqlite3"
    assert settings.raw_archive_path == (
        repository_root() / "data" / "archive" / "relative"
    )
    assert settings.frontend_dist_path == repository_root() / "frontend" / "dist"


def test_settings_creates_local_directories(tmp_path: Path) -> None:
    settings = Settings(
        database_path=tmp_path / "nested" / "runstats.sqlite3",
        raw_archive_path=tmp_path / "archive" / "raw-imports",
    )

    settings.ensure_local_directories()

    assert settings.database_path.parent.is_dir()
    assert settings.raw_archive_path.is_dir()
