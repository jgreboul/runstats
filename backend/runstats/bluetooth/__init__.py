"""Bluetooth provider adapters for Garmin watch workflows."""

from runstats.bluetooth.factory import create_watch_provider
from runstats.bluetooth.fake import FAKE_WATCHES, FakeWatchProfile, FakeWatchProvider
from runstats.bluetooth.provider import (
    WatchCapabilityProbe,
    WatchConnectionResult,
    WatchDiscovery,
    WatchExportPayload,
    WatchIdentity,
    WatchProvider,
    WatchProviderError,
    WatchProviderStatus,
)

__all__ = [
    "FAKE_WATCHES",
    "FakeWatchProfile",
    "FakeWatchProvider",
    "WatchCapabilityProbe",
    "WatchConnectionResult",
    "WatchDiscovery",
    "WatchExportPayload",
    "WatchIdentity",
    "WatchProvider",
    "WatchProviderError",
    "WatchProviderStatus",
    "create_watch_provider",
]
