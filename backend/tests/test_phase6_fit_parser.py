from hashlib import sha256

import pytest

from runstats.importers import FitActivityParseError, FitActivityParser
from tests.fit_fixtures import build_activity_fit


def test_fit_activity_parser_extracts_activity_laps_and_samples() -> None:
    payload = build_activity_fit()
    activity = FitActivityParser().parse(
        payload,
        sha256=sha256(payload).hexdigest(),
        source_id="D:/Garmin/Activities/morning-10k.fit",
        source_name="Morning 10K",
    )

    assert activity.name == "Morning 10K"
    assert activity.sport == "running"
    assert activity.distance_meters == 10_000.0
    assert activity.duration_seconds == 1_800.0
    assert activity.avg_pace_seconds_per_km == 180.0
    assert activity.avg_heart_rate == 145
    assert activity.max_heart_rate == 170
    assert activity.avg_cadence == 168.0
    assert activity.elevation_gain_meters == 80.0
    assert activity.training_effect == 3.2
    assert len(activity.laps) == 2
    assert activity.laps[0].distance_meters == 5_000.0
    assert len(activity.samples) == 3
    assert activity.samples[-1].elapsed_seconds == 1_800.0
    assert activity.samples[-1].distance_meters == 10_000.0
    assert activity.samples[-1].latitude is not None
    assert activity.samples[-1].longitude is not None
    assert activity.samples[-1].speed_meters_per_second == 3.1


def test_fit_activity_parser_handles_missing_optional_fields() -> None:
    payload = build_activity_fit(include_optional=False)
    activity = FitActivityParser().parse(
        payload,
        sha256=sha256(payload).hexdigest(),
        source_id="minimal.fit",
    )

    assert activity.calories is None
    assert activity.avg_heart_rate is None
    assert activity.max_heart_rate is None
    assert activity.avg_cadence is None
    assert activity.elevation_gain_meters is None
    assert activity.training_effect is None
    assert activity.laps == []
    assert len(activity.samples) == 3


def test_fit_activity_parser_rejects_malformed_files() -> None:
    with pytest.raises(FitActivityParseError):
        FitActivityParser().parse(
            b"not a fit file",
            sha256="0" * 64,
            source_id="broken.fit",
        )
