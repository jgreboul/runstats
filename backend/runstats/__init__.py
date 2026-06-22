"""RunStats backend package."""

from typing import TypedDict

__version__ = "0.1.0"


class ProjectStatus(TypedDict):
    """Small typed status object used by Phase 0 tooling tests."""

    name: str
    phase: str


def get_project_status() -> ProjectStatus:
    """Return the current backend implementation status for smoke tests."""

    return {"name": "RunStats", "phase": "backend_foundation"}
