from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from runstats.config import Settings
from runstats.db.models import Base
from runstats.db.seed import seed_development_data
from runstats.main import create_app


def test_activity_api_lists_details_samples_and_summary(tmp_path: Path) -> None:
    app = _seeded_app(tmp_path)

    with TestClient(app) as client:
        listed = client.get(
            "/api/activities",
            params={"min_distance_meters": 8000, "limit": 1, "offset": 0},
        )
        detail = client.get("/api/activities/seed-activity-001")
        samples = client.get("/api/activities/seed-activity-001/samples")
        summary = client.get("/api/activities/summary", params={"bucket": "month"})

    assert listed.status_code == 200
    assert listed.json()["total"] == 2
    assert listed.json()["items"][0]["name"] == "Sunday Long Run"
    assert detail.status_code == 200
    assert detail.json()["summary"]["lap_count"] == 5
    assert detail.json()["summary"]["has_gps"] is True
    assert samples.status_code == 200
    elapsed = [sample["elapsed_seconds"] for sample in samples.json()["samples"]]
    assert elapsed == sorted(elapsed)
    assert summary.status_code == 200
    assert summary.json()["total_distance_meters"] == 25220.0
    assert len(summary.json()["buckets"]) == 1


def test_activity_api_filters_by_date_sport_and_distance(tmp_path: Path) -> None:
    app = _seeded_app(tmp_path)

    with TestClient(app) as client:
        response = client.get(
            "/api/activities",
            params={
                "from": "2026-06-08T00:00:00Z",
                "to": "2026-06-16T00:00:00Z",
                "sport": "running",
                "min_distance_meters": 10000,
            },
        )
        missing = client.get("/api/activities/not-real")

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == "seed-activity-003"
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "ACTIVITY_NOT_FOUND"


def test_health_api_discovers_metrics_and_returns_series(tmp_path: Path) -> None:
    app = _seeded_app(tmp_path)

    with TestClient(app) as client:
        metrics = client.get("/api/health/metrics")
        series = client.get(
            "/api/health/series",
            params={"metric_type": "steps", "bucket": "month"},
        )
        ranged = client.get(
            "/api/health/series",
            params={
                "metric_type": "resting_hr",
                "from": "2026-06-08T00:00:00Z",
                "to": "2026-06-09T00:00:00Z",
                "bucket": "week",
            },
        )
        missing = client.get(
            "/api/health/series",
            params={"metric_type": "body_battery", "bucket": "week"},
        )

    assert metrics.status_code == 200
    assert {metric["metric_type"] for metric in metrics.json()["metrics"]} == {
        "hrv",
        "resting_hr",
        "sleep",
        "steps",
    }
    assert series.status_code == 200
    assert series.json()["points"][0]["value"] == 8420.0 + 8421.0 + 8422.0
    assert ranged.status_code == 200
    assert ranged.json()["points"][0]["value"] == 54.0
    assert missing.status_code == 200
    assert missing.json()["metric_available"] is False
    assert missing.json()["points"] == []


def test_sync_api_lists_recent_runs_and_details(tmp_path: Path) -> None:
    app = _seeded_app(tmp_path)

    with TestClient(app) as client:
        listed = client.get("/api/sync-runs", params={"limit": 2})
        failed = client.get("/api/sync-runs/seed-sync-002")
        missing = client.get("/api/sync-runs/not-real")

    assert listed.status_code == 200
    assert listed.json()["total"] == 3
    assert [run["id"] for run in listed.json()["items"]] == [
        "seed-sync-003",
        "seed-sync-002",
    ]
    assert failed.status_code == 200
    assert failed.json()["error_summary"] == (
        "Seeded Bluetooth export unavailable; folder import required."
    )
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "SYNC_RUN_NOT_FOUND"


def test_settings_api_reads_updates_and_rejects_invalid_values(
    tmp_path: Path,
) -> None:
    app = _empty_app(tmp_path)

    with TestClient(app) as client:
        defaults = client.get("/api/settings")
        updated = client.patch(
            "/api/settings",
            json={
                "chat_provider": "disabled",
                "chat_retention_policy": "do_not_retain",
            },
        )
        invalid = client.patch("/api/settings", json={"chat_provider": "invalid"})

    assert defaults.status_code == 200
    assert defaults.json()["chat_provider"] == "local"
    assert defaults.json()["local_chat_provider"] == "ollama"
    assert defaults.json()["chat_retention_policy"] == "retain_until_deleted"
    assert updated.status_code == 200
    assert updated.json()["chat_provider"] == "disabled"
    assert updated.json()["chat_retention_policy"] == "do_not_retain"
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"


def _seeded_app(tmp_path: Path) -> FastAPI:
    app = _empty_app(tmp_path)
    settings: Settings = app.state.settings
    session_factory: Any = app.state.session_factory
    with session_factory() as session:
        seed_development_data(session, settings.raw_archive_path)
    return app


def _empty_app(tmp_path: Path) -> FastAPI:
    settings = Settings(
        database_path=tmp_path / "api.sqlite3",
        raw_archive_path=tmp_path / "archive",
    )
    app = create_app(settings)
    Base.metadata.create_all(bind=app.state.engine)
    return app
