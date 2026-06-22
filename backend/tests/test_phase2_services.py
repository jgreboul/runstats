from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from runstats.config import Settings
from runstats.db.models import (
    Activity,
    AppSettings,
    Base,
    Device,
    HealthMetric,
)
from runstats.db.seed import seed_development_data
from runstats.db.session import (
    SessionFactory,
    create_session_factory,
    create_sqlite_engine,
)
from runstats.schemas import AppSettingsPatchRequest
from runstats.services.activity_service import ActivityFilters, ActivityService
from runstats.services.analytics_service import AnalyticsService
from runstats.services.health_service import HealthService
from runstats.services.settings_service import SettingsService
from runstats.services.sync_service import SyncService, safe_error_summary


def test_activity_service_filters_and_derives_values(tmp_path: Path) -> None:
    session_factory = _seeded_session_factory(tmp_path)

    with session_factory() as session:
        service = ActivityService(session)
        result = service.list_activities(
            filters=ActivityFilters(
                sport="running",
                min_distance_meters=8000.0,
            ),
            limit=1,
            offset=0,
        )
        detail = service.get_activity("seed-activity-001")
        samples = service.get_activity_samples("seed-activity-001")
        summary = service.summarize_activities(bucket="week")

    assert result.total == 2
    assert len(result.items) == 1
    assert result.items[0].name == "Sunday Long Run"
    assert detail.summary.lap_count == 5
    assert detail.summary.sample_count == 6
    assert detail.summary.has_gps is True
    assert detail.summary.avg_speed_meters_per_second == pytest.approx(
        5020.0 / 1545.0
    )
    assert [sample.elapsed_seconds for sample in samples.samples] == sorted(
        sample.elapsed_seconds for sample in samples.samples
    )
    assert summary.total_activities == 3
    assert summary.total_distance_meters == 25220.0
    assert len(summary.buckets) == 3


def test_activity_service_derives_missing_pace(tmp_path: Path) -> None:
    session_factory = _seeded_session_factory(tmp_path)
    started_at = datetime(2026, 6, 20, 8, 0, tzinfo=UTC)

    with session_factory() as session:
        device = session.get(Device, "seed-device-forerunner-935")
        assert device is not None
        session.add(
            Activity(
                id="derived-pace-run",
                device=device,
                source_activity_id="derived-pace-source",
                sport="running",
                name="Derived Pace Run",
                started_at=started_at,
                duration_seconds=300.0,
                distance_meters=1000.0,
                avg_pace_seconds_per_km=None,
            )
        )
        session.commit()
        detail = ActivityService(session).get_activity("derived-pace-run")

    assert detail.avg_pace_seconds_per_km == 300.0
    assert detail.summary.avg_pace_seconds_per_km == 300.0


def test_health_service_discovers_metrics_and_aggregates_series(
    tmp_path: Path,
) -> None:
    session_factory = _seeded_session_factory(tmp_path)

    with session_factory() as session:
        service = HealthService(session)
        metrics = service.list_metrics()
        steps = service.get_series(metric_type="steps", bucket="month")
        ranged_resting_hr = service.get_series(
            metric_type="resting_hr",
            start_at=datetime(2026, 6, 8, 0, 0, tzinfo=UTC),
            end_at=datetime(2026, 6, 9, 0, 0, tzinfo=UTC),
            bucket="week",
        )
        missing = service.get_series(metric_type="body_battery", bucket="week")

    assert {metric.metric_type for metric in metrics.metrics} == {
        "hrv",
        "resting_hr",
        "sleep",
        "steps",
    }
    assert steps.metric_available is True
    assert steps.points[0].value == 8420.0 + 8421.0 + 8422.0
    assert steps.points[0].record_count == 3
    assert len(ranged_resting_hr.points) == 1
    assert ranged_resting_hr.points[0].value == 54.0
    assert missing.metric_available is False
    assert missing.points == []
    assert missing.message is not None


def test_sync_service_serializes_history_and_safe_errors(tmp_path: Path) -> None:
    session_factory = _seeded_session_factory(tmp_path)

    with session_factory() as session:
        service = SyncService(session)
        result = service.list_sync_runs(limit=2)
        failed = service.get_sync_run("seed-sync-002")

    assert result.total == 3
    assert [run.id for run in result.items] == ["seed-sync-003", "seed-sync-002"]
    assert failed.status == "failed"
    assert failed.duration_seconds == 60.0
    assert failed.error_summary == (
        "Seeded Bluetooth export unavailable; folder import required."
    )
    assert safe_error_summary("Traceback:\nsecret stack trace") == (
        "A sync failure occurred. Check local logs for technical detail."
    )


def test_analytics_service_returns_running_summaries_and_rankings(
    tmp_path: Path,
) -> None:
    session_factory = _seeded_session_factory(tmp_path)

    with session_factory() as session:
        service = AnalyticsService(session)
        weekly = service.weekly_running_summary()
        monthly = service.monthly_running_summary()
        fastest = service.fastest_runs_by_distance_threshold(
            min_distance_meters=5000.0
        )
        longest = service.longest_runs()
        pace_trend = service.pace_trend()
        heart_rate_trend = service.heart_rate_trend()

    assert weekly.total_activities == 3
    assert len(weekly.buckets) == 3
    assert monthly.total_distance_meters == 25220.0
    assert len(monthly.buckets) == 1
    assert fastest.items[0].name == "Tempo 8K"
    assert longest.items[0].name == "Sunday Long Run"
    assert pace_trend.points[0].value == pytest.approx(1545.0 / 5.02)
    assert heart_rate_trend.points[0].value == 142.0


def test_analytics_service_compares_health_metrics_and_empty_data(
    tmp_path: Path,
) -> None:
    session_factory = _seeded_session_factory(tmp_path)
    first_day = datetime(2026, 6, 1, 0, 0, tzinfo=UTC)
    second_day = datetime(2026, 6, 8, 0, 0, tzinfo=UTC)

    with session_factory() as session:
        service = AnalyticsService(session)
        comparison = service.health_metric_comparison(
            metric_type="steps",
            baseline_start_at=first_day,
            baseline_end_at=first_day + timedelta(hours=23, minutes=59),
            comparison_start_at=second_day,
            comparison_end_at=second_day + timedelta(hours=23, minutes=59),
        )

    empty_factory = _session_factory(tmp_path, "empty-analytics.sqlite3")
    with empty_factory() as session:
        empty_summary = AnalyticsService(session).weekly_running_summary()

    assert comparison.aggregation == "sum"
    assert comparison.baseline.value == 8420.0
    assert comparison.comparison.value == 8421.0
    assert comparison.delta_value == 1.0
    assert empty_summary.total_activities == 0
    assert empty_summary.buckets == []


def test_analytics_service_handles_partial_activity_data(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path, "partial-analytics.sqlite3")
    started_at = datetime(2026, 6, 1, 7, 0, tzinfo=UTC)

    with session_factory() as session:
        device = Device(
            id="partial-device",
            name="Partial Device",
            model="Forerunner 935",
            bluetooth_address="partial-ble",
        )
        session.add(device)
        session.add(
            Activity(
                id="partial-run",
                device=device,
                source_activity_id="partial-source",
                sport="running",
                name="Partial Run",
                started_at=started_at,
                duration_seconds=1800.0,
                distance_meters=5000.0,
                avg_heart_rate=None,
            )
        )
        session.commit()
        trend = AnalyticsService(session).heart_rate_trend()

    assert len(trend.points) == 1
    assert trend.points[0].value is None
    assert trend.points[0].record_count == 0


def test_analytics_service_marks_mixed_health_units(tmp_path: Path) -> None:
    session_factory = _seeded_session_factory(tmp_path)
    first_day = datetime(2026, 6, 1, 0, 0, tzinfo=UTC)
    second_day = datetime(2026, 6, 8, 0, 0, tzinfo=UTC)

    with session_factory() as session:
        device = session.get(Device, "seed-device-forerunner-935")
        assert device is not None
        session.add(
            HealthMetric(
                device=device,
                metric_type="hrv",
                start_time=second_day + timedelta(hours=1),
                end_time=None,
                value=0.061,
                unit="seconds",
                source_record_id="mixed-unit-hrv",
            )
        )
        session.commit()
        comparison = AnalyticsService(session).health_metric_comparison(
            metric_type="hrv",
            baseline_start_at=first_day,
            baseline_end_at=first_day + timedelta(hours=23, minutes=59),
            comparison_start_at=second_day,
            comparison_end_at=second_day + timedelta(hours=23, minutes=59),
        )

    assert comparison.unit == "mixed"


def test_settings_service_defaults_updates_and_validation(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path, "settings.sqlite3")
    runtime_settings = Settings(
        database_path=tmp_path / "settings.sqlite3",
        raw_archive_path=tmp_path / "archive",
    )

    with session_factory() as session:
        service = SettingsService(session, runtime_settings)
        defaults = service.get_settings()
        updated = service.update_settings(
            AppSettingsPatchRequest(
                chat_provider="disabled",
                chat_retention_policy="do_not_retain",
            )
        )
        stored = session.get(AppSettings, 1)

    assert defaults.raw_archive_path == str(tmp_path / "archive")
    assert defaults.chat_provider == "local"
    assert defaults.local_chat_provider == "ollama"
    assert defaults.chat_retention_policy == "retain_until_deleted"
    assert updated.chat_provider == "disabled"
    assert updated.chat_retention_policy == "do_not_retain"
    assert stored is not None
    assert stored.chat_provider == "disabled"
    with pytest.raises(ValidationError):
        AppSettingsPatchRequest.model_validate({"chat_provider": "invalid"})
    with pytest.raises(ValidationError):
        AppSettingsPatchRequest.model_validate(
            {"chat_retention_policy": "retain_forever"}
        )


def _seeded_session_factory(tmp_path: Path) -> SessionFactory:
    session_factory = _session_factory(tmp_path, "seeded.sqlite3")
    with session_factory() as session:
        seed_development_data(session, tmp_path / "archive")
    return session_factory


def _session_factory(tmp_path: Path, filename: str) -> SessionFactory:
    settings = Settings(database_path=tmp_path / filename)
    engine = create_sqlite_engine(settings)
    Base.metadata.create_all(bind=engine)
    return create_session_factory(engine)
