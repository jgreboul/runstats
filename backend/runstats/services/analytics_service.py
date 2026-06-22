"""Reusable analytics methods for dashboards and chat tools."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from runstats.db.models import Activity, HealthMetric
from runstats.schemas import (
    ActivityListItem,
    ActivityRankingResult,
    HealthComparisonWindow,
    HealthMetricComparisonResult,
    RunningSummaryBucket,
    RunningSummaryResult,
    TrendBucketName,
    TrendPoint,
    TrendResult,
)
from runstats.services.health_service import SUM_AGGREGATED_METRICS
from runstats.services.time_buckets import (
    bucket_end_for,
    bucket_start_for,
    ensure_valid_range,
)

RUNNING_SPORTS = {"running", "trail_running", "treadmill_running"}


class AnalyticsService:
    """Read-only analytics over local activity and health data."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def weekly_running_summary(
        self,
        *,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> RunningSummaryResult:
        """Return running totals grouped by week."""

        return self._running_summary("week", start_at=start_at, end_at=end_at)

    def monthly_running_summary(
        self,
        *,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> RunningSummaryResult:
        """Return running totals grouped by month."""

        return self._running_summary("month", start_at=start_at, end_at=end_at)

    def fastest_runs_by_distance_threshold(
        self,
        *,
        min_distance_meters: float,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        limit: int = 5,
    ) -> ActivityRankingResult:
        """Return fastest runs at or above a distance threshold."""

        ensure_valid_range(start_at, end_at)
        activities = [
            activity
            for activity in self._running_activities(start_at, end_at)
            if activity.distance_meters >= min_distance_meters
        ]
        sorted_activities = sorted(
            activities,
            key=lambda activity: (
                _pace_seconds_per_km(activity) is None,
                _pace_seconds_per_km(activity) or 0.0,
                activity.started_at,
            ),
        )
        return ActivityRankingResult(
            ranking="fastest_by_distance_threshold",
            from_time=start_at,
            to_time=end_at,
            min_distance_meters=min_distance_meters,
            items=[
                _activity_list_item(activity)
                for activity in sorted_activities[:limit]
            ],
        )

    def longest_runs(
        self,
        *,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        limit: int = 5,
    ) -> ActivityRankingResult:
        """Return longest runs by distance."""

        ensure_valid_range(start_at, end_at)
        sorted_activities = sorted(
            self._running_activities(start_at, end_at),
            key=lambda activity: (-activity.distance_meters, activity.started_at),
        )
        return ActivityRankingResult(
            ranking="longest_runs",
            from_time=start_at,
            to_time=end_at,
            min_distance_meters=None,
            items=[
                _activity_list_item(activity)
                for activity in sorted_activities[:limit]
            ],
        )

    def pace_trend(
        self,
        *,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        bucket: TrendBucketName = "week",
    ) -> TrendResult:
        """Return weighted pace trend by calendar bucket."""

        ensure_valid_range(start_at, end_at)
        grouped = _group_activities(self._running_activities(start_at, end_at), bucket)
        points: list[TrendPoint] = []
        for bucket_start in sorted(grouped):
            rows = grouped[bucket_start]
            distance = sum(activity.distance_meters for activity in rows)
            duration = sum(activity.duration_seconds for activity in rows)
            points.append(
                TrendPoint(
                    bucket_start=bucket_start,
                    bucket_end=bucket_end_for(bucket_start, bucket),
                    value=_weighted_pace(distance, duration),
                    record_count=len(rows),
                )
            )
        return TrendResult(
            metric="pace_seconds_per_km",
            bucket=bucket,
            from_time=start_at,
            to_time=end_at,
            points=points,
        )

    def heart_rate_trend(
        self,
        *,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        bucket: TrendBucketName = "week",
    ) -> TrendResult:
        """Return average heart-rate trend by calendar bucket."""

        ensure_valid_range(start_at, end_at)
        grouped = _group_activities(self._running_activities(start_at, end_at), bucket)
        points: list[TrendPoint] = []
        for bucket_start in sorted(grouped):
            values = [
                float(activity.avg_heart_rate)
                for activity in grouped[bucket_start]
                if activity.avg_heart_rate is not None
            ]
            points.append(
                TrendPoint(
                    bucket_start=bucket_start,
                    bucket_end=bucket_end_for(bucket_start, bucket),
                    value=_average(values),
                    record_count=len(values),
                )
            )
        return TrendResult(
            metric="heart_rate_bpm",
            bucket=bucket,
            from_time=start_at,
            to_time=end_at,
            points=points,
        )

    def health_metric_comparison(
        self,
        *,
        metric_type: str,
        baseline_start_at: datetime,
        baseline_end_at: datetime,
        comparison_start_at: datetime,
        comparison_end_at: datetime,
    ) -> HealthMetricComparisonResult:
        """Compare one health metric across two explicit time windows."""

        ensure_valid_range(baseline_start_at, baseline_end_at)
        ensure_valid_range(comparison_start_at, comparison_end_at)
        baseline_metrics = self._health_metrics(
            metric_type,
            baseline_start_at,
            baseline_end_at,
        )
        comparison_metrics = self._health_metrics(
            metric_type,
            comparison_start_at,
            comparison_end_at,
        )
        aggregation: Literal["average", "sum"] = (
            "sum" if metric_type in SUM_AGGREGATED_METRICS else "average"
        )
        baseline_value = _health_metric_value(baseline_metrics, aggregation)
        comparison_value = _health_metric_value(comparison_metrics, aggregation)
        delta = (
            comparison_value - baseline_value
            if baseline_value is not None and comparison_value is not None
            else None
        )
        percent_change: float | None = None
        if delta is not None and baseline_value is not None and baseline_value != 0:
            percent_change = (delta / baseline_value) * 100.0
        return HealthMetricComparisonResult(
            metric_type=metric_type,
            unit=_unit_for_metrics([*baseline_metrics, *comparison_metrics]),
            aggregation=aggregation,
            baseline=HealthComparisonWindow(
                from_time=baseline_start_at,
                to_time=baseline_end_at,
                value=baseline_value,
                record_count=len(baseline_metrics),
            ),
            comparison=HealthComparisonWindow(
                from_time=comparison_start_at,
                to_time=comparison_end_at,
                value=comparison_value,
                record_count=len(comparison_metrics),
            ),
            delta_value=delta,
            percent_change=percent_change,
        )

    def _running_summary(
        self,
        bucket: Literal["week", "month"],
        *,
        start_at: datetime | None,
        end_at: datetime | None,
    ) -> RunningSummaryResult:
        ensure_valid_range(start_at, end_at)
        activities = self._running_activities(start_at, end_at)
        grouped = _group_activities(activities, bucket)
        buckets: list[RunningSummaryBucket] = []
        for bucket_start in sorted(grouped):
            rows = grouped[bucket_start]
            distance = sum(activity.distance_meters for activity in rows)
            duration = sum(activity.duration_seconds for activity in rows)
            heart_rates = [
                float(activity.avg_heart_rate)
                for activity in rows
                if activity.avg_heart_rate is not None
            ]
            buckets.append(
                RunningSummaryBucket(
                    bucket_start=bucket_start,
                    bucket_end=bucket_end_for(bucket_start, bucket),
                    activity_count=len(rows),
                    distance_meters=distance,
                    duration_seconds=duration,
                    avg_pace_seconds_per_km=_weighted_pace(distance, duration),
                    avg_heart_rate=_average(heart_rates),
                )
            )
        total_distance = sum(activity.distance_meters for activity in activities)
        total_duration = sum(activity.duration_seconds for activity in activities)
        return RunningSummaryResult(
            bucket=bucket,
            from_time=start_at,
            to_time=end_at,
            total_activities=len(activities),
            total_distance_meters=total_distance,
            total_duration_seconds=total_duration,
            avg_pace_seconds_per_km=_weighted_pace(total_distance, total_duration),
            buckets=buckets,
        )

    def _running_activities(
        self,
        start_at: datetime | None,
        end_at: datetime | None,
    ) -> list[Activity]:
        query = select(Activity).where(Activity.sport.in_(RUNNING_SPORTS))
        if start_at is not None:
            query = query.where(Activity.started_at >= start_at)
        if end_at is not None:
            query = query.where(Activity.started_at <= end_at)
        return list(self.session.scalars(query.order_by(Activity.started_at)).all())

    def _health_metrics(
        self,
        metric_type: str,
        start_at: datetime,
        end_at: datetime,
    ) -> list[HealthMetric]:
        return list(
            self.session.scalars(
                select(HealthMetric)
                .where(HealthMetric.metric_type == metric_type)
                .where(HealthMetric.start_time >= start_at)
                .where(HealthMetric.start_time <= end_at)
                .order_by(HealthMetric.start_time)
            ).all()
        )


def _group_activities(
    activities: list[Activity],
    bucket: TrendBucketName | Literal["week", "month"],
) -> dict[datetime, list[Activity]]:
    grouped: dict[datetime, list[Activity]] = defaultdict(list)
    for activity in activities:
        grouped[bucket_start_for(activity.started_at, bucket)].append(activity)
    return grouped


def _activity_list_item(activity: Activity) -> ActivityListItem:
    return ActivityListItem(
        id=activity.id,
        device_id=activity.device_id,
        sport=activity.sport,
        name=activity.name,
        started_at=activity.started_at,
        duration_seconds=activity.duration_seconds,
        distance_meters=activity.distance_meters,
        avg_pace_seconds_per_km=_pace_seconds_per_km(activity),
        avg_heart_rate=activity.avg_heart_rate,
        elevation_gain_meters=activity.elevation_gain_meters,
    )


def _pace_seconds_per_km(activity: Activity) -> float | None:
    if activity.avg_pace_seconds_per_km is not None:
        return activity.avg_pace_seconds_per_km
    return _weighted_pace(activity.distance_meters, activity.duration_seconds)


def _weighted_pace(distance_meters: float, duration_seconds: float) -> float | None:
    if distance_meters <= 0:
        return None
    return duration_seconds / (distance_meters / 1000.0)


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _health_metric_value(
    metrics: list[HealthMetric],
    aggregation: Literal["average", "sum"],
) -> float | None:
    if not metrics:
        return None
    values = [metric.value for metric in metrics]
    if aggregation == "sum":
        return sum(values)
    return sum(values) / len(values)


def _unit_for_metrics(metrics: list[HealthMetric]) -> str | None:
    units = {metric.unit for metric in metrics}
    if not units:
        return None
    if len(units) > 1:
        return "mixed"
    return units.pop()
