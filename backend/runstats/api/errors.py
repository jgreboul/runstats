"""Structured API error handling."""

from __future__ import annotations

from collections.abc import Mapping

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette import status
from starlette.exceptions import HTTPException as StarletteHTTPException


class RunStatsError(Exception):
    """Application exception that can be safely returned through the API."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: Mapping[str, object] | None = None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = dict(details or {})
        self.status_code = status_code


def error_payload(
    code: str,
    message: str,
    details: Mapping[str, object] | None = None,
) -> dict[str, dict[str, object]]:
    """Build the stable API error envelope."""

    return {"error": {"code": code, "message": message, "details": dict(details or {})}}


async def runstats_exception_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    """Serialize expected application errors."""

    if not isinstance(exc, RunStatsError):
        raise exc

    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload(exc.code, exc.message, exc.details),
    )


async def http_exception_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    """Normalize FastAPI and Starlette HTTP exceptions."""

    if not isinstance(exc, StarletteHTTPException):
        raise exc

    code = "HTTP_ERROR"
    message = "Request failed."
    details: dict[str, object] = {}

    if exc.status_code == status.HTTP_404_NOT_FOUND:
        code = "NOT_FOUND"
        message = "Resource not found."

    if isinstance(exc.detail, Mapping):
        raw_code = exc.detail.get("code")
        raw_message = exc.detail.get("message")
        raw_details = exc.detail.get("details")
        if isinstance(raw_code, str):
            code = raw_code
        if isinstance(raw_message, str):
            message = raw_message
        if isinstance(raw_details, Mapping):
            details = dict(raw_details)
    elif exc.status_code != status.HTTP_404_NOT_FOUND and isinstance(exc.detail, str):
        message = exc.detail

    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload(code, message, details),
    )


async def validation_exception_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    """Normalize request validation errors."""

    if not isinstance(exc, RequestValidationError):
        raise exc

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_payload(
            "VALIDATION_ERROR",
            "Request validation failed.",
            {"errors": list(exc.errors())},
        ),
    )


def register_error_handlers(app: FastAPI) -> None:
    """Register API exception handlers on an application instance."""

    app.add_exception_handler(RunStatsError, runstats_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
