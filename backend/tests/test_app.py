from pathlib import Path

from fastapi.testclient import TestClient

from runstats.config import Settings
from runstats.main import create_app


def test_create_app_registers_healthcheck(tmp_path: Path) -> None:
    settings = Settings(database_path=tmp_path / "runstats.sqlite3")
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.get("/api/healthcheck")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "runstats",
        "version": "0.1.0",
    }


def test_api_errors_use_structured_shape(tmp_path: Path) -> None:
    settings = Settings(database_path=tmp_path / "runstats.sqlite3")
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.get("/api/missing")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "NOT_FOUND",
            "message": "Resource not found.",
            "details": {},
        }
    }
