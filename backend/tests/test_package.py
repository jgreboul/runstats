from runstats import __version__, get_project_status


def test_backend_package_exposes_version() -> None:
    assert __version__ == "0.1.0"


def test_project_status_identifies_scaffold_phase() -> None:
    assert get_project_status() == {"name": "RunStats", "phase": "backend_foundation"}
