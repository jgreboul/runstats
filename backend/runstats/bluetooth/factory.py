"""Factory for configured watch provider adapters."""

from __future__ import annotations

from runstats.bluetooth.bleak_provider import BleakWatchProvider
from runstats.bluetooth.fake import FakeWatchProvider
from runstats.bluetooth.provider import WatchProvider
from runstats.config import WatchProviderName


def create_watch_provider(provider_name: WatchProviderName) -> WatchProvider:
    """Build the configured watch provider."""

    if provider_name == "fake":
        return FakeWatchProvider()
    return BleakWatchProvider()
