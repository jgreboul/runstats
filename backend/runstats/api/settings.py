"""Application settings APIs."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from runstats.config import Settings
from runstats.db.session import get_db_session
from runstats.schemas import AppSettingsPatchRequest, AppSettingsResponse
from runstats.services.settings_service import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])
SessionDep = Annotated[Session, Depends(get_db_session)]


@router.get("", response_model=AppSettingsResponse)
def get_settings(request: Request, session: SessionDep) -> AppSettingsResponse:
    """Return local application settings."""

    runtime_settings: Settings = request.app.state.settings
    return SettingsService(session, runtime_settings).get_settings()


@router.patch("", response_model=AppSettingsResponse)
def update_settings(
    patch: AppSettingsPatchRequest,
    request: Request,
    session: SessionDep,
) -> AppSettingsResponse:
    """Update local application settings."""

    runtime_settings: Settings = request.app.state.settings
    return SettingsService(session, runtime_settings).update_settings(patch)
