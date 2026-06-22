"""SQLAlchemy models for RunStats local data."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    """Return the current UTC timestamp."""

    return datetime.now(UTC)


def new_uuid() -> str:
    """Return a UUID string for application primary keys."""

    return str(uuid4())


class Base(DeclarativeBase):
    """Base class for all database models."""

    type_annotation_map = {str: Text()}


class Device(Base):
    """Known Garmin watch or compatible device."""

    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(nullable=False)
    model: Mapped[str] = mapped_column(nullable=False)
    bluetooth_address: Mapped[str] = mapped_column(nullable=False, unique=True)
    serial_number: Mapped[str | None] = mapped_column(nullable=True)
    firmware_version: Mapped[str | None] = mapped_column(nullable=True)
    paired_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    settings: Mapped[DeviceSettings | None] = relationship(
        back_populates="device",
        cascade="all, delete-orphan",
    )
    capabilities: Mapped[DeviceCapabilities | None] = relationship(
        back_populates="device",
        cascade="all, delete-orphan",
    )
    sync_runs: Mapped[list[SyncRun]] = relationship(back_populates="device")
    activities: Mapped[list[Activity]] = relationship(back_populates="device")
    health_metrics: Mapped[list[HealthMetric]] = relationship(back_populates="device")
    raw_imports: Mapped[list[RawImport]] = relationship(back_populates="device")


class DeviceSettings(Base):
    """Per-device sync and display preferences."""

    __tablename__ = "device_settings"

    device_id: Mapped[str] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"),
        primary_key=True,
    )
    auto_sync_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    sync_interval_minutes: Mapped[int] = mapped_column(
        Integer, default=60, nullable=False
    )
    import_activities: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    import_health_stats: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    preferred_units: Mapped[str] = mapped_column(default="metric", nullable=False)
    historical_fit_import_folder: Mapped[str | None] = mapped_column(nullable=True)

    device: Mapped[Device] = relationship(back_populates="settings")


class DeviceCapabilities(Base):
    """Latest known import capabilities for a configured device."""

    __tablename__ = "device_capabilities"

    device_id: Mapped[str] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"),
        primary_key=True,
    )
    supports_ble_activity_export: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    supports_ble_health_export: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    supports_folder_import: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    capability_notes: Mapped[str | None] = mapped_column(nullable=True)
    probed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    device: Mapped[Device] = relationship(back_populates="capabilities")


class AppSettings(Base):
    """Single-row local application preferences."""

    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    raw_archive_path: Mapped[str] = mapped_column(nullable=False)
    chat_provider: Mapped[str] = mapped_column(default="local", nullable=False)
    local_chat_provider: Mapped[str] = mapped_column(default="ollama", nullable=False)
    hosted_chat_provider: Mapped[str | None] = mapped_column(nullable=True)
    chat_retention_policy: Mapped[str] = mapped_column(
        default="retain_until_deleted",
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class SyncRun(Base):
    """One sync attempt against a configured device."""

    __tablename__ = "sync_runs"
    __table_args__ = (
        Index("ix_sync_runs_device_started", "device_id", "started_at"),
        Index("ix_sync_runs_status_started", "status", "started_at"),
    )

    id: Mapped[str] = mapped_column(primary_key=True, default=new_uuid)
    device_id: Mapped[str] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    activities_imported: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    health_records_imported: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(nullable=True)

    device: Mapped[Device] = relationship(back_populates="sync_runs")


class Activity(Base):
    """One imported activity summary."""

    __tablename__ = "activities"
    __table_args__ = (
        UniqueConstraint(
            "device_id",
            "source_activity_id",
            name="uq_activities_device_source",
        ),
        Index("ix_activities_device_started", "device_id", "started_at"),
        Index("ix_activities_sport_started", "sport", "started_at"),
    )

    id: Mapped[str] = mapped_column(primary_key=True, default=new_uuid)
    device_id: Mapped[str] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_activity_id: Mapped[str] = mapped_column(nullable=False)
    sport: Mapped[str] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    duration_seconds: Mapped[float] = mapped_column(nullable=False)
    distance_meters: Mapped[float] = mapped_column(nullable=False)
    calories: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avg_heart_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_heart_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avg_cadence: Mapped[float | None] = mapped_column(nullable=True)
    avg_pace_seconds_per_km: Mapped[float | None] = mapped_column(nullable=True)
    elevation_gain_meters: Mapped[float | None] = mapped_column(nullable=True)
    training_effect: Mapped[float | None] = mapped_column(nullable=True)
    raw_file_id: Mapped[str | None] = mapped_column(
        ForeignKey("raw_imports.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    device: Mapped[Device] = relationship(back_populates="activities")
    raw_import: Mapped[RawImport | None] = relationship(back_populates="activities")
    laps: Mapped[list[ActivityLap]] = relationship(
        back_populates="activity",
        cascade="all, delete-orphan",
        order_by="ActivityLap.lap_index",
    )
    samples: Mapped[list[ActivitySample]] = relationship(
        back_populates="activity",
        cascade="all, delete-orphan",
        order_by="ActivitySample.elapsed_seconds",
    )


class ActivityLap(Base):
    """Lap or split summary for an activity."""

    __tablename__ = "activity_laps"
    __table_args__ = (
        UniqueConstraint("activity_id", "lap_index", name="uq_activity_laps_order"),
        Index("ix_activity_laps_activity_order", "activity_id", "lap_index"),
    )

    id: Mapped[str] = mapped_column(primary_key=True, default=new_uuid)
    activity_id: Mapped[str] = mapped_column(
        ForeignKey("activities.id", ondelete="CASCADE"),
        nullable=False,
    )
    lap_index: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    duration_seconds: Mapped[float] = mapped_column(nullable=False)
    distance_meters: Mapped[float] = mapped_column(nullable=False)
    avg_heart_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avg_pace_seconds_per_km: Mapped[float | None] = mapped_column(nullable=True)

    activity: Mapped[Activity] = relationship(back_populates="laps")


class ActivitySample(Base):
    """Time-series sample for activity charts and maps."""

    __tablename__ = "activity_samples"
    __table_args__ = (
        Index("ix_activity_samples_activity_elapsed", "activity_id", "elapsed_seconds"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    activity_id: Mapped[str] = mapped_column(
        ForeignKey("activities.id", ondelete="CASCADE"),
        nullable=False,
    )
    sample_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    elapsed_seconds: Mapped[float] = mapped_column(nullable=False)
    distance_meters: Mapped[float | None] = mapped_column(nullable=True)
    latitude: Mapped[float | None] = mapped_column(nullable=True)
    longitude: Mapped[float | None] = mapped_column(nullable=True)
    elevation_meters: Mapped[float | None] = mapped_column(nullable=True)
    heart_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cadence: Mapped[float | None] = mapped_column(nullable=True)
    power_watts: Mapped[float | None] = mapped_column(nullable=True)
    speed_meters_per_second: Mapped[float | None] = mapped_column(nullable=True)

    activity: Mapped[Activity] = relationship(back_populates="samples")


class HealthMetric(Base):
    """Timestamped health metric value."""

    __tablename__ = "health_metrics"
    __table_args__ = (
        Index("ix_health_metrics_metric_start", "metric_type", "start_time"),
        Index("ix_health_metrics_device_start", "device_id", "start_time"),
        UniqueConstraint(
            "device_id",
            "metric_type",
            "source_record_id",
            name="uq_health_metrics_source_record",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
    )
    metric_type: Mapped[str] = mapped_column(nullable=False)
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    end_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    value: Mapped[float] = mapped_column(nullable=False)
    unit: Mapped[str] = mapped_column(nullable=False)
    source_record_id: Mapped[str | None] = mapped_column(nullable=True)

    device: Mapped[Device] = relationship(back_populates="health_metrics")


class RawImport(Base):
    """Metadata for a retained raw export file or payload."""

    __tablename__ = "raw_imports"
    __table_args__ = (
        UniqueConstraint(
            "device_id", "source_id", "kind", name="uq_raw_imports_source"
        ),
        Index("ix_raw_imports_sha256", "sha256"),
    )

    id: Mapped[str] = mapped_column(primary_key=True, default=new_uuid)
    device_id: Mapped[str] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_id: Mapped[str] = mapped_column(nullable=False)
    kind: Mapped[str] = mapped_column(nullable=False)
    sha256: Mapped[str] = mapped_column(nullable=False)
    storage_path: Mapped[str] = mapped_column(nullable=False)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    device: Mapped[Device] = relationship(back_populates="raw_imports")
    activities: Mapped[list[Activity]] = relationship(back_populates="raw_import")


class ChatSession(Base):
    """Chatbot conversation."""

    __tablename__ = "chat_sessions"
    __table_args__ = (Index("ix_chat_sessions_updated", "updated_at"),)

    id: Mapped[str] = mapped_column(primary_key=True, default=new_uuid)
    title: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    messages: Mapped[list[ChatMessage]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )


class ChatMessage(Base):
    """Persisted user, assistant, system, or tool message."""

    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("ix_chat_messages_session_created", "session_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(primary_key=True, default=new_uuid)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(nullable=False)
    content: Mapped[str] = mapped_column(nullable=False)
    tool_trace_json: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    session: Mapped[ChatSession] = relationship(back_populates="messages")
