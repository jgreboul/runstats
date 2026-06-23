"""Run a seeded local server for Playwright end-to-end tests."""

from __future__ import annotations

import os
from pathlib import Path
from shutil import rmtree

import uvicorn

from runstats.bluetooth import FakeWatchProvider
from runstats.chat.fake import FakeChatProvider
from runstats.config import Settings, repository_root
from runstats.db.seed import seed_development_data
from runstats.db.session import create_session_factory, create_sqlite_engine
from runstats.local_app import upgrade_database
from runstats.main import create_app

HOST = "127.0.0.1"
PORT = int(os.environ.get("RUNSTATS_E2E_PORT", "8765"))


def main() -> int:
    """Prepare deterministic local data and run the test server."""

    root = repository_root()
    database_path = root / "data" / "e2e.sqlite3"
    raw_archive_path = root / "data" / "e2e-archive"
    frontend_dist_path = root / "frontend" / "dist"
    _reset_local_test_data(database_path, raw_archive_path, root / "data")

    settings = Settings(
        database_path=database_path,
        raw_archive_path=raw_archive_path,
        frontend_dist_path=frontend_dist_path,
        watch_provider="fake",
    )
    upgrade_database(settings)
    engine = create_sqlite_engine(settings)
    session_factory = create_session_factory(engine)
    with session_factory() as session:
        seed_development_data(session, raw_archive_path)
    engine.dispose()

    app = create_app(
        settings,
        watch_provider=FakeWatchProvider(),
        chat_response_provider=FakeChatProvider(),
    )
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")
    return 0


def _reset_local_test_data(
    database_path: Path,
    raw_archive_path: Path,
    data_root: Path,
) -> None:
    data_root.mkdir(parents=True, exist_ok=True)
    for path in (
        database_path,
        database_path.with_name(f"{database_path.name}-wal"),
        database_path.with_name(f"{database_path.name}-shm"),
    ):
        _remove_file_inside(path, data_root)
    _remove_directory_inside(raw_archive_path, data_root)


def _remove_file_inside(path: Path, root: Path) -> None:
    resolved_path = path.resolve()
    resolved_root = root.resolve()
    if not _is_relative_to(resolved_path, resolved_root):
        raise RuntimeError(f"Refusing to remove path outside data root: {path}")
    resolved_path.unlink(missing_ok=True)


def _remove_directory_inside(path: Path, root: Path) -> None:
    resolved_path = path.resolve()
    resolved_root = root.resolve()
    if not _is_relative_to(resolved_path, resolved_root):
        raise RuntimeError(f"Refusing to remove path outside data root: {path}")
    if resolved_path.exists():
        rmtree(resolved_path)


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


if __name__ == "__main__":
    raise SystemExit(main())
