from types import SimpleNamespace

import pytest

import runstats.bluetooth.bleak_provider as bleak_provider
from runstats.bluetooth import WatchProviderError
from runstats.bluetooth.bleak_provider import BleakWatchProvider


def test_bleak_scanner_identifies_forerunner_name_and_garmin_advertising(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Scanner:
        @staticmethod
        async def discover(
            timeout: float,
            return_adv: bool,
        ) -> dict[str, tuple[object, object]]:
            assert timeout == 3.0
            assert return_adv is True
            return {
                "forerunner": (
                    SimpleNamespace(address="AA:BB", name="Garmin Forerunner 955"),
                    SimpleNamespace(
                        local_name=None,
                        manufacturer_data={},
                        rssi=-41,
                        service_uuids=[],
                    ),
                ),
                "manufacturer": (
                    SimpleNamespace(address="CC:DD", name=None),
                    SimpleNamespace(
                        local_name=None,
                        manufacturer_data={0x0087: b"garmin"},
                        rssi=-67,
                        service_uuids=[],
                    ),
                ),
                "other": (
                    SimpleNamespace(address="EE:FF", name="Keyboard"),
                    SimpleNamespace(
                        local_name=None,
                        manufacturer_data={},
                        rssi=-20,
                        service_uuids=[],
                    ),
                ),
            }

    monkeypatch.setattr(
        bleak_provider,
        "_load_bleak",
        lambda: SimpleNamespace(BleakScanner=Scanner),
    )

    watches = BleakWatchProvider().scan(3)

    assert [watch.bluetooth_device_id for watch in watches] == ["AA:BB", "CC:DD"]
    assert watches[0].model_hint == "Forerunner 955"
    assert watches[1].name == "Garmin watch CC:DD"
    assert watches[1].model_hint == "Garmin"


def test_bleak_scanner_reports_bluetooth_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Scanner:
        @staticmethod
        async def discover(timeout: float, return_adv: bool) -> object:
            _ = timeout
            _ = return_adv
            raise RuntimeError("Bluetooth adapter unavailable")

    monkeypatch.setattr(
        bleak_provider,
        "_load_bleak",
        lambda: SimpleNamespace(BleakScanner=Scanner),
    )

    with pytest.raises(WatchProviderError) as exc_info:
        BleakWatchProvider().scan(5)

    assert exc_info.value.code == "BLUETOOTH_UNAVAILABLE"
    assert exc_info.value.status_code == 503


def test_bleak_capability_probe_reads_services(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Client:
        def __init__(self, address: str, timeout: float) -> None:
            assert address == "AA:BB"
            assert timeout == 15.0
            self.is_connected = True
            self.services = [SimpleNamespace(uuid="activity-export-service")]

        async def __aenter__(self) -> "Client":
            return self

        async def __aexit__(
            self,
            exc_type: object,
            exc: object,
            traceback: object,
        ) -> None:
            _ = exc_type
            _ = exc
            _ = traceback

    monkeypatch.setattr(
        bleak_provider,
        "_load_bleak",
        lambda: SimpleNamespace(BleakClient=Client),
    )
    monkeypatch.setattr(
        bleak_provider,
        "DIRECT_EXPORT_SERVICE_UUIDS",
        ("activity-export-service",),
    )

    probe = BleakWatchProvider().probe_capabilities("AA:BB")

    assert probe.supports_ble_activity_export is True
    assert probe.supports_ble_health_export is False
    assert probe.supports_folder_import is True
    assert probe.observed_services == ("activity-export-service",)
