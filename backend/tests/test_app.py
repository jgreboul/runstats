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


def test_create_app_serves_production_frontend_bundle(tmp_path: Path) -> None:
    frontend_dist_path = tmp_path / "frontend-dist"
    assets_path = frontend_dist_path / "assets"
    assets_path.mkdir(parents=True)
    (frontend_dist_path / "index.html").write_text("<main>RunStats</main>")
    (assets_path / "app.js").write_text("console.log('runstats')")
    settings = Settings(
        database_path=tmp_path / "runstats.sqlite3",
        frontend_dist_path=frontend_dist_path,
    )
    app = create_app(settings)

    with TestClient(app) as client:
        root = client.get("/")
        asset = client.get("/assets/app.js")
        spa_route = client.get("/activities/seed-activity-001")
        missing_api = client.get("/api/missing")

    assert root.status_code == 200
    assert "RunStats" in root.text
    assert asset.status_code == 200
    assert "runstats" in asset.text
    assert spa_route.status_code == 200
    assert "RunStats" in spa_route.text
    assert missing_api.status_code == 404
    assert missing_api.json()["error"]["code"] == "NOT_FOUND"
