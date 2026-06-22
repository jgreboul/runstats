"""Raw activity import APIs."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from runstats.config import Settings
from runstats.db.session import get_db_session
from runstats.schemas import (
    FitFolderImportRequest,
    FitFolderImportResponse,
    ImportedActivityFileResult,
)
from runstats.services.import_service import ActivityImportService

router = APIRouter(prefix="/imports", tags=["imports"])
SessionDep = Annotated[Session, Depends(get_db_session)]


@router.post(
    "/fit-folder",
    response_model=FitFolderImportResponse,
    status_code=status.HTTP_200_OK,
)
def import_fit_folder(
    import_request: FitFolderImportRequest,
    request: Request,
    session: SessionDep,
) -> FitFolderImportResponse:
    """Import historical FIT files from a local folder."""

    runtime_settings: Settings = request.app.state.settings
    summary = ActivityImportService(session, runtime_settings).import_fit_folder(
        device_id=import_request.device_id,
        folder_path=import_request.folder_path,
        recursive=import_request.recursive,
    )
    return FitFolderImportResponse(
        created=summary.created,
        skipped=summary.skipped,
        failed=summary.failed,
        raw_files_archived=summary.raw_files_archived,
        files=[
            ImportedActivityFileResult(
                source_id=result.source_id,
                status=result.status,
                message=result.message,
                sha256=result.sha256,
                activity_id=result.activity_id,
                raw_import_id=result.raw_import_id,
                archived=result.archived,
            )
            for result in summary.files
        ],
    )
