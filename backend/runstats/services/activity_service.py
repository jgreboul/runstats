"""Activity query and summary services."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from runstats.api.errors import RunStatsError
from runstats.db.models import Activity, ActivityLap, ActivitySample
from runstats.schemas import (
    ActivityDetailResponse,
    ActivityLapResponse,
    ActivityListItem,
    ActivityListResponse,
    ActivitySampleResponse,
    ActivitySamplesResponse,
    ActivitySummaryBucket,
    ActivitySummaryBucketName,
    ActivitySummaryResponse,
    ActivitySummaryStats,
)
from runstats.services.time_buckets import (
    bucket_end_for,
    bucket_start_for,
    ensure_valid_range,
)


@dataclass(frozen=True)
class ActivityFilters:
    """Filters for activity list and summary queries."""

    start_at: datetime | None = None
    end_at: datetime | None = None
    sport: str | None = None
    min_distance_meters: float | None = None
    max_distance_meters: float | None = None


class ActivityService:
    """Read activities and activity aggregates from the database."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_activities(
        self,
        *,
        filters: ActivityFilters | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ActivityListResponse:
        """Return a filtered, paginated activity list."""

        normalized_filters = filters or ActivityFilters()
        ensure_valid_range(normalized_filters.start_at, normalized_filters.end_at)

        total = self._count_activities(normalized_filters)
        query = self._activity_query(normalized_filters).order_by(
            Activity.started_at.desc(), Activity.id
        )
        activities = list(self.session.scalars(query.limit(limit).offset(offset)).all())
        return ActivityListResponse(
            items=[_activity_list_item(activity) for activity in activities],
            total=total,
            limit=limit,
            offset=offset,
        )

    def get_activity(self, activity_id: str) -> ActivityDetailResponse:
        """Return one activity with laps and derived statistics."""

        activity = self.session.scalar(
            select(Activity)
            .where(Activity.id == activity_id)
            .options(
                selectinload(Activity.laps),
                selectinload(Activity.samples),
            )
        )
        if activity is None:
            raise _not_found(activity_id)

        gps_sample_count = sum(
            1
            for sample in activity.samples
            if sample.latitude is not None and sample.longitude is not None
        )
        summary = ActivitySummaryStats(
            distance_kilometers=activity.distance_meters / 1000.0,
            avg_speed_meters_per_second=_avg_speed(
                activity.distance_meters,
                activity.duration_seconds,
            ),
            avg_pace_seconds_per_km=_pace_seconds_per_km(activity),
            lap_count=len(activity.laps),
            sample_count=len(activity.samples),
            gps_sample_count=gps_sample_count,
            has_gps=gps_sample_count > 0,
        )
        return ActivityDetailResponse(
            id=activity.id,
            device_id=activity.device_id,
            source_activity_id=activity.source_activity_id,
            sport=activity.sport,
            name=activity.name,
            started_at=activity.started_at,
            duration_seconds=activity.duration_seconds,
            distance_meters=activity.distance_meters,
            calories=activity.calories,
            avg_heart_rate=activity.avg_heart_rate,
            max_heart_rate=activity.max_heart_rate,
            avg_cadence=activity.avg_cadence,
            avg_pace_seconds_per_km=_pace_seconds_per_km(activity),
            elevation_gain_meters=activity.elevation_gain_meters,
            training_effect=activity.training_effect,
            summary=summary,
            laps=[_lap_response(lap) for lap in activity.laps],
        )

    def get_activity_samples(self, activity_id: str) -> ActivitySamplesResponse:
        """Return samples ordered for chart and map rendering."""

        if self.session.get(Activity, activity_id) is None:
            raise _not_found(activity_id)

        samples = list(
            self.session.scalars(
                select(ActivitySample)
                .where(ActivitySample.activity_id == activity_id)
                .order_by(ActivitySample.elapsed_seconds, ActivitySample.id)
            ).all()
        )
        return ActivitySamplesResponse(
            activity_id=activity_id,
            samples=[_sample_response(sample) for sample in samples],
        )

    def summarize_activities(
        self,
        *,
        filters: ActivityFilters | None = None,
        bucket: ActivitySummaryBucketName = "week",
    ) -> ActivitySummaryResponse:
        """Return aggregate activity totals grouped by calendar bucket."""

        normalized_filters = filters or ActivityFilters()
        ensure_valid_range(normalized_filters.start_at, normalized_filters.end_at)
        activities = list(
            self.session.scalars(
                self._activity_query(normalized_filters).order_by(Activity.started_at)
            ).all()
        )
        buckets = _build_activity_buckets(activities, bucket)
        total_distance = sum(activity.distance_meters for activity in activities)
        total_duration = sum(activity.duration_seconds for activity in activities)
        return ActivitySummaryResponse(
            bucket=bucket,
            from_time=normalized_filters.start_at,
            to_time=normalized_filters.end_at,
            total_activities=len(activities),
            total_distance_meters=total_distance,
            total_duration_seconds=total_duration,
            avg_pace_seconds_per_km=_weighted_pace(total_distance, total_duration),
            avg_heart_rate=_average(
                [
                    float(activity.avg_heart_rate)
                    for activity in activities
                    if activity.avg_heart_rate is not None
                ]
            ),
            buckets=buckets,
        )

    def _activity_query(self, filters: ActivityFilters) -> Select[tuple[Activity]]:
        query = select(Activity)
        if filters.start_at is not None:
            query = query.where(Activity.started_at >= filters.start_at)
        if filters.end_at is not None:
            query = query.where(Activity.started_at <= filters.end_at)
        if filters.sport:
            query = query.where(Activity.sport == filters.sport)
        if filters.min_distance_meters is not None:
            query = query.where(Activity.distance_meters >= filters.min_distance_meters)
        if filters.max_distance_meters is not None:
            query = query.where(Activity.distance_meters <= filters.max_distance_meters)
        return query

    def _count_activities(self, filters: ActivityFilters) -> int:
        query = select(func.count()).select_from(Activity)
        if filters.start_at is not None:
            query = query.where(Activity.started_at >= filters.start_at)
        if filters.end_at is not None:
            query = query.where(Activity.started_at <= filters.end_at)
        if filters.sport:
            query = query.where(Activity.sport == filters.sport)
        if filters.min_distance_meters is not None:
            query = query.where(Activity.distance_meters >= filters.min_distance_meters)
        if filters.max_distance_meters is not None:
            query = query.where(Activity.distance_meters <= filters.max_distance_meters)
        return int(self.session.scalar(query) or 0)


def _build_activity_buckets(
    activities: list[Activity],
    bucket: ActivitySummaryBucketName,
) -> list[ActivitySummaryBucket]:
    grouped: dict[datetime, list[Activity]] = defaultdict(list)
    for activity in activities:
        grouped[bucket_start_for(activity.started_at, bucket)].append(activity)

    results: list[ActivitySummaryBucket] = []
    for bucket_start in sorted(grouped):
        rows = grouped[bucket_start]
        distance = sum(activity.distance_meters for activity in rows)
        duration = sum(activity.duration_seconds for activity in rows)
        heart_rates = [
            float(activity.avg_heart_rate)
            for activity in rows
            if activity.avg_heart_rate is not None
        ]
        results.append(
            ActivitySummaryBucket(
                bucket_start=bucket_start,
                bucket_end=bucket_end_for(bucket_start, bucket),
                activity_count=len(rows),
                distance_meters=distance,
                duration_seconds=duration,
                avg_pace_seconds_per_km=_weighted_pace(distance, duration),
                avg_heart_rate=_average(heart_rates),
                longest_distance_meters=max(
                    (activity.distance_meters for activity in rows),
                    default=0.0,
                ),
            )
        )
    return results


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


def _lap_response(lap: ActivityLap) -> ActivityLapResponse:
    return ActivityLapResponse(
        id=lap.id,
        lap_index=lap.lap_index,
        started_at=lap.started_at,
        duration_seconds=lap.duration_seconds,
        distance_meters=lap.distance_meters,
        avg_heart_rate=lap.avg_heart_rate,
        avg_pace_seconds_per_km=lap.avg_pace_seconds_per_km,
    )


def _sample_response(sample: ActivitySample) -> ActivitySampleResponse:
    return ActivitySampleResponse(
        id=sample.id,
        sample_time=sample.sample_time,
        elapsed_seconds=sample.elapsed_seconds,
        distance_meters=sample.distance_meters,
        latitude=sample.latitude,
        longitude=sample.longitude,
        elevation_meters=sample.elevation_meters,
        heart_rate=sample.heart_rate,
        cadence=sample.cadence,
        power_watts=sample.power_watts,
        speed_meters_per_second=sample.speed_meters_per_second,
    )


def _pace_seconds_per_km(activity: Activity) -> float | None:
    if activity.avg_pace_seconds_per_km is not None:
        return activity.avg_pace_seconds_per_km
    return _weighted_pace(activity.distance_meters, activity.duration_seconds)


def _weighted_pace(distance_meters: float, duration_seconds: float) -> float | None:
    if distance_meters <= 0:
        return None
    return duration_seconds / (distance_meters / 1000.0)


def _avg_speed(distance_meters: float, duration_seconds: float) -> float | None:
    if duration_seconds <= 0:
        return None
    return distance_meters / duration_seconds


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _not_found(activity_id: str) -> RunStatsError:
    return RunStatsError(
        "ACTIVITY_NOT_FOUND",
        "Activity not found.",
        details={"activity_id": activity_id},
        status_code=404,
    )
