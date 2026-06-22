"""Raw activity import APIs."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from runstats.config import Settings
from runstats.db.session import get_db_session
from runstats.schemas import (
    FitFolderImportRequest,
    FitFolderImportResponse,
    HealthPayloadImportRequest,
    HealthPayloadImportResponse,
    ImportedActivityFileResult,
    ImportedHealthPayloadResult,
    ImportedHealthWarning,
)
from runstats.services.health_import_service import HealthImportService
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


@router.post(
    "/health-payload",
    response_model=HealthPayloadImportResponse,
    status_code=status.HTTP_200_OK,
)
def import_health_payload(
    import_request: HealthPayloadImportRequest,
    request: Request,
    session: SessionDep,
) -> HealthPayloadImportResponse:
    """Import a local JSON health payload fixture."""

    runtime_settings: Settings = request.app.state.settings
    result = HealthImportService(session, runtime_settings).import_health_file(
        device_id=import_request.device_id,
        file_path=Path(import_request.file_path),
    )
    return HealthPayloadImportResponse(
        records_created=result.records_created,
        records_skipped=result.records_skipped,
        payloads_failed=1 if result.status == "failed" else 0,
        raw_files_archived=1 if result.archived else 0,
        payloads=[
            ImportedHealthPayloadResult(
                source_id=result.source_id,
                status=result.status,
                message=result.message,
                sha256=result.sha256,
                raw_import_id=result.raw_import_id,
                archived=result.archived,
                records_created=result.records_created,
                records_skipped=result.records_skipped,
                warnings=[
                    ImportedHealthWarning(
                        source_id=warning.source_id,
                        message=warning.message,
                        record_index=warning.record_index,
                        metric_type=warning.metric_type,
                    )
                    for warning in result.warnings or []
                ],
            )
        ],
    )
