"""Local data export and deletion services."""

from __future__ import annotations

from base64 import b64encode
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload
from starlette import status

from runstats.api.errors import RunStatsError
from runstats.db.models import (
    Activity,
    ChatMessage,
    ChatSession,
    Device,
    DeviceCapabilities,
    DeviceSettings,
    HealthMetric,
    RawImport,
)
from runstats.schemas import (
    ChatMessageRole,
    DataDeletionResponse,
    DataExportActivity,
    DataExportActivityLap,
    DataExportActivitySample,
    DataExportChatMessage,
    DataExportChatSession,
    DataExportCounts,
    DataExportDevice,
    DataExportHealthMetric,
    DataExportRawFile,
    DataExportRawImport,
    DataExportRequest,
    DataExportResponse,
    DeviceCapabilitiesResponse,
    DeviceSettingsResponse,
    PreferredUnits,
    RawFileExportKind,
)


class DataManagementService:
    """Export local data and delete user-controlled data sets."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def export_data(self, request: DataExportRequest) -> DataExportResponse:
        """Serialize local app data without mutating the database."""

        devices = list(
            self.session.scalars(
                select(Device)
                .options(
                    selectinload(Device.settings),
                    selectinload(Device.capabilities),
                )
                .order_by(Device.created_at, Device.id)
            ).all()
        )
        activities = list(
            self.session.scalars(
                select(Activity)
                .options(
                    selectinload(Activity.laps),
                    selectinload(Activity.samples),
                )
                .order_by(Activity.started_at, Activity.id)
            ).all()
        )
        health_metrics = list(
            self.session.scalars(
                select(HealthMetric).order_by(
                    HealthMetric.start_time,
                    HealthMetric.id,
                )
            ).all()
        )
        raw_imports = list(
            self.session.scalars(
                select(RawImport).order_by(RawImport.imported_at, RawImport.id)
            ).all()
        )
        chat_sessions = self._chat_sessions() if request.include_chat_history else []
        raw_files = (
            [_raw_file_export(raw_import) for raw_import in raw_imports]
            if request.include_raw_files
            else []
        )

        return DataExportResponse(
            format_version="runstats.local-data.v1",
            exported_at=datetime.now(UTC),
            include_raw_files=request.include_raw_files,
            include_chat_history=request.include_chat_history,
            counts=DataExportCounts(
                devices=len(devices),
                activities=len(activities),
                activity_laps=sum(len(activity.laps) for activity in activities),
                activity_samples=sum(len(activity.samples) for activity in activities),
                health_metrics=len(health_metrics),
                raw_imports=len(raw_imports),
                raw_files=sum(1 for raw_file in raw_files if raw_file.included),
                chat_sessions=len(chat_sessions),
                chat_messages=sum(
                    len(chat_session.messages) for chat_session in chat_sessions
                ),
            ),
            devices=[_device_export(device) for device in devices],
            activities=[_activity_export(activity) for activity in activities],
            health_metrics=[
                _health_metric_export(metric) for metric in health_metrics
            ],
            raw_imports=[_raw_import_export(raw_import) for raw_import in raw_imports],
            raw_files=raw_files,
            chat_sessions=[
                _chat_session_export(chat_session) for chat_session in chat_sessions
            ],
        )

    def delete_chat_history(self) -> DataDeletionResponse:
        """Delete all local chat sessions and messages."""

        deleted_sessions = _count(self.session, ChatSession)
        deleted_messages = _count(self.session, ChatMessage)
        chat_sessions = list(self.session.scalars(select(ChatSession)).all())
        for chat_session in chat_sessions:
            self.session.delete(chat_session)
        self.session.commit()
        return DataDeletionResponse(
            deleted_chat_sessions=deleted_sessions,
            deleted_chat_messages=deleted_messages,
        )

    def delete_imported_data_for_device(self, device_id: str) -> DataDeletionResponse:
        """Delete imported activity, health, and raw archive data for one device."""

        device = self.session.get(Device, device_id)
        if device is None:
            raise RunStatsError(
                "DEVICE_NOT_FOUND",
                "Device not found.",
                details={"device_id": device_id},
                status_code=status.HTTP_404_NOT_FOUND,
            )

        activities = list(
            self.session.scalars(
                select(Activity)
                .where(Activity.device_id == device_id)
                .options(
                    selectinload(Activity.laps),
                    selectinload(Activity.samples),
                )
            ).all()
        )
        health_metrics = list(
            self.session.scalars(
                select(HealthMetric).where(HealthMetric.device_id == device_id)
            ).all()
        )
        raw_imports = list(
            self.session.scalars(
                select(RawImport).where(RawImport.device_id == device_id)
            ).all()
        )
        raw_paths = [
            Path(raw_import.storage_path).expanduser()
            for raw_import in raw_imports
        ]
        deleted_laps = sum(len(activity.laps) for activity in activities)
        deleted_samples = sum(len(activity.samples) for activity in activities)

        for activity in activities:
            self.session.delete(activity)
        for metric in health_metrics:
            self.session.delete(metric)
        for raw_import in raw_imports:
            self.session.delete(raw_import)
        self.session.commit()

        deleted_files = 0
        missing_files = 0
        for path in _dedupe_paths(raw_paths):
            if not path.exists():
                missing_files += 1
                continue
            try:
                path.unlink()
                deleted_files += 1
            except OSError:
                missing_files += 1

        return DataDeletionResponse(
            device_id=device_id,
            deleted_activities=len(activities),
            deleted_activity_laps=deleted_laps,
            deleted_activity_samples=deleted_samples,
            deleted_health_metrics=len(health_metrics),
            deleted_raw_imports=len(raw_imports),
            deleted_raw_files=deleted_files,
            missing_raw_files=missing_files,
        )

    def _chat_sessions(self) -> list[ChatSession]:
        return list(
            self.session.scalars(
                select(ChatSession)
                .options(selectinload(ChatSession.messages))
                .order_by(ChatSession.created_at, ChatSession.id)
            ).all()
        )


def _count(session: Session, model: type[object]) -> int:
    value = session.scalar(select(func.count()).select_from(model))
    return int(value or 0)


def _device_export(device: Device) -> DataExportDevice:
    return DataExportDevice(
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
            _device_settings_export(device.id, device.settings)
            if device.settings is not None
            else None
        ),
        capabilities=(
            _device_capabilities_export(device.id, device.capabilities)
            if device.capabilities is not None
            else None
        ),
    )


def _device_settings_export(
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


def _device_capabilities_export(
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


def _activity_export(activity: Activity) -> DataExportActivity:
    return DataExportActivity(
        id=activity.id,
        device_id=activity.device_id,
        source_activity_id=activity.source_activity_id,
        sport=activity.sport,
        name=activity.name,
        started_at=activity.started_at,
        duration_seconds=activity.duration_seconds,
        distance_meters=activity.distance_meters,
        calories=activity.calories,
        avg_heart_rate=activity.avg_heart_rate,
        max_heart_rate=activity.max_heart_rate,
        avg_cadence=activity.avg_cadence,
        avg_pace_seconds_per_km=activity.avg_pace_seconds_per_km,
        elevation_gain_meters=activity.elevation_gain_meters,
        training_effect=activity.training_effect,
        raw_file_id=activity.raw_file_id,
        created_at=activity.created_at,
        laps=[
            DataExportActivityLap(
                id=lap.id,
                lap_index=lap.lap_index,
                started_at=lap.started_at,
                duration_seconds=lap.duration_seconds,
                distance_meters=lap.distance_meters,
                avg_heart_rate=lap.avg_heart_rate,
                avg_pace_seconds_per_km=lap.avg_pace_seconds_per_km,
            )
            for lap in activity.laps
        ],
        samples=[
            DataExportActivitySample(
                id=sample.id,
                sample_time=sample.sample_time,
                elapsed_seconds=sample.elapsed_seconds,
                distance_meters=sample.distance_meters,
                latitude=sample.latitude,
                longitude=sample.longitude,
                elevation_meters=sample.elevation_meters,
                heart_rate=sample.heart_rate,
                cadence=sample.cadence,
                power_watts=sample.power_watts,
                speed_meters_per_second=sample.speed_meters_per_second,
            )
            for sample in activity.samples
        ],
    )


def _health_metric_export(metric: HealthMetric) -> DataExportHealthMetric:
    return DataExportHealthMetric(
        id=metric.id,
        device_id=metric.device_id,
        metric_type=metric.metric_type,
        start_time=metric.start_time,
        end_time=metric.end_time,
        value=metric.value,
        unit=metric.unit,
        source_record_id=metric.source_record_id,
    )


def _raw_import_export(raw_import: RawImport) -> DataExportRawImport:
    return DataExportRawImport(
        id=raw_import.id,
        device_id=raw_import.device_id,
        source_id=raw_import.source_id,
        kind=raw_import.kind,
        sha256=raw_import.sha256,
        storage_path=raw_import.storage_path,
        imported_at=raw_import.imported_at,
    )


def _raw_file_export(raw_import: RawImport) -> DataExportRawFile:
    path = Path(raw_import.storage_path).expanduser()
    kind = _raw_file_kind(raw_import.kind)
    if not path.exists() or not path.is_file():
        return DataExportRawFile(
            raw_import_id=raw_import.id,
            source_id=raw_import.source_id,
            kind=kind,
            sha256=raw_import.sha256,
            storage_path=raw_import.storage_path,
            byte_size=0,
            content_base64=None,
            included=False,
            missing=True,
            error="Archived raw file was not found.",
        )

    try:
        content = path.read_bytes()
    except OSError:
        return DataExportRawFile(
            raw_import_id=raw_import.id,
            source_id=raw_import.source_id,
            kind=kind,
            sha256=raw_import.sha256,
            storage_path=raw_import.storage_path,
            byte_size=0,
            content_base64=None,
            included=False,
            missing=False,
            error="Archived raw file could not be read.",
        )

    return DataExportRawFile(
        raw_import_id=raw_import.id,
        source_id=raw_import.source_id,
        kind=kind,
        sha256=raw_import.sha256,
        storage_path=raw_import.storage_path,
        byte_size=len(content),
        content_base64=b64encode(content).decode("ascii"),
        included=True,
        missing=False,
        error=None,
    )


def _raw_file_kind(kind: str) -> RawFileExportKind:
    if kind in {"activity_fit", "health_payload"}:
        return cast(RawFileExportKind, kind)
    return "unknown"


def _chat_session_export(chat_session: ChatSession) -> DataExportChatSession:
    return DataExportChatSession(
        id=chat_session.id,
        title=chat_session.title,
        created_at=chat_session.created_at,
        updated_at=chat_session.updated_at,
        messages=[
            DataExportChatMessage(
                id=message.id,
                session_id=message.session_id,
                role=cast(ChatMessageRole, message.role),
                content=message.content,
                tool_trace_json=message.tool_trace_json,
                created_at=message.created_at,
            )
            for message in chat_session.messages
        ],
    )


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    deduped: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            deduped.append(resolved)
    return deduped
