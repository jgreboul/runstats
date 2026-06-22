"""Health metric discovery and series services."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from runstats.db.models import HealthMetric
from runstats.schemas import (
    HealthMetricDescriptor,
    HealthMetricsResponse,
    HealthSeriesBucketName,
    HealthSeriesPoint,
    HealthSeriesResponse,
)
from runstats.services.time_buckets import (
    bucket_end_for,
    bucket_start_for,
    ensure_valid_range,
)

SUM_AGGREGATED_METRICS = {"steps"}


class HealthService:
    """Read health metric metadata and chart-ready series."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_metrics(self) -> HealthMetricsResponse:
        """Return metric types currently stored in the database."""

        rows = self.session.execute(
            select(
                HealthMetric.metric_type,
                HealthMetric.unit,
                func.count(HealthMetric.id),
                func.min(HealthMetric.start_time),
                func.max(HealthMetric.start_time),
            )
            .group_by(HealthMetric.metric_type, HealthMetric.unit)
            .order_by(HealthMetric.metric_type)
        ).all()
        metrics = [
            HealthMetricDescriptor(
                metric_type=row[0],
                unit=row[1],
                record_count=int(row[2]),
                first_start_time=row[3],
                last_start_time=row[4],
            )
            for row in rows
        ]
        return HealthMetricsResponse(metrics=metrics)

    def get_series(
        self,
        *,
        metric_type: str,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        bucket: HealthSeriesBucketName = "day",
    ) -> HealthSeriesResponse:
        """Return an aggregated health metric series."""

        ensure_valid_range(start_at, end_at)
        query = select(HealthMetric).where(HealthMetric.metric_type == metric_type)
        if start_at is not None:
            query = query.where(HealthMetric.start_time >= start_at)
        if end_at is not None:
            query = query.where(HealthMetric.start_time <= end_at)
        metrics = list(
            self.session.scalars(query.order_by(HealthMetric.start_time)).all()
        )
        if not metrics:
            return HealthSeriesResponse(
                metric_type=metric_type,
                unit=self._unit_for_metric(metric_type),
                bucket=bucket,
                from_time=start_at,
                to_time=end_at,
                metric_available=self._metric_exists(metric_type),
                message=f"No stored data is available for metric '{metric_type}'.",
                points=[],
            )

        grouped: dict[datetime, list[HealthMetric]] = defaultdict(list)
        for metric in metrics:
            grouped[bucket_start_for(metric.start_time, bucket)].append(metric)

        points: list[HealthSeriesPoint] = []
        for bucket_start in sorted(grouped):
            rows = grouped[bucket_start]
            values = [row.value for row in rows]
            average_value = sum(values) / len(values)
            total_value = sum(values)
            selected_value = (
                total_value
                if metric_type in SUM_AGGREGATED_METRICS
                else average_value
            )
            points.append(
                HealthSeriesPoint(
                    bucket_start=bucket_start,
                    bucket_end=bucket_end_for(bucket_start, bucket),
                    value=selected_value,
                    average_value=average_value,
                    total_value=total_value,
                    min_value=min(values),
                    max_value=max(values),
                    record_count=len(values),
                )
            )

        return HealthSeriesResponse(
            metric_type=metric_type,
            unit=metrics[0].unit,
            bucket=bucket,
            from_time=start_at,
            to_time=end_at,
            metric_available=True,
            message=None,
            points=points,
        )

    def _metric_exists(self, metric_type: str) -> bool:
        count = self.session.scalar(
            select(func.count())
            .select_from(HealthMetric)
            .where(HealthMetric.metric_type == metric_type)
        )
        return int(count or 0) > 0

    def _unit_for_metric(self, metric_type: str) -> str | None:
        unit = self.session.scalar(
            select(HealthMetric.unit)
            .where(HealthMetric.metric_type == metric_type)
            .order_by(HealthMetric.start_time.desc())
            .limit(1)
        )
        return str(unit) if unit is not None else None
