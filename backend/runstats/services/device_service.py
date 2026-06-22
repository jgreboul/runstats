"""Device configuration services backed by watch providers."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from runstats.api.errors import RunStatsError
from runstats.bluetooth import (
    FakeWatchProvider,
    WatchCapabilityProbe,
    WatchDiscovery,
    WatchProvider,
    WatchProviderError,
)
from runstats.db.models import Device, DeviceCapabilities, DeviceSettings
from runstats.schemas import (
    DeviceCapabilitiesResponse,
    DeviceConnectionTestResponse,
    DeviceListResponse,
    DevicePairRequest,
    DeviceResponse,
    DeviceScanResponse,
    DeviceSettingsPatchRequest,
    DeviceSettingsResponse,
    DiscoveredWatch,
    PreferredUnits,
)


class DeviceService:
    """Read and mutate configured watch records."""

    def __init__(
        self,
        session: Session,
        provider: WatchProvider | None = None,
    ) -> None:
        self.session = session
        self.provider = provider or FakeWatchProvider()

    def scan_for_watches(self, scan_seconds: int = 10) -> DeviceScanResponse:
        """Return provider scan results with known-device flags."""

        known_addresses = set(self.session.scalars(select(Device.bluetooth_address)))
        watches = _map_provider_errors(lambda: self.provider.scan(scan_seconds))
        return DeviceScanResponse(
            devices=[
                _discovered_watch_response(watch, known_addresses)
                for watch in watches
            ]
        )

    def pair_device(self, request: DevicePairRequest) -> DeviceResponse:
        """Create or update a configured watch from provider metadata."""

        identity = _map_provider_errors(
            lambda: self.provider.resolve_watch(request.bluetooth_device_id)
        )

        now = datetime.now(UTC)
        device = self.session.scalar(
            select(Device).where(
                Device.bluetooth_address == identity.bluetooth_device_id
            )
        )
        if device is None:
            device = Device(
                name=request.display_name or identity.name,
                model=identity.model,
                bluetooth_address=identity.bluetooth_device_id,
                serial_number=identity.serial_number,
                firmware_version=identity.firmware_version,
                paired_at=now,
                last_seen_at=now,
                created_at=now,
                updated_at=now,
            )
            self.session.add(device)
        else:
            device.name = request.display_name or device.name
            device.model = identity.model
            device.serial_number = identity.serial_number
            device.firmware_version = identity.firmware_version
            device.paired_at = device.paired_at or now
            device.last_seen_at = now
            device.updated_at = now

        self._ensure_settings(device)
        self._ensure_capabilities(device)
        self.session.commit()
        self.session.refresh(device)
        return _device_response(device)

    def list_devices(self) -> DeviceListResponse:
        """Return configured watches ordered by most recently seen."""

        devices = list(
            self.session.scalars(
                select(Device).order_by(
                    Device.last_seen_at.desc().nullslast(),
                    Device.created_at.desc(),
                    Device.id,
                )
            ).all()
        )
        return DeviceListResponse(
            items=[_device_response(device) for device in devices]
        )

    def update_settings(
        self,
        device_id: str,
        patch: DeviceSettingsPatchRequest,
    ) -> DeviceResponse:
        """Persist a partial settings update for a configured watch."""

        device = self._get_device(device_id)
        settings = self._ensure_settings(device)
        update_data = patch.model_dump(exclude_unset=True)
        for field_name, value in update_data.items():
            if field_name == "historical_fit_import_folder" and value == "":
                value = None
            setattr(settings, field_name, value)
        device.updated_at = datetime.now(UTC)
        self.session.commit()
        self.session.refresh(device)
        return _device_response(device)

    def test_connection(self, device_id: str) -> DeviceConnectionTestResponse:
        """Test provider connectivity and update last seen on success."""

        device = self._get_device(device_id)
        now = datetime.now(UTC)
        try:
            result = self.provider.test_connection(device.bluetooth_address)
        except WatchProviderError as exc:
            return DeviceConnectionTestResponse(
                device_id=device.id,
                status="failed",
                success=False,
                message=exc.message,
                last_seen_at=device.last_seen_at,
                error_code=exc.code,
            )

        if result.connected:
            device.last_seen_at = now
            device.updated_at = now
            if result.serial_number is not None:
                device.serial_number = result.serial_number
            if result.firmware_version is not None:
                device.firmware_version = result.firmware_version
            self.session.commit()
            self.session.refresh(device)
            return DeviceConnectionTestResponse(
                device_id=device.id,
                status="connected",
                success=True,
                message=result.message,
                last_seen_at=device.last_seen_at,
            )

        return DeviceConnectionTestResponse(
            device_id=device.id,
            status="failed",
            success=False,
            message=result.message,
            last_seen_at=device.last_seen_at,
            error_code=result.error_code or "WATCH_CONNECTION_FAILED",
        )

    def probe_capabilities(self, device_id: str) -> DeviceCapabilitiesResponse:
        """Run and persist the latest provider capability probe."""

        device = self._get_device(device_id)
        probe = _map_provider_errors(
            lambda: self.provider.probe_capabilities(device.bluetooth_address)
        )
        now = datetime.now(UTC)
        capabilities = self._apply_capability_probe(device, probe, now)
        device.last_seen_at = now
        device.updated_at = now
        self.session.commit()
        self.session.refresh(device)
        return _capabilities_response(device.id, capabilities)

    def get_capabilities(self, device_id: str) -> DeviceCapabilitiesResponse:
        """Return the latest stored capability result for a device."""

        device = self._get_device(device_id)
        capabilities = self._ensure_capabilities(device)
        return _capabilities_response(device.id, capabilities)

    def _get_device(self, device_id: str) -> Device:
        device = self.session.get(Device, device_id)
        if device is None:
            raise RunStatsError(
                "DEVICE_NOT_FOUND",
                "Device not found.",
                details={"device_id": device_id},
                status_code=404,
            )
        return device

    def _ensure_settings(self, device: Device) -> DeviceSettings:
        if device.settings is not None:
            return device.settings

        settings = DeviceSettings(
            auto_sync_enabled=False,
            sync_interval_minutes=60,
            import_activities=True,
            import_health_stats=True,
            preferred_units="metric",
            historical_fit_import_folder=None,
        )
        device.settings = settings
        return settings

    def _ensure_capabilities(self, device: Device) -> DeviceCapabilities:
        if device.capabilities is not None:
            return device.capabilities

        capabilities = DeviceCapabilities(
            supports_ble_activity_export=False,
            supports_ble_health_export=False,
            supports_folder_import=True,
            capability_notes=None,
            probed_at=None,
        )
        device.capabilities = capabilities
        return capabilities

    def _apply_capability_probe(
        self,
        device: Device,
        probe: WatchCapabilityProbe,
        now: datetime,
    ) -> DeviceCapabilities:
        capabilities = self._ensure_capabilities(device)
        capabilities.supports_ble_activity_export = probe.supports_ble_activity_export
        capabilities.supports_ble_health_export = probe.supports_ble_health_export
        capabilities.supports_folder_import = probe.supports_folder_import
        capabilities.capability_notes = probe.capability_notes
        capabilities.probed_at = now
        return capabilities


def _map_provider_errors[T](operation: Callable[[], T]) -> T:
    try:
        return operation()
    except WatchProviderError as exc:
        raise RunStatsError(
            exc.code,
            exc.message,
            details=exc.details,
            status_code=exc.status_code,
        ) from exc


def _discovered_watch_response(
    watch: WatchDiscovery,
    known_addresses: set[str],
) -> DiscoveredWatch:
    return DiscoveredWatch(
        id=watch.bluetooth_device_id,
        name=watch.name,
        rssi=watch.rssi,
        model_hint=watch.model_hint,
        is_known=watch.bluetooth_device_id in known_addresses,
    )


def _device_response(device: Device) -> DeviceResponse:
    settings = device.settings
    capabilities = device.capabilities
    return DeviceResponse(
        id=device.id,
        name=device.name,
        model=device.model,
        bluetooth_address=device.bluetooth_address,
        serial_number=device.serial_number,
        firmware_version=device.firmware_version,
        paired_at=device.paired_at,
        last_seen_at=device.last_seen_at,
        created_at=device.created_at,
        updated_at=device.updated_at,
        settings=(
            _settings_response(device.id, settings)
            if settings is not None
            else DeviceSettingsResponse(
                device_id=device.id,
                auto_sync_enabled=False,
                sync_interval_minutes=60,
                import_activities=True,
                import_health_stats=True,
                preferred_units="metric",
                historical_fit_import_folder=None,
            )
        ),
        capabilities=(
            _capabilities_response(device.id, capabilities)
            if capabilities is not None
            else DeviceCapabilitiesResponse(
                device_id=device.id,
                supports_ble_activity_export=False,
                supports_ble_health_export=False,
                supports_folder_import=True,
                capability_notes=None,
                probed_at=None,
            )
        ),
    )


def _settings_response(
    device_id: str,
    settings: DeviceSettings,
) -> DeviceSettingsResponse:
    return DeviceSettingsResponse(
        device_id=device_id,
        auto_sync_enabled=settings.auto_sync_enabled,
        sync_interval_minutes=settings.sync_interval_minutes,
        import_activities=settings.import_activities,
        import_health_stats=settings.import_health_stats,
        preferred_units=cast(PreferredUnits, settings.preferred_units),
        historical_fit_import_folder=settings.historical_fit_import_folder,
    )


def _capabilities_response(
    device_id: str,
    capabilities: DeviceCapabilities,
) -> DeviceCapabilitiesResponse:
    return DeviceCapabilitiesResponse(
        device_id=device_id,
        supports_ble_activity_export=capabilities.supports_ble_activity_export,
        supports_ble_health_export=capabilities.supports_ble_health_export,
        supports_folder_import=capabilities.supports_folder_import,
        capability_notes=capabilities.capability_notes,
        probed_at=capabilities.probed_at,
    )
