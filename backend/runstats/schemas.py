"""Typed service and API schemas for RunStats."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ActivitySummaryBucketName = Literal["day", "week", "month", "year"]
HealthSeriesBucketName = Literal["day", "week", "month"]
TrendBucketName = Literal["day", "week", "month"]
PreferredUnits = Literal["metric", "imperial"]
ChatProvider = Literal["local", "hosted", "disabled"]
LocalChatProvider = Literal["ollama"]
HostedChatProvider = Literal["openai", "anthropic"]
ChatRetentionPolicy = Literal[
    "retain_until_deleted",
    "retain_90_days",
    "do_not_retain",
]


class SerializableModel(BaseModel):
    """Base model configured for service-layer serialization."""

    model_config = ConfigDict(from_attributes=True)


class ActivityListItem(SerializableModel):
    """Compact activity row used by list and ranking responses."""

    id: str
    device_id: str
    sport: str
    name: str
    started_at: datetime
    duration_seconds: float
    distance_meters: float
    avg_pace_seconds_per_km: float | None
    avg_heart_rate: int | None
    elevation_gain_meters: float | None


class ActivityListResponse(SerializableModel):
    """Paginated activity list."""

    items: list[ActivityListItem]
    total: int
    limit: int
    offset: int


class ActivityLapResponse(SerializableModel):
    """Lap summary in activity detail responses."""

    id: str
    lap_index: int
    started_at: datetime
    duration_seconds: float
    distance_meters: float
    avg_heart_rate: int | None
    avg_pace_seconds_per_km: float | None


class ActivitySummaryStats(SerializableModel):
    """Derived activity statistics."""

    distance_kilometers: float
    avg_speed_meters_per_second: float | None
    avg_pace_seconds_per_km: float | None
    lap_count: int
    sample_count: int
    gps_sample_count: int
    has_gps: bool


class ActivityDetailResponse(SerializableModel):
    """Activity detail including laps and derived statistics."""

    id: str
    device_id: str
    source_activity_id: str
    sport: str
    name: str
    started_at: datetime
    duration_seconds: float
    distance_meters: float
    calories: int | None
    avg_heart_rate: int | None
    max_heart_rate: int | None
    avg_cadence: float | None
    avg_pace_seconds_per_km: float | None
    elevation_gain_meters: float | None
    training_effect: float | None
    summary: ActivitySummaryStats
    laps: list[ActivityLapResponse]


class ActivitySampleResponse(SerializableModel):
    """Chart-ready activity sample."""

    id: int
    sample_time: datetime
    elapsed_seconds: float
    distance_meters: float | None
    latitude: float | None
    longitude: float | None
    elevation_meters: float | None
    heart_rate: int | None
    cadence: float | None
    power_watts: float | None
    speed_meters_per_second: float | None


class ActivitySamplesResponse(SerializableModel):
    """Ordered samples for one activity."""

    activity_id: str
    samples: list[ActivitySampleResponse]


class ActivitySummaryBucket(SerializableModel):
    """Aggregated activity totals for one calendar bucket."""

    bucket_start: datetime
    bucket_end: datetime
    activity_count: int
    distance_meters: float
    duration_seconds: float
    avg_pace_seconds_per_km: float | None
    avg_heart_rate: float | None
    longest_distance_meters: float


class ActivitySummaryResponse(SerializableModel):
    """Activity aggregate totals and buckets."""

    bucket: ActivitySummaryBucketName
    from_time: datetime | None = Field(serialization_alias="from")
    to_time: datetime | None = Field(serialization_alias="to")
    total_activities: int
    total_distance_meters: float
    total_duration_seconds: float
    avg_pace_seconds_per_km: float | None
    avg_heart_rate: float | None
    buckets: list[ActivitySummaryBucket]


class HealthMetricDescriptor(SerializableModel):
    """Discovered health metric metadata."""

    metric_type: str
    unit: str
    record_count: int
    first_start_time: datetime
    last_start_time: datetime


class HealthMetricsResponse(SerializableModel):
    """Available health metrics."""

    metrics: list[HealthMetricDescriptor]


class HealthSeriesPoint(SerializableModel):
    """Aggregated health metric point for charts."""

    bucket_start: datetime
    bucket_end: datetime
    value: float
    average_value: float
    total_value: float
    min_value: float
    max_value: float
    record_count: int


class HealthSeriesResponse(SerializableModel):
    """Health metric time-series response."""

    metric_type: str
    unit: str | None
    bucket: HealthSeriesBucketName
    from_time: datetime | None = Field(serialization_alias="from")
    to_time: datetime | None = Field(serialization_alias="to")
    metric_available: bool
    message: str | None
    points: list[HealthSeriesPoint]


class SyncRunResponse(SerializableModel):
    """Safe sync run serialization."""

    id: str
    device_id: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    duration_seconds: float | None
    activities_imported: int
    health_records_imported: int
    error_summary: str | None


class SyncRunListResponse(SerializableModel):
    """Paginated sync run list."""

    items: list[SyncRunResponse]
    total: int
    limit: int
    offset: int


class DiscoveredWatch(SerializableModel):
    """Watch discovered by the configured provider."""

    id: str
    name: str
    rssi: int
    model_hint: str | None
    is_known: bool


class DeviceScanRequest(SerializableModel):
    """Request body for a watch scan."""

    scan_seconds: int = Field(default=10, ge=1, le=60)


class DeviceScanResponse(SerializableModel):
    """Watches discovered during a scan."""

    devices: list[DiscoveredWatch]


class DevicePairRequest(SerializableModel):
    """Request body for pairing or registering a watch."""

    bluetooth_device_id: str = Field(min_length=1)
    display_name: str | None = Field(default=None, min_length=1, max_length=120)


class DeviceSettingsResponse(SerializableModel):
    """Per-device sync and display settings."""

    device_id: str
    auto_sync_enabled: bool
    sync_interval_minutes: int
    import_activities: bool
    import_health_stats: bool
    preferred_units: PreferredUnits
    historical_fit_import_folder: str | None


class DeviceSettingsPatchRequest(SerializableModel):
    """Partial per-device settings update."""

    auto_sync_enabled: bool | None = None
    sync_interval_minutes: int | None = Field(default=None, ge=5, le=1440)
    import_activities: bool | None = None
    import_health_stats: bool | None = None
    preferred_units: PreferredUnits | None = None
    historical_fit_import_folder: str | None = Field(default=None, max_length=500)


class DeviceCapabilitiesResponse(SerializableModel):
    """Latest known watch import capabilities."""

    device_id: str
    supports_ble_activity_export: bool
    supports_ble_health_export: bool
    supports_folder_import: bool
    capability_notes: str | None
    probed_at: datetime | None


class DeviceResponse(SerializableModel):
    """Configured watch with settings and capabilities."""

    id: str
    name: str
    model: str
    bluetooth_address: str
    serial_number: str | None
    firmware_version: str | None
    paired_at: datetime | None
    last_seen_at: datetime | None
    created_at: datetime
    updated_at: datetime
    settings: DeviceSettingsResponse
    capabilities: DeviceCapabilitiesResponse


class DeviceListResponse(SerializableModel):
    """Configured watch list."""

    items: list[DeviceResponse]


class DeviceConnectionTestResponse(SerializableModel):
    """Result of a watch connection test."""

    device_id: str
    status: Literal["connected", "failed"]
    success: bool
    message: str
    last_seen_at: datetime | None
    error_code: str | None = None


class ManualSyncRequest(SerializableModel):
    """Request body for starting a manual sync."""

    device_id: str
    include_activities: bool = True
    include_health: bool = True

    @model_validator(mode="after")
    def at_least_one_import_type(self) -> ManualSyncRequest:
        """Require a meaningful sync request."""

        if not self.include_activities and not self.include_health:
            raise ValueError("At least one import type must be selected.")
        return self


class SyncProgressEvent(SerializableModel):
    """Progress event streamed for a fake sync run."""

    sync_run_id: str
    type: Literal["progress", "completed", "failed"]
    stage: str
    message: str
    percent: int = Field(ge=0, le=100)


class AppSettingsResponse(SerializableModel):
    """Local application settings."""

    raw_archive_path: str
    chat_provider: ChatProvider
    local_chat_provider: LocalChatProvider
    hosted_chat_provider: HostedChatProvider | None
    chat_retention_policy: ChatRetentionPolicy
    created_at: datetime
    updated_at: datetime


class AppSettingsPatchRequest(SerializableModel):
    """Partial application settings update."""

    raw_archive_path: str | None = None
    chat_provider: ChatProvider | None = None
    local_chat_provider: LocalChatProvider | None = None
    hosted_chat_provider: HostedChatProvider | None = None
    chat_retention_policy: ChatRetentionPolicy | None = None


class RunningSummaryBucket(SerializableModel):
    """Running summary bucket used by analytics methods."""

    bucket_start: datetime
    bucket_end: datetime
    activity_count: int
    distance_meters: float
    duration_seconds: float
    avg_pace_seconds_per_km: float | None
    avg_heart_rate: float | None


class RunningSummaryResult(SerializableModel):
    """Weekly or monthly running summary."""

    bucket: Literal["week", "month"]
    from_time: datetime | None
    to_time: datetime | None
    total_activities: int
    total_distance_meters: float
    total_duration_seconds: float
    avg_pace_seconds_per_km: float | None
    buckets: list[RunningSummaryBucket]


class ActivityRankingResult(SerializableModel):
    """Ranked activity analytics result."""

    ranking: Literal["fastest_by_distance_threshold", "longest_runs"]
    from_time: datetime | None
    to_time: datetime | None
    min_distance_meters: float | None
    items: list[ActivityListItem]


class TrendPoint(SerializableModel):
    """Trend value for a time bucket."""

    bucket_start: datetime
    bucket_end: datetime
    value: float | None
    record_count: int


class TrendResult(SerializableModel):
    """Activity trend analytics result."""

    metric: Literal["pace_seconds_per_km", "heart_rate_bpm"]
    bucket: TrendBucketName
    from_time: datetime | None
    to_time: datetime | None
    points: list[TrendPoint]


class HealthComparisonWindow(SerializableModel):
    """Aggregated values for one health comparison window."""

    from_time: datetime
    to_time: datetime
    value: float | None
    record_count: int


class HealthMetricComparisonResult(SerializableModel):
    """Health metric comparison across two time windows."""

    metric_type: str
    unit: str | None
    aggregation: Literal["average", "sum"]
    baseline: HealthComparisonWindow
    comparison: HealthComparisonWindow
    delta_value: float | None
    percent_change: float | None
