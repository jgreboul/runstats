"""Local data export and deletion APIs."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from runstats.db.session import get_db_session
from runstats.schemas import (
    DataDeletionResponse,
    DataExportRequest,
    DataExportResponse,
)
from runstats.services.data_management_service import DataManagementService

router = APIRouter(prefix="/data-management", tags=["data-management"])
SessionDep = Annotated[Session, Depends(get_db_session)]


@router.post("/export", response_model=DataExportResponse)
def export_data(
    request: DataExportRequest,
    session: SessionDep,
) -> DataExportResponse:
    """Export local data in the documented RunStats JSON format."""

    return DataManagementService(session).export_data(request)


@router.delete("/chat-history", response_model=DataDeletionResponse)
def delete_chat_history(session: SessionDep) -> DataDeletionResponse:
    """Delete all local chat history."""

    return DataManagementService(session).delete_chat_history()


@router.delete(
    "/devices/{device_id}/imported-data",
    response_model=DataDeletionResponse,
)
def delete_device_imported_data(
    device_id: str,
    session: SessionDep,
) -> DataDeletionResponse:
    """Delete imported activity, health, and raw archive data for one device."""

    return DataManagementService(session).delete_imported_data_for_device(device_id)
