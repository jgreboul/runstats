"""Device configuration APIs."""

from __future__ import annotations

from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from runstats.bluetooth import WatchProvider
from runstats.db.session import get_db_session
from runstats.schemas import (
    DeviceCapabilitiesResponse,
    DeviceConnectionTestResponse,
    DeviceListResponse,
    DevicePairRequest,
    DeviceResponse,
    DeviceScanRequest,
    DeviceScanResponse,
    DeviceSettingsPatchRequest,
)
from runstats.services.device_service import DeviceService

router = APIRouter(prefix="/devices", tags=["devices"])
SessionDep = Annotated[Session, Depends(get_db_session)]


def get_watch_provider(request: Request) -> WatchProvider:
    """Return the app-scoped watch provider."""

    return cast(WatchProvider, request.app.state.watch_provider)


WatchProviderDep = Annotated[WatchProvider, Depends(get_watch_provider)]


@router.post("/scan", response_model=DeviceScanResponse)
def scan_devices(
    request: DeviceScanRequest,
    session: SessionDep,
    provider: WatchProviderDep,
) -> DeviceScanResponse:
    """Return nearby Garmin watches from the configured provider."""

    return DeviceService(session, provider).scan_for_watches(request.scan_seconds)


@router.post("/pair", response_model=DeviceResponse)
def pair_device(
    request: DevicePairRequest,
    session: SessionDep,
    provider: WatchProviderDep,
) -> DeviceResponse:
    """Pair or register a discovered watch."""

    return DeviceService(session, provider).pair_device(request)


@router.get("", response_model=DeviceListResponse)
def list_devices(session: SessionDep) -> DeviceListResponse:
    """Return configured watches."""

    return DeviceService(session).list_devices()


@router.patch("/{device_id}/settings", response_model=DeviceResponse)
def update_device_settings(
    device_id: str,
    patch: DeviceSettingsPatchRequest,
    session: SessionDep,
    provider: WatchProviderDep,
) -> DeviceResponse:
    """Update persisted per-device settings."""

    return DeviceService(session, provider).update_settings(device_id, patch)


@router.post(
    "/{device_id}/test-connection",
    response_model=DeviceConnectionTestResponse,
)
def test_device_connection(
    device_id: str,
    session: SessionDep,
    provider: WatchProviderDep,
) -> DeviceConnectionTestResponse:
    """Run a connection test for a configured watch."""

    return DeviceService(session, provider).test_connection(device_id)


@router.post(
    "/{device_id}/probe-capabilities",
    response_model=DeviceCapabilitiesResponse,
)
def probe_device_capabilities(
    device_id: str,
    session: SessionDep,
    provider: WatchProviderDep,
) -> DeviceCapabilitiesResponse:
    """Run and persist a watch capability probe."""

    return DeviceService(session, provider).probe_capabilities(device_id)


@router.get(
    "/{device_id}/capabilities",
    response_model=DeviceCapabilitiesResponse,
)
def get_device_capabilities(
    device_id: str,
    session: SessionDep,
    provider: WatchProviderDep,
) -> DeviceCapabilitiesResponse:
    """Return the latest stored watch capability probe result."""

    return DeviceService(session, provider).get_capabilities(device_id)
