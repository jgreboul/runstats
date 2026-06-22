"""Date range validation and calendar bucketing helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from runstats.api.errors import RunStatsError
from runstats.schemas import (
    ActivitySummaryBucketName,
    HealthSeriesBucketName,
    TrendBucketName,
)

BucketName = ActivitySummaryBucketName | HealthSeriesBucketName | TrendBucketName


def ensure_valid_range(start_at: datetime | None, end_at: datetime | None) -> None:
    """Validate an optional inclusive time range."""

    if start_at is not None and end_at is not None and start_at > end_at:
        raise RunStatsError(
            "INVALID_DATE_RANGE",
            "The from date must be before the to date.",
            status_code=422,
        )


def ensure_aware_utc(value: datetime) -> datetime:
    """Return a timezone-aware UTC datetime for consistent bucket math."""

    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def bucket_start_for(value: datetime, bucket: BucketName) -> datetime:
    """Return the inclusive calendar bucket start for a datetime."""

    normalized = ensure_aware_utc(value)
    if bucket == "day":
        return normalized.replace(hour=0, minute=0, second=0, microsecond=0)
    if bucket == "week":
        day_start = normalized.replace(hour=0, minute=0, second=0, microsecond=0)
        return day_start - _days(day_start.weekday())
    if bucket == "month":
        return normalized.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if bucket == "year":
        return normalized.replace(
            month=1,
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
    raise ValueError(f"Unsupported bucket: {bucket}")


def bucket_end_for(start: datetime, bucket: BucketName) -> datetime:
    """Return the exclusive calendar bucket end for a bucket start."""

    normalized = ensure_aware_utc(start)
    if bucket == "day":
        return normalized.replace(day=normalized.day) + _days(1)
    if bucket == "week":
        return normalized + _days(7)
    if bucket == "month":
        if normalized.month == 12:
            return normalized.replace(year=normalized.year + 1, month=1)
        return normalized.replace(month=normalized.month + 1)
    if bucket == "year":
        return normalized.replace(year=normalized.year + 1)
    raise ValueError(f"Unsupported bucket: {bucket}")


def _days(count: int) -> timedelta:
    return timedelta(days=count)
