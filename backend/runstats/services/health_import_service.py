"""Health metric import orchestration services."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from shutil import copyfileobj
from typing import Literal, Protocol

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from runstats.api.errors import RunStatsError
from runstats.bluetooth import WatchExportPayload
from runstats.config import Settings
from runstats.db.models import AppSettings, Device, HealthMetric, RawImport
from runstats.importers import (
    HealthImportWarning,
    HealthPayloadParseError,
    HealthPayloadParser,
    ParsedHealthMetric,
    ParsedHealthPayload,
)

HEALTH_PAYLOAD_KIND = "health_payload"

HealthImportStatus = Literal["created", "skipped", "failed"]


class HealthParser(Protocol):
    """Parser contract used by the health import service."""

    def parse(
        self,
        payload: bytes,
        *,
        sha256: str,
        source_id: str,
        source_name: str | None = None,
    ) -> ParsedHealthPayload:
        """Parse one raw health payload."""


@dataclass(frozen=True)
class HealthPayloadImportResult:
    """Import result for one raw health payload."""

    source_id: str
    status: HealthImportStatus
    message: str
    sha256: str | None = None
    raw_import_id: str | None = None
    archived: bool = False
    records_created: int = 0
    records_skipped: int = 0
    warnings: list[HealthImportWarning] | None = None


@dataclass(frozen=True)
class HealthImportSummary:
    """Summary for a multi-payload health import run."""

    records_created: int
    records_skipped: int
    payloads_failed: int
    raw_files_archived: int
    payloads: list[HealthPayloadImportResult]


class HealthImportService:
    """Import health payloads into normalized health metric records."""

    def __init__(
        self,
        session: Session,
        runtime_settings: Settings,
        parser: HealthParser | None = None,
        *,
        now: datetime | None = None,
    ) -> None:
        self.session = session
        self.runtime_settings = runtime_settings
        self.parser = parser or HealthPayloadParser()
        self.now = now

    def import_health_file(
        self,
        *,
        device_id: str,
        file_path: Path,
    ) -> HealthPayloadImportResult:
        """Import one JSON health payload from disk."""

        path = file_path.expanduser()
        if not path.exists() or not path.is_file():
            return HealthPayloadImportResult(
                source_id=str(path),
                status="failed",
                message="Health payload file was not found.",
            )

        try:
            payload = path.read_bytes()
        except OSError:
            return HealthPayloadImportResult(
                source_id=str(path),
                status="failed",
                message="Health payload file could not be read.",
            )

        return self.import_health_payload(
            device_id=device_id,
            payload=payload,
            source_id=str(path.resolve()),
            source_name=path.stem,
        )

    def import_health_payload(
        self,
        *,
        device_id: str,
        payload: bytes,
        source_id: str,
        source_name: str | None = None,
    ) -> HealthPayloadImportResult:
        """Import one raw health payload."""

        self._get_device(device_id)
        payload_sha = sha256(payload).hexdigest()

        duplicate_raw = self._raw_import_by_sha(device_id, payload_sha)
        if duplicate_raw is not None:
            return HealthPayloadImportResult(
                source_id=source_id,
                status="skipped",
                message="Duplicate raw health payload already archived.",
                sha256=payload_sha,
                raw_import_id=duplicate_raw.id,
            )

        duplicate_source = self._raw_import_by_source(device_id, source_id)
        if duplicate_source is not None:
            return HealthPayloadImportResult(
                source_id=source_id,
                status="skipped",
                message="Raw health source was already archived.",
                sha256=payload_sha,
                raw_import_id=duplicate_source.id,
            )

        try:
            parsed = self.parser.parse(
                payload,
                sha256=payload_sha,
                source_id=source_id,
                source_name=source_name,
            )
        except HealthPayloadParseError as exc:
            return HealthPayloadImportResult(
                source_id=source_id,
                status="failed",
                message=str(exc),
                sha256=payload_sha,
            )

        warnings = list(parsed.warnings)
        metrics: list[HealthMetric] = []
        duplicates_skipped = 0
        for record in parsed.records:
            if self._duplicate_metric(device_id, record) is not None:
                duplicates_skipped += 1
                warnings.append(
                    HealthImportWarning(
                        source_id=source_id,
                        message="Duplicate health metric already imported.",
                        metric_type=record.metric_type,
                    )
                )
                continue
            metrics.append(_health_metric_model(device_id, record))

        records_skipped = len(parsed.warnings) + duplicates_skipped
        if not metrics:
            return HealthPayloadImportResult(
                source_id=source_id,
                status="skipped",
                message="No new supported health records were imported.",
                sha256=payload_sha,
                records_created=0,
                records_skipped=records_skipped,
                warnings=warnings,
            )

        archived_path = self._archive_payload(
            device_id=device_id,
            payload=payload,
            payload_sha=payload_sha,
            source_id=source_id,
        )
        raw_import = RawImport(
            device_id=device_id,
            source_id=source_id,
            kind=HEALTH_PAYLOAD_KIND,
            sha256=payload_sha,
            storage_path=str(archived_path),
            imported_at=self._now(),
        )
        try:
            self.session.add(raw_import)
            self.session.add_all(metrics)
            self.session.commit()
        except SQLAlchemyError:
            self.session.rollback()
            _remove_if_unreferenced(archived_path)
            return HealthPayloadImportResult(
                source_id=source_id,
                status="failed",
                message="Health import could not be persisted.",
                sha256=payload_sha,
                warnings=warnings,
            )

        self.session.refresh(raw_import)
        return HealthPayloadImportResult(
            source_id=source_id,
            status="created",
            message="Health records imported.",
            sha256=payload_sha,
            raw_import_id=raw_import.id,
            archived=True,
            records_created=len(metrics),
            records_skipped=records_skipped,
            warnings=warnings,
        )

    def import_watch_health_exports(
        self,
        *,
        device_id: str,
        payloads: Iterable[WatchExportPayload],
    ) -> HealthImportSummary:
        """Import raw health payloads exported by a watch provider."""

        results: list[HealthPayloadImportResult] = []
        for payload in payloads:
            if payload.kind != "health":
                results.append(
                    HealthPayloadImportResult(
                        source_id=payload.source_id,
                        status="skipped",
                        message="Skipped non-health watch payload.",
                    )
                )
                continue

            results.append(
                self.import_health_payload(
                    device_id=device_id,
                    payload=payload.payload,
                    source_id=payload.source_id,
                    source_name=Path(payload.source_id).stem or payload.source_id,
                )
            )
        return _summary(results)

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

    def _raw_import_by_sha(self, device_id: str, payload_sha: str) -> RawImport | None:
        return self.session.scalar(
            select(RawImport).where(
                RawImport.device_id == device_id,
                RawImport.kind == HEALTH_PAYLOAD_KIND,
                RawImport.sha256 == payload_sha,
            )
        )

    def _raw_import_by_source(self, device_id: str, source_id: str) -> RawImport | None:
        return self.session.scalar(
            select(RawImport).where(
                RawImport.device_id == device_id,
                RawImport.kind == HEALTH_PAYLOAD_KIND,
                RawImport.source_id == source_id,
            )
        )

    def _duplicate_metric(
        self,
        device_id: str,
        metric: ParsedHealthMetric,
    ) -> HealthMetric | None:
        duplicate_by_source = self.session.scalar(
            select(HealthMetric).where(
                HealthMetric.device_id == device_id,
                HealthMetric.metric_type == metric.metric_type,
                HealthMetric.source_record_id == metric.source_record_id,
            )
        )
        if duplicate_by_source is not None:
            return duplicate_by_source

        return self.session.scalar(
            select(HealthMetric).where(
                HealthMetric.device_id == device_id,
                HealthMetric.metric_type == metric.metric_type,
                HealthMetric.start_time == metric.start_time,
                HealthMetric.end_time == metric.end_time,
                HealthMetric.value == metric.value,
                HealthMetric.unit == metric.unit,
            )
        )

    def _archive_payload(
        self,
        *,
        device_id: str,
        payload: bytes,
        payload_sha: str,
        source_id: str,
    ) -> Path:
        archive_dir = self._archive_root() / device_id / HEALTH_PAYLOAD_KIND
        archive_dir.mkdir(parents=True, exist_ok=True)
        suffix = Path(source_id).suffix.lower()
        if suffix != ".json":
            suffix = ".json"
        archive_path = archive_dir / f"{payload_sha}{suffix}"
        if not archive_path.exists():
            with archive_path.open("wb") as output:
                copyfileobj(_BytesReader(payload), output)
        return archive_path

    def _archive_root(self) -> Path:
        persisted_settings = self.session.get(AppSettings, 1)
        if persisted_settings is not None:
            return Path(persisted_settings.raw_archive_path).expanduser()
        return self.runtime_settings.raw_archive_path.expanduser()

    def _now(self) -> datetime:
        return self.now or datetime.now(UTC)


class _BytesReader:
    """Small read-compatible wrapper so archive writes stream through shutil."""

    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.offset = 0

    def read(self, size: int = -1) -> bytes:
        """Read bytes from the wrapped payload."""

        if size < 0:
            size = len(self.payload) - self.offset
        chunk = self.payload[self.offset : self.offset + size]
        self.offset += len(chunk)
        return chunk


def _health_metric_model(
    device_id: str,
    parsed: ParsedHealthMetric,
) -> HealthMetric:
    return HealthMetric(
        device_id=device_id,
        metric_type=parsed.metric_type,
        start_time=parsed.start_time,
        end_time=parsed.end_time,
        value=parsed.value,
        unit=parsed.unit,
        source_record_id=parsed.source_record_id,
    )


def _summary(results: list[HealthPayloadImportResult]) -> HealthImportSummary:
    return HealthImportSummary(
        records_created=sum(result.records_created for result in results),
        records_skipped=sum(result.records_skipped for result in results),
        payloads_failed=sum(1 for result in results if result.status == "failed"),
        raw_files_archived=sum(1 for result in results if result.archived),
        payloads=results,
    )


def _remove_if_unreferenced(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
