"""Command-line entry point for historical FIT folder imports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from runstats.config import Settings, get_settings
from runstats.db.session import create_session_factory, create_sqlite_engine
from runstats.services.import_service import ActivityImportService


def main() -> None:
    """Import a folder of FIT files into the configured local database."""

    parser = argparse.ArgumentParser(description="Import RunStats activity FIT files.")
    parser.add_argument("--device-id", required=True, help="RunStats device UUID.")
    parser.add_argument(
        "--folder-path",
        required=True,
        help="Folder containing historical .fit activity files.",
    )
    parser.add_argument(
        "--database-path",
        type=Path,
        default=None,
        help="Optional SQLite database path. Defaults to RUNSTATS_DATABASE_PATH.",
    )
    parser.add_argument(
        "--raw-archive-path",
        type=Path,
        default=None,
        help="Optional raw archive path. Defaults to RUNSTATS_RAW_ARCHIVE_PATH.",
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Only import .fit files directly inside --folder-path.",
    )
    args = parser.parse_args()

    settings = _settings_for_args(
        database_path=args.database_path,
        raw_archive_path=args.raw_archive_path,
    )
    engine = create_sqlite_engine(settings)
    session_factory = create_session_factory(engine)
    try:
        with session_factory() as session:
            summary = ActivityImportService(session, settings).import_fit_folder(
                device_id=args.device_id,
                folder_path=args.folder_path,
                recursive=not args.no_recursive,
            )
        print(json.dumps(_summary_payload(summary), indent=2))
    finally:
        engine.dispose()


def _settings_for_args(
    *,
    database_path: Path | None,
    raw_archive_path: Path | None,
) -> Settings:
    base_settings = get_settings()
    return Settings(
        database_path=database_path or base_settings.database_path,
        raw_archive_path=raw_archive_path or base_settings.raw_archive_path,
        watch_provider=base_settings.watch_provider,
    )


def _summary_payload(summary: Any) -> dict[str, object]:
    return {
        "created": summary.created,
        "skipped": summary.skipped,
        "failed": summary.failed,
        "raw_files_archived": summary.raw_files_archived,
        "files": [
            {
                "source_id": result.source_id,
                "status": result.status,
                "message": result.message,
                "sha256": result.sha256,
                "activity_id": result.activity_id,
                "raw_import_id": result.raw_import_id,
                "archived": result.archived,
            }
            for result in summary.files
        ],
    }


if __name__ == "__main__":
    main()
