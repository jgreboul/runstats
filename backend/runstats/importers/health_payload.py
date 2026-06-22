"""Health payload parsing and metric normalization."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import cast

HEALTH_METRIC_STEPS = "steps"
HEALTH_METRIC_RESTING_HR = "resting_hr"
HEALTH_METRIC_HRV = "hrv"
HEALTH_METRIC_SLEEP = "sleep"
HEALTH_METRIC_STRESS = "stress"
HEALTH_METRIC_BODY_BATTERY = "body_battery"
HEALTH_METRIC_RESPIRATION = "respiration"
HEALTH_METRIC_PULSE_OX = "pulse_ox"

SUPPORTED_HEALTH_METRICS: tuple[str, ...] = (
    HEALTH_METRIC_STEPS,
    HEALTH_METRIC_RESTING_HR,
    HEALTH_METRIC_HRV,
    HEALTH_METRIC_SLEEP,
    HEALTH_METRIC_STRESS,
    HEALTH_METRIC_BODY_BATTERY,
    HEALTH_METRIC_RESPIRATION,
    HEALTH_METRIC_PULSE_OX,
)

CANONICAL_HEALTH_UNITS: Mapping[str, str] = {
    HEALTH_METRIC_STEPS: "count",
    HEALTH_METRIC_RESTING_HR: "bpm",
    HEALTH_METRIC_HRV: "ms",
    HEALTH_METRIC_SLEEP: "hours",
    HEALTH_METRIC_STRESS: "score",
    HEALTH_METRIC_BODY_BATTERY: "score",
    HEALTH_METRIC_RESPIRATION: "breaths/min",
    HEALTH_METRIC_PULSE_OX: "percent",
}

METRIC_ALIASES: Mapping[str, str] = {
    "steps": HEALTH_METRIC_STEPS,
    "step_count": HEALTH_METRIC_STEPS,
    "daily_steps": HEALTH_METRIC_STEPS,
    "resting_hr": HEALTH_METRIC_RESTING_HR,
    "resting_heart_rate": HEALTH_METRIC_RESTING_HR,
    "restingheartrateinbeatsperminute": HEALTH_METRIC_RESTING_HR,
    "hrv": HEALTH_METRIC_HRV,
    "heart_rate_variability": HEALTH_METRIC_HRV,
    "sleep": HEALTH_METRIC_SLEEP,
    "sleep_duration": HEALTH_METRIC_SLEEP,
    "stress": HEALTH_METRIC_STRESS,
    "stress_level": HEALTH_METRIC_STRESS,
    "body_battery": HEALTH_METRIC_BODY_BATTERY,
    "bodybattery": HEALTH_METRIC_BODY_BATTERY,
    "respiration": HEALTH_METRIC_RESPIRATION,
    "respiration_rate": HEALTH_METRIC_RESPIRATION,
    "pulse_ox": HEALTH_METRIC_PULSE_OX,
    "pulseox": HEALTH_METRIC_PULSE_OX,
    "spo2": HEALTH_METRIC_PULSE_OX,
}

SUMMARY_FIELDS: tuple[tuple[tuple[str, ...], str, str], ...] = (
    (("steps",), HEALTH_METRIC_STEPS, "count"),
    (
        ("restingHeartRateInBeatsPerMinute", "restingHeartRate"),
        HEALTH_METRIC_RESTING_HR,
        "bpm",
    ),
    (
        ("hrvWeeklyAverage", "hrvLastNightAverage", "hrv"),
        HEALTH_METRIC_HRV,
        "ms",
    ),
    (
        ("sleepDurationInSeconds", "sleepDuration"),
        HEALTH_METRIC_SLEEP,
        "seconds",
    ),
    (
        ("averageStressLevel", "stressLevel", "stress"),
        HEALTH_METRIC_STRESS,
        "score",
    ),
    (
        ("bodyBatteryMostRecentValue", "bodyBatteryChargedValue", "bodyBattery"),
        HEALTH_METRIC_BODY_BATTERY,
        "score",
    ),
    (
        ("averageRespirationValue", "averageRespiration", "respiration"),
        HEALTH_METRIC_RESPIRATION,
        "breaths/min",
    ),
    (("averageSpo2", "averagePulseOx", "spo2"), HEALTH_METRIC_PULSE_OX, "percent"),
)


class HealthPayloadParseError(ValueError):
    """Expected health payload parsing failure."""


@dataclass(frozen=True)
class HealthImportWarning:
    """A skipped or unsupported health payload record."""

    source_id: str
    message: str
    record_index: int | None = None
    metric_type: str | None = None


@dataclass(frozen=True)
class ParsedHealthMetric:
    """Normalized health metric ready for persistence."""

    metric_type: str
    start_time: datetime
    end_time: datetime | None
    value: float
    unit: str
    source_record_id: str


@dataclass(frozen=True)
class ParsedHealthPayload:
    """Parsed health payload records and non-fatal warnings."""

    records: list[ParsedHealthMetric]
    warnings: list[HealthImportWarning]


class HealthPayloadParser:
    """Parse JSON health exports into canonical RunStats health metrics."""

    def parse(
        self,
        payload: bytes,
        *,
        sha256: str,
        source_id: str,
        source_name: str | None = None,
    ) -> ParsedHealthPayload:
        """Parse one JSON health payload."""

        _ = source_name
        try:
            decoded = payload.decode("utf-8")
            parsed = cast(object, json.loads(decoded))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HealthPayloadParseError(
                "The health payload could not be parsed as JSON."
            ) from exc

        records: list[ParsedHealthMetric] = []
        warnings: list[HealthImportWarning] = []
        for index, record in enumerate(_records_from_payload(parsed, sha256=sha256)):
            parsed_record, warning = _parse_record(
                record,
                index=index,
                sha256=sha256,
                source_id=source_id,
            )
            if parsed_record is not None:
                records.append(parsed_record)
            if warning is not None:
                warnings.append(warning)

        if not records and not warnings:
            warnings.append(
                HealthImportWarning(
                    source_id=source_id,
                    message="Health payload did not contain supported records.",
                )
            )
        return ParsedHealthPayload(records=records, warnings=warnings)


def _records_from_payload(
    payload: object,
    *,
    sha256: str,
) -> list[Mapping[str, object]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, Mapping)]

    if not isinstance(payload, Mapping):
        raise HealthPayloadParseError("The health payload root must be an object.")

    records: list[Mapping[str, object]] = []
    for key in ("records", "metrics", "health_metrics", "healthMetrics"):
        nested = payload.get(key)
        if isinstance(nested, list):
            records.extend(item for item in nested if isinstance(item, Mapping))

    expanded: list[Mapping[str, object]] = []
    for key in ("daily_summaries", "dailySummaries"):
        nested = payload.get(key)
        if isinstance(nested, list):
            for index, item in enumerate(nested):
                if isinstance(item, Mapping):
                    expanded.extend(_expand_summary_record(item, sha256, index))

    for key in ("sleeps", "sleep_summaries", "sleepSummaries"):
        nested = payload.get(key)
        if isinstance(nested, list):
            for index, item in enumerate(nested):
                if isinstance(item, Mapping):
                    expanded.extend(_expand_sleep_record(item, sha256, index))

    if records or expanded:
        return [*records, *expanded]

    if _optional_str(_first_field(payload, ("metric_type", "metricType", "type"))):
        return [payload]

    return []


def _expand_summary_record(
    record: Mapping[str, object],
    sha256: str,
    index: int,
) -> list[Mapping[str, object]]:
    period = _summary_period(record)
    if period is None:
        return []
    period_start, period_end = period
    source_base = _summary_source_id(record, sha256, index)
    expanded: list[Mapping[str, object]] = []
    for field_names, metric_type, unit in SUMMARY_FIELDS:
        value = _first_field(record, field_names)
        if value is None:
            continue
        expanded.append(
            {
                "metric_type": metric_type,
                "start_time": period_start,
                "end_time": period_end,
                "value": value,
                "unit": unit,
                "source_record_id": f"{source_base}:{metric_type}",
            }
        )
    return expanded


def _expand_sleep_record(
    record: Mapping[str, object],
    sha256: str,
    index: int,
) -> list[Mapping[str, object]]:
    period = _summary_period(record)
    if period is None:
        return []
    period_start, period_end = period
    source_base = _summary_source_id(record, sha256, index)
    value = _first_field(
        record,
        ("sleepDurationInSeconds", "durationInSeconds", "sleepDuration", "duration"),
    )
    if value is None:
        return []
    return [
        {
            "metric_type": HEALTH_METRIC_SLEEP,
            "start_time": period_start,
            "end_time": period_end,
            "value": value,
            "unit": "seconds",
            "source_record_id": f"{source_base}:{HEALTH_METRIC_SLEEP}",
        }
    ]


def _parse_record(
    record: Mapping[str, object],
    *,
    index: int,
    sha256: str,
    source_id: str,
) -> tuple[ParsedHealthMetric | None, HealthImportWarning | None]:
    raw_metric = _optional_str(
        _first_field(record, ("metric_type", "metricType", "type", "name", "metric"))
    )
    metric_type = _normalize_metric_type(raw_metric)
    if metric_type is None:
        return None, HealthImportWarning(
            source_id=source_id,
            message="Unsupported or missing health metric type.",
            record_index=index,
            metric_type=raw_metric,
        )

    start_time = _record_start_time(record)
    if start_time is None:
        return None, HealthImportWarning(
            source_id=source_id,
            message="Health metric is missing a start time.",
            record_index=index,
            metric_type=metric_type,
        )

    value = _record_value(record)
    normalized = _normalize_metric_value(
        metric_type,
        value,
        _optional_str(_first_field(record, ("unit", "units"))),
    )
    if normalized is None:
        return None, HealthImportWarning(
            source_id=source_id,
            message="Health metric has an unsupported value or unit.",
            record_index=index,
            metric_type=metric_type,
        )
    normalized_value, unit = normalized
    return (
        ParsedHealthMetric(
            metric_type=metric_type,
            start_time=start_time,
            end_time=_record_end_time(record, start_time),
            value=normalized_value,
            unit=unit,
            source_record_id=_record_source_id(record, sha256, index),
        ),
        None,
    )


def _normalize_metric_type(metric_type: str | None) -> str | None:
    if metric_type is None:
        return None
    cleaned = _clean_token(metric_type)
    return METRIC_ALIASES.get(cleaned)


def _normalize_metric_value(
    metric_type: str,
    raw_value: object,
    raw_unit: str | None,
) -> tuple[float, str] | None:
    value = _optional_float(raw_value)
    if value is None:
        return None
    unit = _clean_unit(raw_unit) or CANONICAL_HEALTH_UNITS[metric_type]

    if metric_type == HEALTH_METRIC_SLEEP:
        if unit in {"s", "sec", "secs", "second", "seconds"}:
            return value / 3600.0, "hours"
        if unit in {"m", "min", "mins", "minute", "minutes"}:
            return value / 60.0, "hours"
        if unit in {"h", "hr", "hrs", "hour", "hours"}:
            return value, "hours"
        return None

    if metric_type == HEALTH_METRIC_HRV:
        if unit in {"s", "sec", "secs", "second", "seconds"}:
            return value * 1000.0, "ms"
        if unit in {"ms", "millisecond", "milliseconds"}:
            return value, "ms"
        return None

    accepted_units: Mapping[str, set[str]] = {
        HEALTH_METRIC_STEPS: {"count", "counts", "step", "steps"},
        HEALTH_METRIC_RESTING_HR: {
            "bpm",
            "beat/min",
            "beats/min",
            "beats_per_minute",
        },
        HEALTH_METRIC_STRESS: {"score", "index"},
        HEALTH_METRIC_BODY_BATTERY: {"score", "percent", "%"},
        HEALTH_METRIC_RESPIRATION: {
            "breaths/min",
            "breaths_per_minute",
            "brpm",
            "rpm",
        },
        HEALTH_METRIC_PULSE_OX: {"percent", "%"},
    }
    if unit in accepted_units.get(metric_type, set()):
        return value, CANONICAL_HEALTH_UNITS[metric_type]
    return None


def _record_value(record: Mapping[str, object]) -> object:
    return _first_field(
        record,
        (
            "value",
            "amount",
            "duration",
            "duration_seconds",
            "durationInSeconds",
        ),
    )


def _record_start_time(record: Mapping[str, object]) -> datetime | None:
    start_time = _optional_datetime(
        _first_field(
            record,
            (
                "start_time",
                "startTime",
                "startTimeGMT",
                "timestamp",
                "time",
                "startTimeInSeconds",
                "start_time_in_seconds",
            ),
        )
    )
    if start_time is not None:
        return start_time

    calendar_date = _optional_date(
        _first_field(record, ("calendarDate", "summaryDate", "date"))
    )
    if calendar_date is None:
        return None
    return datetime.combine(calendar_date, datetime.min.time(), tzinfo=UTC)


def _record_end_time(
    record: Mapping[str, object],
    start_time: datetime,
) -> datetime | None:
    end_time = _optional_datetime(
        _first_field(
            record,
            ("end_time", "endTime", "endTimeGMT", "endTimeInSeconds"),
        )
    )
    if end_time is not None:
        return end_time

    duration = _optional_float(
        _first_field(record, ("duration_seconds", "durationInSeconds"))
    )
    if duration is not None:
        return start_time + timedelta(seconds=duration)

    if _optional_date(_first_field(record, ("calendarDate", "summaryDate", "date"))):
        return start_time + timedelta(days=1)
    return None


def _record_source_id(
    record: Mapping[str, object],
    sha256: str,
    index: int,
) -> str:
    source_record_id = _optional_str(
        _first_field(
            record,
            (
                "source_record_id",
                "sourceRecordId",
                "record_id",
                "recordId",
                "summaryId",
                "id",
            ),
        )
    )
    if source_record_id is not None:
        return source_record_id
    return f"health-sha:{sha256}:{index}"


def _summary_period(
    record: Mapping[str, object],
) -> tuple[datetime, datetime | None] | None:
    start_time = _record_start_time(record)
    if start_time is None:
        return None
    return start_time, _record_end_time(record, start_time)


def _summary_source_id(record: Mapping[str, object], sha256: str, index: int) -> str:
    return _record_source_id(record, sha256, index)


def _first_field(
    record: Mapping[str, object],
    field_names: tuple[str, ...],
) -> object:
    for field_name in field_names:
        value = record.get(field_name)
        if value is not None:
            return value
    return None


def _optional_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
    if isinstance(value, int | float) and not isinstance(value, bool):
        return datetime.fromtimestamp(float(value), tz=UTC)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
        except ValueError:
            parsed_date = _optional_date(value)
            if parsed_date is not None:
                return datetime.combine(parsed_date, datetime.min.time(), tzinfo=UTC)
    return None


def _optional_date(value: object) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def _optional_float(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _optional_str(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _clean_token(value: str) -> str:
    return value.strip().replace("-", "_").replace(" ", "_").lower()


def _clean_unit(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip().replace(" ", "_").lower()
