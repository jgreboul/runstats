"""Deterministic fake Garmin provider used by tests and mock workflows."""

from __future__ import annotations

from dataclasses import dataclass

from runstats.bluetooth.provider import (
    WatchCapabilityProbe,
    WatchConnectionResult,
    WatchDiscovery,
    WatchExportPayload,
    WatchIdentity,
    WatchProviderError,
    WatchProviderStatus,
)


@dataclass(frozen=True)
class FakeWatchProfile:
    """Static fake watch behavior."""

    bluetooth_device_id: str
    name: str
    model: str
    model_hint: str
    rssi: int
    serial_number: str | None
    firmware_version: str | None
    supports_ble_activity_export: bool
    supports_ble_health_export: bool
    supports_folder_import: bool
    connection_succeeds: bool
    capability_notes: str
    service_uuids: tuple[str, ...] = ()


FAKE_WATCHES: tuple[FakeWatchProfile, ...] = (
    FakeWatchProfile(
        bluetooth_device_id="fake-fr935-001",
        name="Garmin Forerunner 935",
        model="Forerunner 935",
        model_hint="Forerunner",
        rssi=-58,
        serial_number="FR935-MOCK-001",
        firmware_version="21.00",
        supports_ble_activity_export=False,
        supports_ble_health_export=False,
        supports_folder_import=True,
        connection_succeeds=True,
        capability_notes=(
            "Direct BLE export is not available in the fake Forerunner 935 "
            "profile. Use folder import until a Garmin export adapter is "
            "configured."
        ),
    ),
    FakeWatchProfile(
        bluetooth_device_id="fake-fr965-002",
        name="Garmin Forerunner 965",
        model="Forerunner 965",
        model_hint="Forerunner",
        rssi=-49,
        serial_number="FR965-MOCK-002",
        firmware_version="18.22",
        supports_ble_activity_export=True,
        supports_ble_health_export=False,
        supports_folder_import=True,
        connection_succeeds=True,
        capability_notes=(
            "The fake Forerunner 965 profile reports direct activity export and "
            "folder import support. Health export remains unsupported."
        ),
        service_uuids=("fake-garmin-activity-export",),
    ),
    FakeWatchProfile(
        bluetooth_device_id="fake-fr935-offline",
        name="Garmin Forerunner 935 Offline",
        model="Forerunner 935",
        model_hint="Forerunner",
        rssi=-86,
        serial_number="FR935-MOCK-OFFLINE",
        firmware_version="21.00",
        supports_ble_activity_export=False,
        supports_ble_health_export=False,
        supports_folder_import=True,
        connection_succeeds=False,
        capability_notes=(
            "This fake device is intentionally offline so connection and sync "
            "failure states can be tested without hardware."
        ),
    ),
)


class FakeWatchProvider:
    """Deterministic provider for tests and fake device workflows."""

    def __init__(self, profiles: tuple[FakeWatchProfile, ...] = FAKE_WATCHES) -> None:
        self._profiles = {profile.bluetooth_device_id: profile for profile in profiles}

    def get_status(self) -> WatchProviderStatus:
        """Return fake provider availability."""

        return WatchProviderStatus(
            available=True,
            provider_name="fake",
            message="Fake Garmin watch provider is available.",
        )

    def scan(self, timeout_seconds: int = 10) -> list[WatchDiscovery]:
        """Return fake nearby Garmin watches."""

        _ = timeout_seconds
        return [
            WatchDiscovery(
                bluetooth_device_id=profile.bluetooth_device_id,
                name=profile.name,
                rssi=profile.rssi,
                model_hint=profile.model_hint,
                service_uuids=profile.service_uuids,
            )
            for profile in self._profiles.values()
        ]

    def resolve_watch(
        self,
        bluetooth_device_id: str,
        *,
        timeout_seconds: int = 5,
    ) -> WatchIdentity:
        """Return fake watch metadata by Bluetooth identifier."""

        _ = timeout_seconds
        profile = self.get_profile(bluetooth_device_id)
        if profile is None:
            raise WatchProviderError(
                "WATCH_NOT_DISCOVERED",
                "The selected watch is no longer available. Scan again.",
                details={"bluetooth_device_id": bluetooth_device_id},
                status_code=404,
            )
        return WatchIdentity(
            bluetooth_device_id=profile.bluetooth_device_id,
            name=profile.name,
            model=profile.model,
            serial_number=profile.serial_number,
            firmware_version=profile.firmware_version,
        )

    def get_profile(self, bluetooth_device_id: str) -> FakeWatchProfile | None:
        """Return a fake watch profile by Bluetooth identifier."""

        return self._profiles.get(bluetooth_device_id)

    def test_connection(self, bluetooth_device_id: str) -> WatchConnectionResult:
        """Return whether the fake device should connect successfully."""

        profile = self.get_profile(bluetooth_device_id)
        if profile is not None and profile.connection_succeeds:
            return WatchConnectionResult(
                bluetooth_device_id=bluetooth_device_id,
                connected=True,
                message="Connection test succeeded.",
                serial_number=profile.serial_number,
                firmware_version=profile.firmware_version,
            )
        return WatchConnectionResult(
            bluetooth_device_id=bluetooth_device_id,
            connected=False,
            message=(
                "Connection test failed. Keep the watch nearby and retry after "
                "Bluetooth is available."
            ),
            error_code="WATCH_CONNECTION_FAILED",
        )

    def probe_capabilities(self, bluetooth_device_id: str) -> WatchCapabilityProbe:
        """Return the configured fake capability matrix."""

        profile = self.get_profile(bluetooth_device_id)
        if profile is None:
            raise WatchProviderError(
                "WATCH_NOT_DISCOVERED",
                "The selected watch is no longer available. Scan again.",
                details={"bluetooth_device_id": bluetooth_device_id},
                status_code=404,
            )
        if not profile.connection_succeeds:
            raise WatchProviderError(
                "WATCH_CONNECTION_FAILED",
                "Unable to connect to the watch for capability probing.",
                details={"bluetooth_device_id": bluetooth_device_id},
                status_code=503,
            )
        return WatchCapabilityProbe(
            supports_ble_activity_export=profile.supports_ble_activity_export,
            supports_ble_health_export=profile.supports_ble_health_export,
            supports_folder_import=profile.supports_folder_import,
            capability_notes=profile.capability_notes,
            observed_services=profile.service_uuids,
        )

    def export_activities(self, bluetooth_device_id: str) -> list[WatchExportPayload]:
        """Return no fake raw activity payloads yet."""

        _ = bluetooth_device_id
        return []

    def export_health(self, bluetooth_device_id: str) -> list[WatchExportPayload]:
        """Return no fake raw health payloads yet."""

        _ = bluetooth_device_id
        return []
