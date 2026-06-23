"""Bleak-backed Garmin watch discovery and capability probing."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Coroutine, Iterable, Mapping
from datetime import datetime
from importlib import import_module
from typing import Any

from runstats.bluetooth.provider import (
    WatchCapabilityProbe,
    WatchConnectionResult,
    WatchDiscovery,
    WatchExportPayload,
    WatchIdentity,
    WatchProviderError,
    WatchProviderStatus,
)

GARMIN_COMPANY_IDENTIFIER = 0x0087
DIRECT_EXPORT_SERVICE_UUIDS: tuple[str, ...] = ()


class BleakWatchProvider:
    """Cross-platform BLE provider backed by the Bleak library."""

    provider_name = "bleak"

    def get_status(self) -> WatchProviderStatus:
        """Return whether the Bleak dependency is importable."""

        try:
            _load_bleak()
        except WatchProviderError as exc:
            return WatchProviderStatus(
                available=False,
                provider_name=self.provider_name,
                message=exc.message,
            )
        return WatchProviderStatus(
            available=True,
            provider_name=self.provider_name,
            message="Bleak Bluetooth provider is available.",
        )

    def scan(self, timeout_seconds: int = 10) -> list[WatchDiscovery]:
        """Scan for nearby Garmin Forerunner-like BLE advertisements."""

        return _run_async(self._scan(timeout_seconds))

    async def _scan(self, timeout_seconds: int) -> list[WatchDiscovery]:
        bleak = _load_bleak()
        scanner = bleak.BleakScanner
        try:
            raw_devices = await scanner.discover(
                timeout=float(timeout_seconds),
                return_adv=True,
            )
        except Exception as exc:
            raise _bluetooth_unavailable(exc) from exc

        watches = [
            watch
            for watch in (
                _watch_from_ble_device(device, advertisement)
                for device, advertisement in _iter_ble_scan_results(raw_devices)
            )
            if watch is not None
        ]
        return sorted(watches, key=lambda watch: watch.rssi, reverse=True)

    def resolve_watch(
        self,
        bluetooth_device_id: str,
        *,
        timeout_seconds: int = 5,
    ) -> WatchIdentity:
        """Resolve selected watch metadata by scanning for the same address."""

        discoveries = self.scan(timeout_seconds)
        for discovery in discoveries:
            if discovery.bluetooth_device_id == bluetooth_device_id:
                return WatchIdentity(
                    bluetooth_device_id=discovery.bluetooth_device_id,
                    name=discovery.name,
                    model=discovery.model_hint or "Garmin watch",
                )
        raise WatchProviderError(
            "WATCH_NOT_DISCOVERED",
            "The selected watch is no longer available. Scan again.",
            details={"bluetooth_device_id": bluetooth_device_id},
            status_code=404,
        )

    def test_connection(self, bluetooth_device_id: str) -> WatchConnectionResult:
        """Attempt a BLE connection to a configured watch."""

        return _run_async(self._test_connection(bluetooth_device_id))

    async def _test_connection(self, bluetooth_device_id: str) -> WatchConnectionResult:
        bleak = _load_bleak()
        client_type = bleak.BleakClient
        try:
            async with client_type(bluetooth_device_id, timeout=10.0) as client:
                connected = bool(getattr(client, "is_connected", False))
                if connected:
                    return WatchConnectionResult(
                        bluetooth_device_id=bluetooth_device_id,
                        connected=True,
                        message="Connection test succeeded.",
                    )
        except Exception as exc:
            if _looks_like_bluetooth_unavailable(exc):
                raise _bluetooth_unavailable(exc) from exc
            return WatchConnectionResult(
                bluetooth_device_id=bluetooth_device_id,
                connected=False,
                message=(
                    "Connection test failed. Keep the watch nearby and retry "
                    "after Bluetooth is available."
                ),
                error_code="WATCH_CONNECTION_FAILED",
            )

        return WatchConnectionResult(
            bluetooth_device_id=bluetooth_device_id,
            connected=False,
            message="The watch did not report a connected Bluetooth state.",
            error_code="WATCH_CONNECTION_FAILED",
        )

    def probe_capabilities(self, bluetooth_device_id: str) -> WatchCapabilityProbe:
        """Inspect watch GATT services for known direct export capabilities."""

        return _run_async(self._probe_capabilities(bluetooth_device_id))

    async def _probe_capabilities(
        self,
        bluetooth_device_id: str,
    ) -> WatchCapabilityProbe:
        bleak = _load_bleak()
        client_type = bleak.BleakClient
        try:
            async with client_type(bluetooth_device_id, timeout=15.0) as client:
                if not bool(getattr(client, "is_connected", False)):
                    raise WatchProviderError(
                        "WATCH_CONNECTION_FAILED",
                        "Unable to connect to the watch for capability probing.",
                        details={"bluetooth_device_id": bluetooth_device_id},
                        status_code=503,
                    )
                services = _service_uuids(await _client_services(client))
        except WatchProviderError:
            raise
        except Exception as exc:
            if _looks_like_bluetooth_unavailable(exc):
                raise _bluetooth_unavailable(exc) from exc
            raise WatchProviderError(
                "WATCH_CAPABILITY_PROBE_FAILED",
                "Unable to inspect watch Bluetooth services.",
                details={"bluetooth_device_id": bluetooth_device_id},
                status_code=503,
            ) from exc

        supports_direct_export = any(
            service_uuid in DIRECT_EXPORT_SERVICE_UUIDS for service_uuid in services
        )
        if supports_direct_export:
            notes = (
                "A known direct BLE export service was detected. Activity export "
                "can be implemented behind the Garmin BLE adapter; health export "
                "still needs a confirmed record source."
            )
        else:
            notes = (
                "Connected to the watch, but no direct BLE activity or health "
                "export service was identified. Use folder-based FIT import next; "
                "evaluate Garmin Health SDK or Garmin Connect Developer Program "
                "APIs for richer health data."
            )

        return WatchCapabilityProbe(
            supports_ble_activity_export=supports_direct_export,
            supports_ble_health_export=False,
            supports_folder_import=True,
            capability_notes=notes,
            observed_services=services,
        )

    def export_activities(
        self,
        bluetooth_device_id: str,
        *,
        since: datetime | None = None,
    ) -> list[WatchExportPayload]:
        """Direct BLE activity export is not implemented until probe confirms it."""

        _ = bluetooth_device_id
        _ = since
        raise WatchProviderError(
            "WATCH_EXPORT_UNSUPPORTED",
            "Direct BLE activity export is not available for this provider yet.",
            status_code=409,
        )

    def export_health(
        self,
        bluetooth_device_id: str,
        *,
        since: datetime | None = None,
    ) -> list[WatchExportPayload]:
        """Direct BLE health export is not implemented until probe confirms it."""

        _ = bluetooth_device_id
        _ = since
        raise WatchProviderError(
            "WATCH_EXPORT_UNSUPPORTED",
            "Direct BLE health export is not available for this provider yet.",
            status_code=409,
        )


def _load_bleak() -> Any:
    try:
        return import_module("bleak")
    except ImportError as exc:
        raise WatchProviderError(
            "BLUETOOTH_UNAVAILABLE",
            "Bluetooth support is unavailable because Bleak is not installed.",
            status_code=503,
        ) from exc


def _run_async[T](awaitable: Coroutine[Any, Any, T]) -> T:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)
    raise WatchProviderError(
        "BLUETOOTH_PROVIDER_BUSY",
        "Bluetooth provider cannot run inside an active event loop.",
        status_code=503,
    )


def _bluetooth_unavailable(exc: Exception) -> WatchProviderError:
    message = (
        "Bluetooth adapter is unavailable. Enable Bluetooth and allow local "
        "device access, then retry."
    )
    return WatchProviderError(
        "BLUETOOTH_UNAVAILABLE",
        message,
        details={"reason": str(exc)},
        status_code=503,
    )


def _looks_like_bluetooth_unavailable(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(
        fragment in text
        for fragment in (
            "adapter",
            "bluetooth",
            "radio",
            "winerror -2147020577",
            "no backend",
            "not available",
        )
    )


def _iter_ble_scan_results(raw_devices: Any) -> Iterable[tuple[Any, Any | None]]:
    if isinstance(raw_devices, Mapping):
        values = raw_devices.values()
    else:
        values = raw_devices

    for item in values:
        if isinstance(item, tuple) and item:
            device = item[0]
            advertisement = item[1] if len(item) > 1 else None
            yield device, advertisement
        else:
            yield item, None


def _watch_from_ble_device(
    device: Any,
    advertisement: Any | None,
) -> WatchDiscovery | None:
    bluetooth_device_id = str(getattr(device, "address", "") or "").strip()
    if not bluetooth_device_id:
        return None

    name = _device_name(device, advertisement)
    service_uuids = _advertised_service_uuids(device, advertisement)
    manufacturer_ids = _manufacturer_ids(advertisement)
    model_hint = _model_hint(name, service_uuids, manufacturer_ids)
    if model_hint is None:
        return None

    return WatchDiscovery(
        bluetooth_device_id=bluetooth_device_id,
        name=name or f"Garmin watch {bluetooth_device_id}",
        rssi=_rssi(device, advertisement),
        model_hint=model_hint,
        service_uuids=service_uuids,
    )


def _device_name(device: Any, advertisement: Any | None) -> str:
    local_name = str(getattr(advertisement, "local_name", "") or "").strip()
    if local_name:
        return local_name
    return str(getattr(device, "name", "") or "").strip()


def _advertised_service_uuids(
    device: Any,
    advertisement: Any | None,
) -> tuple[str, ...]:
    advertisement_uuids = getattr(advertisement, "service_uuids", None)
    device_metadata = getattr(device, "metadata", None)
    metadata_uuids = None
    if isinstance(device_metadata, Mapping):
        metadata_uuids = device_metadata.get("uuids")
    raw_uuids = advertisement_uuids or metadata_uuids or ()
    return tuple(sorted(str(uuid).lower() for uuid in raw_uuids))


def _manufacturer_ids(advertisement: Any | None) -> set[int]:
    manufacturer_data = getattr(advertisement, "manufacturer_data", None)
    if not isinstance(manufacturer_data, Mapping):
        return set()
    return {int(identifier) for identifier in manufacturer_data}


def _model_hint(
    name: str,
    service_uuids: tuple[str, ...],
    manufacturer_ids: set[int],
) -> str | None:
    normalized_name = name.lower()
    model = re.search(r"forerunner\s+([0-9]{2,3})", normalized_name)
    if model is not None:
        return f"Forerunner {model.group(1)}"
    if "forerunner" in normalized_name:
        return "Forerunner"
    if "garmin" in normalized_name:
        return "Garmin"
    if GARMIN_COMPANY_IDENTIFIER in manufacturer_ids:
        return "Garmin"
    if service_uuids and any("garmin" in uuid for uuid in service_uuids):
        return "Garmin service"
    return None


def _rssi(device: Any, advertisement: Any | None) -> int:
    raw_rssi = getattr(advertisement, "rssi", None)
    if raw_rssi is None:
        raw_rssi = getattr(device, "rssi", None)
    return int(raw_rssi or 0)


async def _client_services(client: Any) -> Any:
    services = getattr(client, "services", None)
    if services is not None:
        return services
    get_services = getattr(client, "get_services", None)
    if get_services is None:
        return []
    return await get_services()


def _service_uuids(services: Any) -> tuple[str, ...]:
    return tuple(
        sorted(
            str(getattr(service, "uuid", service)).lower()
            for service in services
            if str(getattr(service, "uuid", service)).strip()
        )
    )
