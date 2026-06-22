"""Healthcheck route."""

from __future__ import annotations

from typing import Literal, TypedDict

from fastapi import APIRouter

from runstats import __version__


class HealthcheckResponse(TypedDict):
    """Response payload for the service health endpoint."""

    status: Literal["ok"]
    service: Literal["runstats"]
    version: str


router = APIRouter(tags=["health"])


@router.get("/healthcheck")
def healthcheck() -> HealthcheckResponse:
    """Return a lightweight backend status payload."""

    return {"status": "ok", "service": "runstats", "version": __version__}
