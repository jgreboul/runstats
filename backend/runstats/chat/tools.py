"""Approved read-only tools for grounded chat answers."""

from __future__ import annotations

from datetime import datetime
from typing import Final

from sqlalchemy import select
from sqlalchemy.orm import Session

from runstats.db.models import HealthMetric
from runstats.schemas import (
    ActivityDetailResponse,
    ActivityListItem,
    ChatReference,
    ChatToolResult,
    HealthSeriesResponse,
    SyncRunResponse,
)
from runstats.services.activity_service import ActivityService
from runstats.services.analytics_service import AnalyticsService
from runstats.services.health_service import HealthService
from runstats.services.sync_service import SyncService

APPROVED_CHAT_TOOL_NAMES: Final[frozenset[str]] = frozenset(
    {
        "weekly_running_summary",
        "monthly_running_summary",
        "fastest_run_by_distance_threshold",
        "longest_run",
        "activity_detail_lookup",
        "health_metric_trend",
        "activity_health_comparison",
        "sync_status_lookup",
    }
)


class ChatToolRegistry:
    """Read-only tool registry used by chat orchestration."""

    read_only = True

    def __init__(self, session: Session) -> None:
        self.session = session
        self.analytics = AnalyticsService(session)
        self.activities = ActivityService(session)
        self.health = HealthService(session)
        self.sync = SyncService(session)

    @property
    def approved_tool_names(self) -> frozenset[str]:
        """Return the only tool names that orchestration may execute."""

        return APPROVED_CHAT_TOOL_NAMES

    def weekly_running_summary(
        self,
        *,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> ChatToolResult:
        """Summarize running totals by week."""

        result = self.analytics.weekly_running_summary(
            start_at=start_at,
            end_at=end_at,
        )
        return ChatToolResult(
            tool_name="weekly_running_summary",
            intent="weekly_running_summary",
            summary=(
                "Weekly running summary: "
                f"{result.total_activities} runs, "
                f"{_format_distance(result.total_distance_meters)}, "
                f"average pace {_format_pace(result.avg_pace_seconds_per_km)}."
            ),
            row_count=result.total_activities,
            time_range=_range_text(result.from_time, result.to_time),
            metrics=["running_distance", "running_duration", "running_pace"],
            references=[],
            notes=[] if result.total_activities else ["No running activities found."],
            data={
                "bucket": result.bucket,
                "bucket_count": len(result.buckets),
                "total_activities": result.total_activities,
                "total_distance_meters": result.total_distance_meters,
                "total_duration_seconds": result.total_duration_seconds,
                "avg_pace_seconds_per_km": result.avg_pace_seconds_per_km,
            },
        )

    def monthly_running_summary(
        self,
        *,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> ChatToolResult:
        """Summarize running totals by month."""

        result = self.analytics.monthly_running_summary(
            start_at=start_at,
            end_at=end_at,
        )
        return ChatToolResult(
            tool_name="monthly_running_summary",
            intent="monthly_running_summary",
            summary=(
                "Monthly running summary: "
                f"{result.total_activities} runs, "
                f"{_format_distance(result.total_distance_meters)}, "
                f"average pace {_format_pace(result.avg_pace_seconds_per_km)}."
            ),
            row_count=result.total_activities,
            time_range=_range_text(result.from_time, result.to_time),
            metrics=["running_distance", "running_duration", "running_pace"],
            references=[],
            notes=[] if result.total_activities else ["No running activities found."],
            data={
                "bucket": result.bucket,
                "bucket_count": len(result.buckets),
                "total_activities": result.total_activities,
                "total_distance_meters": result.total_distance_meters,
                "total_duration_seconds": result.total_duration_seconds,
                "avg_pace_seconds_per_km": result.avg_pace_seconds_per_km,
            },
        )

    def fastest_run_by_distance_threshold(
        self,
        *,
        min_distance_meters: float,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> ChatToolResult:
        """Find the fastest run at or above a distance threshold."""

        result = self.analytics.fastest_runs_by_distance_threshold(
            min_distance_meters=min_distance_meters,
            start_at=start_at,
            end_at=end_at,
            limit=5,
        )
        winner = result.items[0] if result.items else None
        return ChatToolResult(
            tool_name="fastest_run_by_distance_threshold",
            intent="fastest_run_by_distance_threshold",
            summary=(
                "Fastest qualifying run: "
                f"{_activity_summary(winner)} over at least "
                f"{_format_distance(min_distance_meters)}."
            ),
            row_count=len(result.items),
            time_range=_range_text(result.from_time, result.to_time),
            metrics=["running_pace", "running_distance"],
            references=_activity_references(result.items),
            notes=[] if result.items else ["No runs matched the distance threshold."],
            data={
                "min_distance_meters": min_distance_meters,
                "items": [_activity_data(item) for item in result.items],
            },
        )

    def longest_run(
        self,
        *,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> ChatToolResult:
        """Find the longest imported run."""

        result = self.analytics.longest_runs(
            start_at=start_at,
            end_at=end_at,
            limit=5,
        )
        longest = result.items[0] if result.items else None
        return ChatToolResult(
            tool_name="longest_run",
            intent="longest_run",
            summary=f"Longest run: {_activity_summary(longest)}.",
            row_count=len(result.items),
            time_range=_range_text(result.from_time, result.to_time),
            metrics=["running_distance", "running_duration"],
            references=_activity_references(result.items),
            notes=[] if result.items else ["No running activities found."],
            data={"items": [_activity_data(item) for item in result.items]},
        )

    def activity_detail_lookup(self, activity_id: str) -> ChatToolResult:
        """Return one activity detail summary."""

        detail = self.activities.get_activity(activity_id)
        return ChatToolResult(
            tool_name="activity_detail_lookup",
            intent="activity_detail_lookup",
            summary=(
                f"Activity detail for {detail.name}: "
                f"{_format_distance(detail.distance_meters)}, "
                f"{_format_duration(detail.duration_seconds)}, "
                "average heart rate "
                f"{_format_nullable(detail.avg_heart_rate, ' bpm')}, "
                f"{len(detail.laps)} laps."
            ),
            row_count=1,
            time_range=_range_text(detail.started_at, detail.started_at),
            metrics=["running_distance", "running_duration", "heart_rate"],
            references=[_activity_reference(detail)],
            notes=[],
            data=_activity_detail_data(detail),
        )

    def health_metric_trend(
        self,
        *,
        metric_type: str,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> ChatToolResult:
        """Return a health metric trend without exposing raw records."""

        result = self.health.get_series(
            metric_type=metric_type,
            start_at=start_at,
            end_at=end_at,
            bucket="week",
        )
        row_count = sum(point.record_count for point in result.points)
        latest = result.points[-1] if result.points else None
        notes = []
        if not result.metric_available:
            notes.append(f"Metric '{metric_type}' has not been imported.")
        elif row_count == 0:
            notes.append("No records matched the requested range.")
        return ChatToolResult(
            tool_name="health_metric_trend",
            intent="health_metric_trend",
            summary=(
                f"{_metric_label(metric_type)} trend: "
                f"{row_count} records across {len(result.points)} weekly buckets"
                f"{_latest_health_text(result)}."
            ),
            row_count=row_count,
            time_range=_range_text(result.from_time, result.to_time),
            metrics=[metric_type],
            references=[
                ChatReference(
                    type="chart",
                    id=f"health:{metric_type}",
                    label=f"{_metric_label(metric_type)} chart",
                    href=f"/health?metric={metric_type}",
                )
            ],
            notes=notes,
            data={
                "metric_type": result.metric_type,
                "unit": result.unit,
                "bucket": result.bucket,
                "point_count": len(result.points),
                "latest_value": latest.value if latest is not None else None,
            },
        )

    def activity_health_comparison(
        self,
        *,
        metric_type: str,
    ) -> ChatToolResult:
        """Compare activity volume with a health metric across stored windows."""

        ranges = self._comparison_ranges(metric_type)
        if ranges is None:
            return ChatToolResult(
                tool_name="activity_health_comparison",
                intent="activity_health_comparison",
                summary=(
                    f"Could not compare running activity with "
                    f"{_metric_label(metric_type)} because there is not enough "
                    "stored health data."
                ),
                row_count=0,
                time_range=None,
                metrics=["running_distance", metric_type],
                references=[],
                notes=[f"Metric '{metric_type}' needs at least two records."],
                data={"metric_type": metric_type},
            )

        baseline_start, baseline_end, comparison_start, comparison_end = ranges
        health_result = self.analytics.health_metric_comparison(
            metric_type=metric_type,
            baseline_start_at=baseline_start,
            baseline_end_at=baseline_end,
            comparison_start_at=comparison_start,
            comparison_end_at=comparison_end,
        )
        baseline_runs = self.analytics.weekly_running_summary(
            start_at=baseline_start,
            end_at=baseline_end,
        )
        comparison_runs = self.analytics.weekly_running_summary(
            start_at=comparison_start,
            end_at=comparison_end,
        )
        row_count = (
            health_result.baseline.record_count
            + health_result.comparison.record_count
            + baseline_runs.total_activities
            + comparison_runs.total_activities
        )
        health_unit_suffix = f" {health_result.unit}" if health_result.unit else ""
        return ChatToolResult(
            tool_name="activity_health_comparison",
            intent="activity_health_comparison",
            summary=(
                f"Comparison: running distance changed from "
                f"{_format_distance(baseline_runs.total_distance_meters)} to "
                f"{_format_distance(comparison_runs.total_distance_meters)}; "
                f"{_metric_label(metric_type)} changed by "
                f"{_format_nullable(health_result.delta_value, health_unit_suffix)}."
            ),
            row_count=row_count,
            time_range=_range_text(baseline_start, comparison_end),
            metrics=["running_distance", metric_type],
            references=[
                ChatReference(
                    type="chart",
                    id=f"health:{metric_type}",
                    label=f"{_metric_label(metric_type)} chart",
                    href=f"/health?metric={metric_type}",
                )
            ],
            notes=[
                "Health comparisons describe observed data only, not medical advice."
            ],
            data={
                "metric_type": metric_type,
                "health_delta_value": health_result.delta_value,
                "health_percent_change": health_result.percent_change,
                "baseline_running_distance_meters": baseline_runs.total_distance_meters,
                "comparison_running_distance_meters": (
                    comparison_runs.total_distance_meters
                ),
            },
        )

    def sync_status_lookup(self) -> ChatToolResult:
        """Return recent sync status."""

        result = self.sync.list_sync_runs(limit=3)
        latest = result.items[0] if result.items else None
        return ChatToolResult(
            tool_name="sync_status_lookup",
            intent="sync_status_lookup",
            summary=(
                "Latest sync: "
                f"{_sync_summary(latest)}."
            ),
            row_count=len(result.items),
            time_range=None,
            metrics=["sync_status"],
            references=_sync_references(result.items),
            notes=[] if result.items else ["No sync runs have been recorded."],
            data={"items": [_sync_data(item) for item in result.items]},
        )

    def _comparison_ranges(
        self,
        metric_type: str,
    ) -> tuple[datetime, datetime, datetime, datetime] | None:
        metrics = list(
            self.session.scalars(
                select(HealthMetric)
                .where(HealthMetric.metric_type == metric_type)
                .order_by(HealthMetric.start_time)
            ).all()
        )
        if len(metrics) < 2:
            return None
        midpoint = max(1, len(metrics) // 2)
        baseline_rows = metrics[:midpoint]
        comparison_rows = metrics[midpoint:]
        if not comparison_rows:
            return None
        return (
            baseline_rows[0].start_time,
            baseline_rows[-1].start_time,
            comparison_rows[0].start_time,
            comparison_rows[-1].start_time,
        )


def _activity_summary(activity: ActivityListItem | None) -> str:
    if activity is None:
        return "not available"
    return (
        f"{activity.name} on {_format_date(activity.started_at)} "
        f"({_format_distance(activity.distance_meters)}, "
        f"{_format_pace(activity.avg_pace_seconds_per_km)})"
    )


def _activity_reference(activity: ActivityDetailResponse) -> ChatReference:
    return ChatReference(
        type="activity",
        id=activity.id,
        label=activity.name,
        href=f"/activities/{activity.id}",
    )


def _activity_references(activities: list[ActivityListItem]) -> list[ChatReference]:
    return [
        ChatReference(
            type="activity",
            id=activity.id,
            label=activity.name,
            href=f"/activities/{activity.id}",
        )
        for activity in activities
    ]


def _sync_references(runs: list[SyncRunResponse]) -> list[ChatReference]:
    return [
        ChatReference(
            type="sync_run",
            id=run.id,
            label=f"Sync {run.status}",
            href=f"/sync-history/{run.id}",
        )
        for run in runs
    ]


def _activity_data(activity: ActivityListItem) -> dict[str, object]:
    return {
        "id": activity.id,
        "name": activity.name,
        "started_at": activity.started_at.isoformat(),
        "distance_meters": activity.distance_meters,
        "duration_seconds": activity.duration_seconds,
        "avg_pace_seconds_per_km": activity.avg_pace_seconds_per_km,
        "avg_heart_rate": activity.avg_heart_rate,
    }


def _activity_detail_data(activity: ActivityDetailResponse) -> dict[str, object]:
    return {
        "id": activity.id,
        "name": activity.name,
        "started_at": activity.started_at.isoformat(),
        "distance_meters": activity.distance_meters,
        "duration_seconds": activity.duration_seconds,
        "avg_pace_seconds_per_km": activity.avg_pace_seconds_per_km,
        "avg_heart_rate": activity.avg_heart_rate,
        "max_heart_rate": activity.max_heart_rate,
        "lap_count": len(activity.laps),
    }


def _sync_data(run: SyncRunResponse) -> dict[str, object]:
    return {
        "id": run.id,
        "status": run.status,
        "started_at": run.started_at.isoformat(),
        "duration_seconds": run.duration_seconds,
        "activities_imported": run.activities_imported,
        "health_records_imported": run.health_records_imported,
        "error_summary": run.error_summary,
    }


def _sync_summary(run: SyncRunResponse | None) -> str:
    if run is None:
        return "not available"
    imported = (
        f"{run.activities_imported} activities and "
        f"{run.health_records_imported} health records imported"
    )
    if run.error_summary:
        imported = f"{imported}; {run.error_summary}"
    return f"{run.status} on {_format_date(run.started_at)} ({imported})"


def _latest_health_text(result: HealthSeriesResponse) -> str:
    latest = result.points[-1] if result.points else None
    if latest is None:
        return ""
    unit = f" {result.unit}" if result.unit else ""
    return f"; latest weekly value {_format_nullable(latest.value, unit)}"


def _range_text(start_at: datetime | None, end_at: datetime | None) -> str | None:
    if start_at is None and end_at is None:
        return None
    if start_at is None:
        return f"through {_format_date(end_at)}"
    if end_at is None:
        return f"from {_format_date(start_at)}"
    return f"{_format_date(start_at)} to {_format_date(end_at)}"


def _format_date(value: datetime | None) -> str:
    if value is None:
        return "not available"
    return value.date().isoformat()


def _format_distance(meters: float | None) -> str:
    if meters is None:
        return "not available"
    return f"{meters / 1000.0:.2f} km"


def _format_duration(seconds: float | None) -> str:
    if seconds is None:
        return "not available"
    rounded = round(seconds)
    hours = rounded // 3600
    minutes = (rounded % 3600) // 60
    remaining = rounded % 60
    if hours:
        return f"{hours}h {minutes:02d}m"
    return f"{minutes}:{remaining:02d}"


def _format_pace(seconds_per_km: float | None) -> str:
    if seconds_per_km is None:
        return "not available"
    rounded = round(seconds_per_km)
    return f"{rounded // 60}:{rounded % 60:02d} /km"


def _format_nullable(value: float | int | None, suffix: str = "") -> str:
    if value is None:
        return "not available"
    if isinstance(value, int):
        return f"{value}{suffix}"
    return f"{value:.1f}{suffix}"


def _metric_label(metric_type: str) -> str:
    return metric_type.replace("_", " ").title()
