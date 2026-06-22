"""Application configuration."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

WatchProviderName = Literal["bleak", "fake"]


def repository_root() -> Path:
    """Return the repository root inferred from the installed package path."""

    return Path(__file__).resolve().parents[2]


def default_database_path() -> Path:
    """Default local SQLite database path."""

    return repository_root() / "data" / "runstats.sqlite3"


def default_raw_archive_path() -> Path:
    """Default retained raw import archive path."""

    return repository_root() / "data" / "archive" / "raw-imports"


def sqlite_database_url(database_path: Path) -> str:
    """Build a SQLAlchemy SQLite URL for a filesystem path."""

    return URL.create(
        "sqlite+pysqlite",
        database=str(database_path.expanduser()),
    ).render_as_string(hide_password=False)


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_prefix="RUNSTATS_", extra="ignore")

    database_path: Path = Field(default_factory=default_database_path)
    raw_archive_path: Path = Field(default_factory=default_raw_archive_path)
    watch_provider: WatchProviderName = "bleak"

    @property
    def database_url(self) -> str:
        """SQLAlchemy URL for the configured SQLite database."""

        return sqlite_database_url(self.database_path)

    def ensure_local_directories(self) -> None:
        """Create local directories needed before SQLite or archives are used."""

        self.database_path.expanduser().parent.mkdir(parents=True, exist_ok=True)
        self.raw_archive_path.expanduser().mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Return cached runtime settings."""

    return Settings()
