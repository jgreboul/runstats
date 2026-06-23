"""Provider contracts for watch Bluetooth and export capabilities."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol

WatchExportKind = Literal["activity", "health"]


class WatchProviderError(Exception):
    """Expected provider failure that can be safely mapped to API errors."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: Mapping[str, object] | None = None,
        status_code: int = 400,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = dict(details or {})
        self.status_code = status_code


@dataclass(frozen=True)
class WatchProviderStatus:
    """Current availability of a watch provider adapter."""

    available: bool
    provider_name: str
    message: str | None = None


@dataclass(frozen=True)
class WatchDiscovery:
    """Watch-like BLE device discovered by a provider scan."""

    bluetooth_device_id: str
    name: str
    rssi: int
    model_hint: str | None
    service_uuids: tuple[str, ...] = ()


@dataclass(frozen=True)
class WatchIdentity:
    """Stable metadata used when registering a discovered watch."""

    bluetooth_device_id: str
    name: str
    model: str
    serial_number: str | None = None
    firmware_version: str | None = None


@dataclass(frozen=True)
class WatchConnectionResult:
    """Outcome of connecting to a known watch."""

    bluetooth_device_id: str
    connected: bool
    message: str
    serial_number: str | None = None
    firmware_version: str | None = None
    error_code: str | None = None


@dataclass(frozen=True)
class WatchCapabilityProbe:
    """Detected export and import capabilities for a watch."""

    supports_ble_activity_export: bool
    supports_ble_health_export: bool
    supports_folder_import: bool
    capability_notes: str
    observed_services: tuple[str, ...] = ()


@dataclass(frozen=True)
class WatchExportPayload:
    """Raw watch export payload passed to future importers."""

    kind: WatchExportKind
    source_id: str
    content_type: str
    payload: bytes


class WatchProvider(Protocol):
    """Provider interface isolating Bluetooth and watch-specific behavior."""

    def get_status(self) -> WatchProviderStatus:
        """Return provider availability without mutating state."""

    def scan(self, timeout_seconds: int) -> list[WatchDiscovery]:
        """Scan for nearby watches."""

    def resolve_watch(
        self,
        bluetooth_device_id: str,
        *,
        timeout_seconds: int = 5,
    ) -> WatchIdentity:
        """Resolve metadata for a selected watch before registration."""

    def test_connection(self, bluetooth_device_id: str) -> WatchConnectionResult:
        """Connect to a watch and return a user-safe result."""

    def probe_capabilities(self, bluetooth_device_id: str) -> WatchCapabilityProbe:
        """Detect available direct export and fallback import capabilities."""

    def export_activities(
        self,
        bluetooth_device_id: str,
        *,
        since: datetime | None = None,
    ) -> list[WatchExportPayload]:
        """Export raw activity payloads from a watch."""

    def export_health(
        self,
        bluetooth_device_id: str,
        *,
        since: datetime | None = None,
    ) -> list[WatchExportPayload]:
        """Export raw health payloads from a watch."""
