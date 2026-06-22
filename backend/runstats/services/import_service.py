"""Activity import orchestration services."""

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
from runstats.db.models import (
    Activity,
    ActivityLap,
    ActivitySample,
    AppSettings,
    Device,
    RawImport,
)
from runstats.importers import (
    FitActivityParseError,
    FitActivityParser,
    ParsedActivity,
)

ACTIVITY_FIT_KIND = "activity_fit"
ACTIVITY_DUPLICATE_DISTANCE_TOLERANCE_METERS = 1.0
ACTIVITY_DUPLICATE_DURATION_TOLERANCE_SECONDS = 1.0

ImportStatus = Literal["created", "skipped", "failed"]


class ActivityParser(Protocol):
    """Parser contract used by the import service."""

    def parse(
        self,
        payload: bytes,
        *,
        sha256: str,
        source_id: str,
        source_name: str | None = None,
    ) -> ParsedActivity:
        """Parse one raw activity payload."""


@dataclass(frozen=True)
class ActivityFileImportResult:
    """Import result for one raw activity file or payload."""

    source_id: str
    status: ImportStatus
    message: str
    sha256: str | None = None
    activity_id: str | None = None
    raw_import_id: str | None = None
    archived: bool = False


@dataclass(frozen=True)
class ActivityImportSummary:
    """Summary for a multi-file activity import run."""

    created: int
    skipped: int
    failed: int
    raw_files_archived: int
    files: list[ActivityFileImportResult]


class ActivityImportService:
    """Import FIT activity payloads into the normalized activity schema."""

    def __init__(
        self,
        session: Session,
        runtime_settings: Settings,
        parser: ActivityParser | None = None,
        *,
        now: datetime | None = None,
    ) -> None:
        self.session = session
        self.runtime_settings = runtime_settings
        self.parser = parser or FitActivityParser()
        self.now = now

    def import_fit_folder(
        self,
        *,
        device_id: str,
        folder_path: str,
        recursive: bool = True,
    ) -> ActivityImportSummary:
        """Import all FIT files from a local folder."""

        self._get_device(device_id)
        folder = Path(folder_path).expanduser()
        if not folder.exists() or not folder.is_dir():
            raise RunStatsError(
                "FIT_FOLDER_NOT_FOUND",
                "FIT import folder was not found.",
                details={"folder_path": folder_path},
                status_code=404,
            )

        pattern = "**/*" if recursive else "*"
        files = sorted(
            path
            for path in folder.glob(pattern)
            if path.is_file() and path.suffix.lower() == ".fit"
        )
        results = [
            self.import_fit_file(device_id=device_id, file_path=file_path)
            for file_path in files
        ]
        return _summary(results)

    def import_fit_file(
        self,
        *,
        device_id: str,
        file_path: Path,
    ) -> ActivityFileImportResult:
        """Import one FIT file from disk."""

        path = file_path.expanduser()
        if not path.exists() or not path.is_file():
            return ActivityFileImportResult(
                source_id=str(path),
                status="failed",
                message="FIT file was not found.",
            )

        try:
            payload = path.read_bytes()
        except OSError:
            return ActivityFileImportResult(
                source_id=str(path),
                status="failed",
                message="FIT file could not be read.",
            )

        return self.import_fit_payload(
            device_id=device_id,
            payload=payload,
            source_id=str(path.resolve()),
            source_name=path.stem,
        )

    def import_fit_payload(
        self,
        *,
        device_id: str,
        payload: bytes,
        source_id: str,
        source_name: str | None = None,
    ) -> ActivityFileImportResult:
        """Import one raw FIT payload."""

        self._get_device(device_id)
        payload_sha = sha256(payload).hexdigest()

        duplicate_raw = self._raw_import_by_sha(device_id, payload_sha)
        if duplicate_raw is not None:
            return ActivityFileImportResult(
                source_id=source_id,
                status="skipped",
                message="Duplicate raw FIT payload already archived.",
                sha256=payload_sha,
                raw_import_id=duplicate_raw.id,
            )

        duplicate_source = self._raw_import_by_source(device_id, source_id)
        if duplicate_source is not None:
            return ActivityFileImportResult(
                source_id=source_id,
                status="skipped",
                message="Raw FIT source was already archived.",
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
        except FitActivityParseError as exc:
            return ActivityFileImportResult(
                source_id=source_id,
                status="failed",
                message=str(exc),
                sha256=payload_sha,
            )

        duplicate_activity = self._duplicate_activity(device_id, parsed, payload_sha)
        if duplicate_activity is not None:
            return ActivityFileImportResult(
                source_id=source_id,
                status="skipped",
                message="Duplicate activity already imported.",
                sha256=payload_sha,
                activity_id=duplicate_activity.id,
            )

        archived_path = self._archive_payload(
            device_id=device_id,
            kind=ACTIVITY_FIT_KIND,
            payload=payload,
            payload_sha=payload_sha,
            source_id=source_id,
        )
        raw_import = RawImport(
            device_id=device_id,
            source_id=source_id,
            kind=ACTIVITY_FIT_KIND,
            sha256=payload_sha,
            storage_path=str(archived_path),
            imported_at=self._now(),
        )
        activity = _activity_model(device_id, raw_import, parsed)
        try:
            self.session.add(raw_import)
            self.session.add(activity)
            self.session.commit()
        except SQLAlchemyError:
            self.session.rollback()
            _remove_if_unreferenced(archived_path)
            return ActivityFileImportResult(
                source_id=source_id,
                status="failed",
                message="Activity import could not be persisted.",
                sha256=payload_sha,
            )

        self.session.refresh(raw_import)
        self.session.refresh(activity)
        return ActivityFileImportResult(
            source_id=source_id,
            status="created",
            message="Activity imported.",
            sha256=payload_sha,
            activity_id=activity.id,
            raw_import_id=raw_import.id,
            archived=True,
        )

    def import_watch_activity_exports(
        self,
        *,
        device_id: str,
        payloads: Iterable[WatchExportPayload],
    ) -> ActivityImportSummary:
        """Import raw activity payloads exported directly by a watch provider."""

        results: list[ActivityFileImportResult] = []
        for payload in payloads:
            if payload.kind != "activity":
                results.append(
                    ActivityFileImportResult(
                        source_id=payload.source_id,
                        status="skipped",
                        message="Skipped non-activity watch payload.",
                    )
                )
                continue

            results.append(
                self.import_fit_payload(
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
                RawImport.kind == ACTIVITY_FIT_KIND,
                RawImport.sha256 == payload_sha,
            )
        )

    def _raw_import_by_source(self, device_id: str, source_id: str) -> RawImport | None:
        return self.session.scalar(
            select(RawImport).where(
                RawImport.device_id == device_id,
                RawImport.kind == ACTIVITY_FIT_KIND,
                RawImport.source_id == source_id,
            )
        )

    def _duplicate_activity(
        self,
        device_id: str,
        parsed: ParsedActivity,
        payload_sha: str,
    ) -> Activity | None:
        duplicate_by_source = self.session.scalar(
            select(Activity).where(
                Activity.device_id == device_id,
                Activity.source_activity_id == parsed.source_activity_id,
            )
        )
        if duplicate_by_source is not None:
            return duplicate_by_source

        duplicate_by_raw = self.session.scalar(
            select(Activity)
            .join(RawImport, Activity.raw_file_id == RawImport.id)
            .where(
                Activity.device_id == device_id,
                RawImport.kind == ACTIVITY_FIT_KIND,
                RawImport.sha256 == payload_sha,
            )
        )
        if duplicate_by_raw is not None:
            return duplicate_by_raw

        if parsed.source_activity_id_kind == "native":
            return None

        candidates = list(
            self.session.scalars(
                select(Activity).where(
                    Activity.device_id == device_id,
                    Activity.started_at == parsed.started_at,
                )
            ).all()
        )
        for candidate in candidates:
            if (
                abs(candidate.duration_seconds - parsed.duration_seconds)
                <= ACTIVITY_DUPLICATE_DURATION_TOLERANCE_SECONDS
                and abs(candidate.distance_meters - parsed.distance_meters)
                <= ACTIVITY_DUPLICATE_DISTANCE_TOLERANCE_METERS
            ):
                return candidate
        return None

    def _archive_payload(
        self,
        *,
        device_id: str,
        kind: str,
        payload: bytes,
        payload_sha: str,
        source_id: str,
    ) -> Path:
        archive_dir = self._archive_root() / device_id / kind
        archive_dir.mkdir(parents=True, exist_ok=True)
        suffix = Path(source_id).suffix.lower()
        if suffix != ".fit":
            suffix = ".fit"
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


def _activity_model(
    device_id: str,
    raw_import: RawImport,
    parsed: ParsedActivity,
) -> Activity:
    activity = Activity(
        device_id=device_id,
        raw_import=raw_import,
        source_activity_id=parsed.source_activity_id,
        sport=parsed.sport,
        name=parsed.name,
        started_at=parsed.started_at,
        duration_seconds=parsed.duration_seconds,
        distance_meters=parsed.distance_meters,
        calories=parsed.calories,
        avg_heart_rate=parsed.avg_heart_rate,
        max_heart_rate=parsed.max_heart_rate,
        avg_cadence=parsed.avg_cadence,
        avg_pace_seconds_per_km=parsed.avg_pace_seconds_per_km,
        elevation_gain_meters=parsed.elevation_gain_meters,
        training_effect=parsed.training_effect,
    )
    activity.laps = [
        ActivityLap(
            lap_index=index,
            started_at=lap.started_at,
            duration_seconds=lap.duration_seconds,
            distance_meters=lap.distance_meters,
            avg_heart_rate=lap.avg_heart_rate,
            avg_pace_seconds_per_km=lap.avg_pace_seconds_per_km,
        )
        for index, lap in enumerate(parsed.laps)
    ]
    activity.samples = [
        ActivitySample(
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
        for sample in parsed.samples
    ]
    return activity


def _summary(results: list[ActivityFileImportResult]) -> ActivityImportSummary:
    return ActivityImportSummary(
        created=sum(1 for result in results if result.status == "created"),
        skipped=sum(1 for result in results if result.status == "skipped"),
        failed=sum(1 for result in results if result.status == "failed"),
        raw_files_archived=sum(1 for result in results if result.archived),
        files=results,
    )


def _remove_if_unreferenced(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
