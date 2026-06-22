"""Activity query APIs."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from runstats.db.session import get_db_session
from runstats.schemas import (
    ActivityDetailResponse,
    ActivityListResponse,
    ActivitySamplesResponse,
    ActivitySummaryBucketName,
    ActivitySummaryResponse,
)
from runstats.services.activity_service import ActivityFilters, ActivityService

router = APIRouter(prefix="/activities", tags=["activities"])
SessionDep = Annotated[Session, Depends(get_db_session)]


@router.get("/summary", response_model=ActivitySummaryResponse)
def summarize_activities(
    session: SessionDep,
    from_time: Annotated[datetime | None, Query(alias="from")] = None,
    to_time: Annotated[datetime | None, Query(alias="to")] = None,
    sport: str | None = None,
    min_distance_meters: Annotated[float | None, Query(ge=0)] = None,
    max_distance_meters: Annotated[float | None, Query(ge=0)] = None,
    bucket: ActivitySummaryBucketName = "week",
) -> ActivitySummaryResponse:
    """Return aggregate activity totals."""

    return ActivityService(session).summarize_activities(
        filters=ActivityFilters(
            start_at=from_time,
            end_at=to_time,
            sport=sport,
            min_distance_meters=min_distance_meters,
            max_distance_meters=max_distance_meters,
        ),
        bucket=bucket,
    )


@router.get("", response_model=ActivityListResponse)
def list_activities(
    session: SessionDep,
    from_time: Annotated[datetime | None, Query(alias="from")] = None,
    to_time: Annotated[datetime | None, Query(alias="to")] = None,
    sport: str | None = None,
    min_distance_meters: Annotated[float | None, Query(ge=0)] = None,
    max_distance_meters: Annotated[float | None, Query(ge=0)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ActivityListResponse:
    """Return filtered activities."""

    return ActivityService(session).list_activities(
        filters=ActivityFilters(
            start_at=from_time,
            end_at=to_time,
            sport=sport,
            min_distance_meters=min_distance_meters,
            max_distance_meters=max_distance_meters,
        ),
        limit=limit,
        offset=offset,
    )


@router.get("/{activity_id}", response_model=ActivityDetailResponse)
def get_activity(activity_id: str, session: SessionDep) -> ActivityDetailResponse:
    """Return one activity detail."""

    return ActivityService(session).get_activity(activity_id)


@router.get("/{activity_id}/samples", response_model=ActivitySamplesResponse)
def get_activity_samples(
    activity_id: str,
    session: SessionDep,
) -> ActivitySamplesResponse:
    """Return ordered activity samples."""

    return ActivityService(session).get_activity_samples(activity_id)
