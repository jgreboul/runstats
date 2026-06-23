"""Deterministic development seed data."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from runstats.config import Settings, default_raw_archive_path, get_settings
from runstats.db.models import (
    Activity,
    ActivityLap,
    ActivitySample,
    AppSettings,
    Base,
    ChatMessage,
    ChatSession,
    Device,
    DeviceCapabilities,
    DeviceSettings,
    HealthMetric,
    RawImport,
    SyncRun,
)
from runstats.db.session import create_session_factory, create_sqlite_engine

SEED_DEVICE_ID = "seed-device-forerunner-935"
SEED_CHAT_SESSION_ID = "seed-chat-session-training-summary"


@dataclass(frozen=True)
class SeedSummary:
    """Counts produced by the seed data command."""

    devices: int
    activities: int
    activity_laps: int
    activity_samples: int
    health_metrics: int
    raw_imports: int
    sync_runs: int
    chat_sessions: int
    chat_messages: int


def seed_development_data(
    session: Session,
    raw_archive_path: Path | None = None,
) -> SeedSummary:
    """Insert deterministic development data if it is not already present."""

    if session.get(Device, SEED_DEVICE_ID) is not None:
        return summarize_seeded_data(session)

    archive_path = raw_archive_path or default_raw_archive_path()
    base_time = datetime(2026, 6, 1, 6, 30, tzinfo=UTC)

    device = Device(
        id=SEED_DEVICE_ID,
        name="Garmin Forerunner 935",
        model="Forerunner 935",
        bluetooth_address="seed-ble-forerunner-935",
        serial_number="FR935-SEED-001",
        firmware_version="21.00",
        paired_at=base_time - timedelta(days=10),
        last_seen_at=base_time + timedelta(days=14, hours=1),
        created_at=base_time - timedelta(days=10),
        updated_at=base_time + timedelta(days=14, hours=1),
    )
    device.settings = DeviceSettings(
        auto_sync_enabled=True,
        sync_interval_minutes=180,
        import_activities=True,
        import_health_stats=True,
        preferred_units="metric",
    )
    device.capabilities = DeviceCapabilities(
        supports_ble_activity_export=False,
        supports_ble_health_export=False,
        supports_folder_import=True,
        capability_notes=(
            "Seeded Forerunner 935 uses folder import until BLE export is verified."
        ),
        probed_at=base_time - timedelta(days=2),
    )

    app_settings = AppSettings(
        id=1,
        raw_archive_path=str(archive_path),
        chat_provider="local",
        local_chat_provider="ollama",
        hosted_chat_provider=None,
        chat_retention_policy="retain_until_deleted",
        created_at=base_time - timedelta(days=10),
        updated_at=base_time - timedelta(days=10),
    )

    raw_imports = [
        RawImport(
            id="seed-raw-run-001",
            device=device,
            source_id="2026-06-01-morning-5k.fit",
            kind="activity_fit",
            sha256="0" * 64,
            storage_path=str(archive_path / "2026-06-01-morning-5k.fit"),
            imported_at=base_time + timedelta(hours=1),
        ),
        RawImport(
            id="seed-raw-run-002",
            device=device,
            source_id="2026-06-08-tempo-8k.fit",
            kind="activity_fit",
            sha256="1" * 64,
            storage_path=str(archive_path / "2026-06-08-tempo-8k.fit"),
            imported_at=base_time + timedelta(days=7, hours=1),
        ),
        RawImport(
            id="seed-raw-run-003",
            device=device,
            source_id="2026-06-15-long-run.fit",
            kind="activity_fit",
            sha256="2" * 64,
            storage_path=str(archive_path / "2026-06-15-long-run.fit"),
            imported_at=base_time + timedelta(days=14, hours=1),
        ),
    ]

    activities = [
        _build_activity(
            device=device,
            raw_import=raw_imports[0],
            activity_id="seed-activity-001",
            source_activity_id="garmin-seed-001",
            name="Morning 5K",
            started_at=base_time,
            distance_meters=5020.0,
            duration_seconds=1545.0,
            avg_heart_rate=142,
            max_heart_rate=164,
            avg_cadence=166.0,
            elevation_gain_meters=24.0,
            training_effect=2.4,
            lap_distances=[1000.0, 1000.0, 1000.0, 1000.0, 1020.0],
        ),
        _build_activity(
            device=device,
            raw_import=raw_imports[1],
            activity_id="seed-activity-002",
            source_activity_id="garmin-seed-002",
            name="Tempo 8K",
            started_at=base_time + timedelta(days=7),
            distance_meters=8040.0,
            duration_seconds=2380.0,
            avg_heart_rate=151,
            max_heart_rate=176,
            avg_cadence=172.0,
            elevation_gain_meters=38.0,
            training_effect=3.1,
            lap_distances=[1000.0] * 8,
        ),
        _build_activity(
            device=device,
            raw_import=raw_imports[2],
            activity_id="seed-activity-003",
            source_activity_id="garmin-seed-003",
            name="Sunday Long Run",
            started_at=base_time + timedelta(days=14),
            distance_meters=12160.0,
            duration_seconds=3965.0,
            avg_heart_rate=146,
            max_heart_rate=169,
            avg_cadence=168.0,
            elevation_gain_meters=86.0,
            training_effect=3.5,
            lap_distances=[2000.0] * 6,
        ),
    ]

    health_metrics = _build_health_metrics(device, base_time)
    sync_runs = [
        SyncRun(
            id="seed-sync-001",
            device=device,
            status="succeeded",
            started_at=base_time + timedelta(days=7, hours=2),
            finished_at=base_time + timedelta(days=7, hours=2, minutes=2),
            activities_imported=2,
            health_records_imported=6,
            error_code=None,
            error_message=None,
        ),
        SyncRun(
            id="seed-sync-002",
            device=device,
            status="failed",
            started_at=base_time + timedelta(days=13, hours=20),
            finished_at=base_time + timedelta(days=13, hours=20, minutes=1),
            activities_imported=0,
            health_records_imported=0,
            error_code="WATCH_EXPORT_FAILED",
            error_message=(
                "Seeded Bluetooth export unavailable; folder import required."
            ),
        ),
        SyncRun(
            id="seed-sync-003",
            device=device,
            status="succeeded",
            started_at=base_time + timedelta(days=14, hours=2),
            finished_at=base_time + timedelta(days=14, hours=2, minutes=3),
            activities_imported=1,
            health_records_imported=6,
            error_code=None,
            error_message=None,
        ),
    ]
    chat_session = ChatSession(
        id=SEED_CHAT_SESSION_ID,
        title="Seed training questions",
        created_at=base_time + timedelta(days=14, hours=4),
        updated_at=base_time + timedelta(days=14, hours=4, minutes=1),
    )
    chat_session.messages = [
        ChatMessage(
            id="seed-chat-message-001",
            role="user",
            content="How much did I run in the seeded data?",
            created_at=base_time + timedelta(days=14, hours=4),
        ),
        ChatMessage(
            id="seed-chat-message-002",
            role="assistant",
            content="The seeded data contains 25.22 km across 3 runs.",
            tool_trace_json=(
                '{"intent":"weekly_running_summary","row_count":3,'
                '"metrics":["distance_meters"]}'
            ),
            created_at=base_time + timedelta(days=14, hours=4, minutes=1),
        ),
    ]

    session.add(device)
    session.merge(app_settings)
    session.add_all(raw_imports)
    session.add_all(activities)
    session.add_all(health_metrics)
    session.add_all(sync_runs)
    session.add(chat_session)
    session.commit()
    return summarize_seeded_data(session)


def summarize_seeded_data(session: Session) -> SeedSummary:
    """Return counts for the current database."""

    return SeedSummary(
        devices=_count(session, Device),
        activities=_count(session, Activity),
        activity_laps=_count(session, ActivityLap),
        activity_samples=_count(session, ActivitySample),
        health_metrics=_count(session, HealthMetric),
        raw_imports=_count(session, RawImport),
        sync_runs=_count(session, SyncRun),
        chat_sessions=_count(session, ChatSession),
        chat_messages=_count(session, ChatMessage),
    )


def _count(session: Session, model: type[Base]) -> int:
    count_value = session.scalar(select(func.count()).select_from(model))
    return int(count_value or 0)


def _build_activity(
    *,
    device: Device,
    raw_import: RawImport,
    activity_id: str,
    source_activity_id: str,
    name: str,
    started_at: datetime,
    distance_meters: float,
    duration_seconds: float,
    avg_heart_rate: int,
    max_heart_rate: int,
    avg_cadence: float,
    elevation_gain_meters: float,
    training_effect: float,
    lap_distances: list[float],
) -> Activity:
    pace = duration_seconds / (distance_meters / 1000.0)
    activity = Activity(
        id=activity_id,
        device=device,
        raw_import=raw_import,
        source_activity_id=source_activity_id,
        sport="running",
        name=name,
        started_at=started_at,
        duration_seconds=duration_seconds,
        distance_meters=distance_meters,
        calories=int(distance_meters / 1000.0 * 68),
        avg_heart_rate=avg_heart_rate,
        max_heart_rate=max_heart_rate,
        avg_cadence=avg_cadence,
        avg_pace_seconds_per_km=pace,
        elevation_gain_meters=elevation_gain_meters,
        training_effect=training_effect,
        created_at=started_at + timedelta(hours=1),
    )

    elapsed = 0.0
    distance = 0.0
    for lap_index, lap_distance in enumerate(lap_distances):
        lap_duration = duration_seconds * (lap_distance / distance_meters)
        activity.laps.append(
            ActivityLap(
                id=f"{activity_id}-lap-{lap_index}",
                lap_index=lap_index,
                started_at=started_at + timedelta(seconds=elapsed),
                duration_seconds=lap_duration,
                distance_meters=lap_distance,
                avg_heart_rate=avg_heart_rate + min(lap_index, 4),
                avg_pace_seconds_per_km=lap_duration / (lap_distance / 1000.0),
            )
        )
        elapsed += lap_duration
        distance += lap_distance

    sample_count = 6
    for sample_index in range(sample_count):
        ratio = sample_index / (sample_count - 1)
        activity.samples.append(
            ActivitySample(
                sample_time=started_at + timedelta(seconds=duration_seconds * ratio),
                elapsed_seconds=duration_seconds * ratio,
                distance_meters=distance_meters * ratio,
                latitude=47.6205 + (0.004 * ratio),
                longitude=-122.3493 - (0.004 * ratio),
                elevation_meters=42.0 + (elevation_gain_meters * ratio),
                heart_rate=avg_heart_rate + int(8 * ratio),
                cadence=avg_cadence + (2.0 * ratio),
                power_watts=220.0 + (15.0 * ratio),
                speed_meters_per_second=distance_meters / duration_seconds,
            )
        )

    if abs(distance - distance_meters) > 250.0:
        raise ValueError("Seed lap distances are not representative.")

    return activity


def _build_health_metrics(device: Device, base_time: datetime) -> list[HealthMetric]:
    metrics: list[HealthMetric] = []
    daily_values = [
        ("steps", 8420.0, "count"),
        ("resting_hr", 52.0, "bpm"),
        ("hrv", 61.0, "ms"),
        ("sleep", 7.4, "hours"),
    ]
    for day_index in range(3):
        day_start = base_time.date() + timedelta(days=day_index * 7)
        start_time = datetime.combine(day_start, datetime.min.time(), tzinfo=UTC)
        end_time = start_time + timedelta(days=1)
        for metric_index, (metric_type, value, unit) in enumerate(daily_values):
            metrics.append(
                HealthMetric(
                    device=device,
                    metric_type=metric_type,
                    start_time=start_time,
                    end_time=end_time,
                    value=value + day_index * (metric_index + 1),
                    unit=unit,
                    source_record_id=(f"seed-health-{metric_type}-{day_index:02d}"),
                )
            )
    return metrics


def build_parser() -> argparse.ArgumentParser:
    """Build the seed command parser."""

    parser = argparse.ArgumentParser(description="Seed a RunStats SQLite database.")
    parser.add_argument(
        "--database-path",
        type=Path,
        default=None,
        help="SQLite database path. Defaults to RUNSTATS_DATABASE_PATH or data/.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Seed a local development database."""

    args = build_parser().parse_args(argv)
    settings = get_settings()
    if args.database_path is not None:
        settings = Settings(
            database_path=args.database_path,
            raw_archive_path=settings.raw_archive_path,
        )

    engine = create_sqlite_engine(settings)
    Base.metadata.create_all(bind=engine)
    session_factory = create_session_factory(engine)
    with session_factory() as session:
        summary = seed_development_data(session, settings.raw_archive_path)

    print(json.dumps(asdict(summary), sort_keys=True))
    engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
