"""Local desktop-style launcher for RunStats."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

import uvicorn
from alembic import command
from alembic.config import Config

from runstats.config import Settings, get_settings, repository_root


def build_parser() -> argparse.ArgumentParser:
    """Build the local app launcher parser."""

    parser = argparse.ArgumentParser(description="Start the local RunStats app.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    parser.add_argument(
        "--database-path",
        default=None,
        type=Path,
        help="SQLite database path. Defaults to RUNSTATS_DATABASE_PATH.",
    )
    parser.add_argument(
        "--frontend-dist-path",
        default=None,
        type=Path,
        help="Built frontend bundle path. Defaults to frontend/dist.",
    )
    parser.add_argument(
        "--skip-migrations",
        action="store_true",
        help="Start without applying Alembic migrations.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Apply local schema migrations and run the combined app server."""

    args = build_parser().parse_args(argv)
    settings = _settings_from_args(args)
    if not args.skip_migrations:
        upgrade_database(settings)

    from runstats.main import create_app

    uvicorn.run(create_app(settings), host=args.host, port=args.port)
    return 0


def upgrade_database(settings: Settings) -> None:
    """Upgrade the configured SQLite database to the latest schema."""

    settings.ensure_local_directories()
    config = Config(str(_alembic_ini_path()))
    config.set_main_option(
        "script_location",
        str(repository_root() / "backend" / "runstats" / "db" / "migrations"),
    )
    config.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(config, "head")


def _settings_from_args(args: argparse.Namespace) -> Settings:
    current = get_settings()
    return Settings(
        database_path=args.database_path or current.database_path,
        raw_archive_path=current.raw_archive_path,
        frontend_dist_path=args.frontend_dist_path or current.frontend_dist_path,
        watch_provider=current.watch_provider,
        local_chat_base_url=current.local_chat_base_url,
        local_chat_model=current.local_chat_model,
        local_chat_timeout_seconds=current.local_chat_timeout_seconds,
        sync_scheduler_poll_seconds=current.sync_scheduler_poll_seconds,
    )


def _alembic_ini_path() -> Path:
    return repository_root() / "backend" / "alembic.ini"


if __name__ == "__main__":
    raise SystemExit(main())
