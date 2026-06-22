"""Health metric APIs."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from runstats.db.session import get_db_session
from runstats.schemas import (
    HealthMetricsResponse,
    HealthSeriesBucketName,
    HealthSeriesResponse,
)
from runstats.services.health_service import HealthService

router = APIRouter(prefix="/health", tags=["health"])
SessionDep = Annotated[Session, Depends(get_db_session)]


@router.get("/metrics", response_model=HealthMetricsResponse)
def list_health_metrics(session: SessionDep) -> HealthMetricsResponse:
    """Return available health metric types."""

    return HealthService(session).list_metrics()


@router.get("/series", response_model=HealthSeriesResponse)
def get_health_series(
    session: SessionDep,
    metric_type: str,
    from_time: Annotated[datetime | None, Query(alias="from")] = None,
    to_time: Annotated[datetime | None, Query(alias="to")] = None,
    bucket: HealthSeriesBucketName = "day",
) -> HealthSeriesResponse:
    """Return chart-ready health metric values."""

    return HealthService(session).get_series(
        metric_type=metric_type,
        start_at=from_time,
        end_at=to_time,
        bucket=bucket,
    )
