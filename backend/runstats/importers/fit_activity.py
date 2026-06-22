"""FIT activity parsing and normalization."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Protocol, cast

from fitparse import FitFile  # type: ignore[import-untyped]
from fitparse.utils import FitParseError  # type: ignore[import-untyped]

FIT_SEMICIRCLE_UNITS = 2**31

class FitMessageProtocol(Protocol):
    """Small subset of fitparse data messages used by the importer."""

    @property
    def name(self) -> str:
        """Return the FIT message name."""

    def get_value(self, field_name: str) -> object:
        """Return one decoded field value."""


class FitActivityParseError(ValueError):
    """Expected FIT parsing or normalization failure."""


@dataclass(frozen=True)
class ParsedActivityLap:
    """Normalized lap data extracted from a FIT file."""

    started_at: datetime
    duration_seconds: float
    distance_meters: float
    avg_heart_rate: int | None
    avg_pace_seconds_per_km: float | None


@dataclass(frozen=True)
class ParsedActivitySample:
    """Normalized activity sample extracted from a FIT record message."""

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


@dataclass(frozen=True)
class ParsedActivity:
    """Normalized activity ready for persistence."""

    source_activity_id: str
    source_activity_id_kind: str
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
    laps: list[ParsedActivityLap]
    samples: list[ParsedActivitySample]


class FitActivityParser:
    """Parse Garmin FIT activity payloads into canonical metric records."""

    def parse(
        self,
        payload: bytes,
        *,
        sha256: str,
        source_id: str,
        source_name: str | None = None,
    ) -> ParsedActivity:
        """Parse one FIT activity payload."""

        try:
            fit_file = FitFile(BytesIO(payload))
            messages = [
                cast(FitMessageProtocol, message)
                for message in fit_file.get_messages()
                if getattr(message, "name", None)
                in {"file_id", "session", "lap", "record"}
            ]
        except (FitParseError, ValueError, OSError) as exc:
            raise FitActivityParseError("The FIT file could not be parsed.") from exc

        try:
            return self._normalize_messages(
                messages,
                sha256=sha256,
                source_id=source_id,
                source_name=source_name,
            )
        except (TypeError, ValueError) as exc:
            raise FitActivityParseError(str(exc)) from exc

    def _normalize_messages(
        self,
        messages: Iterable[FitMessageProtocol],
        *,
        sha256: str,
        source_id: str,
        source_name: str | None,
    ) -> ParsedActivity:
        message_list = list(messages)
        file_id = _first_message(message_list, "file_id")
        sessions = [message for message in message_list if message.name == "session"]
        laps = [message for message in message_list if message.name == "lap"]
        records = [message for message in message_list if message.name == "record"]
        session = sessions[0] if sessions else None

        started_at = _activity_start_time(session, records)
        duration_seconds = _activity_duration_seconds(session, records, started_at)
        distance_meters = _activity_distance_meters(session, records)
        if duration_seconds <= 0:
            raise ValueError("FIT activity duration must be greater than zero.")
        if distance_meters < 0:
            raise ValueError("FIT activity distance cannot be negative.")

        sport = _sport_name(session)
        source_activity_id, source_activity_id_kind = _source_activity_id(
            file_id=file_id,
            session=session,
            started_at=started_at,
            sha256=sha256,
        )
        return ParsedActivity(
            source_activity_id=source_activity_id,
            source_activity_id_kind=source_activity_id_kind,
            sport=sport,
            name=_activity_name(source_name, source_id, sport, started_at),
            started_at=started_at,
            duration_seconds=duration_seconds,
            distance_meters=distance_meters,
            calories=_optional_int(_field(session, "total_calories")),
            avg_heart_rate=_optional_int(_field(session, "avg_heart_rate")),
            max_heart_rate=_optional_int(_field(session, "max_heart_rate")),
            avg_cadence=_optional_float(
                _first_field(session, ("avg_running_cadence", "avg_cadence"))
            ),
            avg_pace_seconds_per_km=_pace_seconds_per_km(
                duration_seconds,
                distance_meters,
            ),
            elevation_gain_meters=_optional_float(_field(session, "total_ascent")),
            training_effect=_optional_float(_field(session, "total_training_effect")),
            laps=_parse_laps(laps),
            samples=_parse_samples(records, started_at),
        )


def _first_message(
    messages: Iterable[FitMessageProtocol],
    name: str,
) -> FitMessageProtocol | None:
    for message in messages:
        if message.name == name:
            return message
    return None


def _field(message: FitMessageProtocol | None, field_name: str) -> object:
    if message is None:
        return None
    return message.get_value(field_name)


def _first_field(
    message: FitMessageProtocol | None,
    field_names: tuple[str, ...],
) -> object:
    for field_name in field_names:
        value = _field(message, field_name)
        if value is not None:
            return value
    return None


def _activity_start_time(
    session: FitMessageProtocol | None,
    records: list[FitMessageProtocol],
) -> datetime:
    raw_start = _first_field(session, ("start_time", "timestamp"))
    start_time = _optional_datetime(raw_start)
    if start_time is not None:
        return start_time

    record_times = [
        record_time
        for record in records
        if (record_time := _optional_datetime(_field(record, "timestamp"))) is not None
    ]
    if record_times:
        return min(record_times)
    raise ValueError("FIT activity is missing a start time.")


def _activity_duration_seconds(
    session: FitMessageProtocol | None,
    records: list[FitMessageProtocol],
    started_at: datetime,
) -> float:
    duration = _optional_float(
        _first_field(session, ("total_timer_time", "total_elapsed_time"))
    )
    if duration is not None:
        return duration

    record_times = [
        record_time
        for record in records
        if (record_time := _optional_datetime(_field(record, "timestamp"))) is not None
    ]
    if record_times:
        return max((max(record_times) - started_at).total_seconds(), 0.0)
    raise ValueError("FIT activity is missing duration data.")


def _activity_distance_meters(
    session: FitMessageProtocol | None,
    records: list[FitMessageProtocol],
) -> float:
    distance = _optional_float(_field(session, "total_distance"))
    if distance is not None:
        return distance

    record_distances = [
        record_distance
        for record in records
        if (record_distance := _optional_float(_field(record, "distance"))) is not None
    ]
    if record_distances:
        return max(record_distances)
    raise ValueError("FIT activity is missing distance data.")


def _source_activity_id(
    *,
    file_id: FitMessageProtocol | None,
    session: FitMessageProtocol | None,
    started_at: datetime,
    sha256: str,
) -> tuple[str, str]:
    serial_number = _optional_int(_field(file_id, "serial_number"))
    time_created = _optional_datetime(_field(file_id, "time_created"))
    if serial_number is not None and time_created is not None:
        return f"fit:{serial_number}:{time_created.isoformat()}", "native"

    session_start = _optional_datetime(_field(session, "start_time")) or started_at
    return f"fit-sha:{sha256}:{session_start.isoformat()}", "checksum"


def _activity_name(
    source_name: str | None,
    source_id: str,
    sport: str,
    started_at: datetime,
) -> str:
    if source_name:
        return source_name

    source_path = Path(source_id)
    if source_path.name:
        return source_path.stem

    return f"{sport.replace('_', ' ').title()} {started_at.date().isoformat()}"


def _sport_name(session: FitMessageProtocol | None) -> str:
    sport = _optional_str(_field(session, "sport")) or "unknown"
    sub_sport = _optional_str(_field(session, "sub_sport"))
    if sport == "running" and sub_sport == "trail":
        return "trail_running"
    return sport


def _parse_laps(
    lap_messages: list[FitMessageProtocol],
) -> list[ParsedActivityLap]:
    parsed_laps: list[ParsedActivityLap] = []
    for lap in lap_messages:
        started_at = _optional_datetime(_field(lap, "start_time"))
        duration = _optional_float(
            _first_field(lap, ("total_timer_time", "total_elapsed_time"))
        )
        distance = _optional_float(_field(lap, "total_distance"))
        if started_at is None or duration is None or distance is None:
            continue
        parsed_laps.append(
            ParsedActivityLap(
                started_at=started_at,
                duration_seconds=duration,
                distance_meters=distance,
                avg_heart_rate=_optional_int(_field(lap, "avg_heart_rate")),
                avg_pace_seconds_per_km=_pace_seconds_per_km(duration, distance),
            )
        )
    return parsed_laps


def _parse_samples(
    record_messages: list[FitMessageProtocol],
    activity_started_at: datetime,
) -> list[ParsedActivitySample]:
    samples: list[ParsedActivitySample] = []
    for record in record_messages:
        sample_time = _optional_datetime(_field(record, "timestamp"))
        if sample_time is None:
            continue
        samples.append(
            ParsedActivitySample(
                sample_time=sample_time,
                elapsed_seconds=max(
                    (sample_time - activity_started_at).total_seconds(),
                    0.0,
                ),
                distance_meters=_optional_float(_field(record, "distance")),
                latitude=_semicircles_to_degrees(_field(record, "position_lat")),
                longitude=_semicircles_to_degrees(_field(record, "position_long")),
                elevation_meters=_optional_float(
                    _first_field(record, ("enhanced_altitude", "altitude"))
                ),
                heart_rate=_optional_int(_field(record, "heart_rate")),
                cadence=_optional_float(
                    _first_field(record, ("running_cadence", "cadence"))
                ),
                power_watts=_optional_float(_field(record, "power")),
                speed_meters_per_second=_optional_float(
                    _first_field(record, ("enhanced_speed", "speed"))
                ),
            )
        )
    return sorted(samples, key=lambda sample: sample.elapsed_seconds)


def _optional_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
    return None


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    return None


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return None


def _optional_str(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _pace_seconds_per_km(
    duration_seconds: float,
    distance_meters: float,
) -> float | None:
    if distance_meters <= 0:
        return None
    return duration_seconds / (distance_meters / 1000.0)


def _semicircles_to_degrees(value: object) -> float | None:
    semicircles = _optional_int(value)
    if semicircles is None:
        return None
    return semicircles * 180.0 / FIT_SEMICIRCLE_UNITS
