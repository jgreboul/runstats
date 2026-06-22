from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from runstats.api.errors import RunStatsError
from runstats.bluetooth import FakeWatchProvider
from runstats.chat.fake import FakeChatProvider
from runstats.chat.provider import ChatModelUnavailable
from runstats.chat.tools import APPROVED_CHAT_TOOL_NAMES, ChatToolRegistry
from runstats.config import Settings
from runstats.db.models import Base, ChatMessage, ChatSession
from runstats.db.seed import seed_development_data
from runstats.db.session import (
    SessionFactory,
    create_session_factory,
    create_sqlite_engine,
)
from runstats.schemas import ChatQuestionRequest, ChatSessionCreateRequest
from runstats.services.chat_service import ChatService


class FailingChatProvider:
    provider_name = "failing"

    def generate_answer(self, **_kwargs: object) -> str:
        raise ChatModelUnavailable("local model is offline")


def test_chat_service_persists_lists_retrieves_and_deletes_sessions(
    tmp_path: Path,
) -> None:
    session_factory = _seeded_session_factory(tmp_path)
    runtime_settings = Settings(database_path=tmp_path / "seeded.sqlite3")

    with session_factory() as session:
        service = ChatService(session, runtime_settings, FakeChatProvider())
        created = service.create_session(
            ChatSessionCreateRequest(title="Training questions")
        )
        answer = service.answer_question(
            created.id,
            ChatQuestionRequest(message="How much did I run each week?"),
        )
        listed = service.list_sessions(limit=10)
        retrieved = service.get_session(created.id)

        assert answer.supporting_data.intent == "weekly_running_summary"
        assert answer.supporting_data.row_count == 3
        assert retrieved.title == "Training questions"
        assert [message.role for message in retrieved.messages] == [
            "user",
            "assistant",
        ]
        assert retrieved.messages[1].tool_trace is not None
        assert listed.total == 2
        assert listed.items[0].message_count == 2

        service.delete_session(created.id)
        assert session.get(ChatSession, created.id) is None
        service.delete_all_sessions()
        assert session.query(ChatSession).count() == 0
        assert session.query(ChatMessage).count() == 0


def test_chat_tools_return_read_only_typed_summaries(tmp_path: Path) -> None:
    session_factory = _seeded_session_factory(tmp_path)

    with session_factory() as session:
        tools = ChatToolRegistry(session)
        weekly = tools.weekly_running_summary()
        monthly = tools.monthly_running_summary()
        fastest = tools.fastest_run_by_distance_threshold(min_distance_meters=5000)
        longest = tools.longest_run()
        detail = tools.activity_detail_lookup("seed-activity-003")
        health = tools.health_metric_trend(metric_type="steps")
        missing_health = tools.health_metric_trend(metric_type="body_battery")
        comparison = tools.activity_health_comparison(metric_type="resting_hr")
        sync = tools.sync_status_lookup()

    assert tools.read_only is True
    assert tools.approved_tool_names == APPROVED_CHAT_TOOL_NAMES
    assert "execute_sql" not in tools.approved_tool_names
    assert "sql" not in " ".join(tools.approved_tool_names)
    assert weekly.row_count == 3
    assert monthly.data["bucket_count"] == 1
    assert fastest.references[0].href == "/activities/seed-activity-002"
    assert longest.references[0].label == "Sunday Long Run"
    assert detail.data["lap_count"] == 6
    assert health.row_count == 3
    assert missing_health.notes == ["Metric 'body_battery' has not been imported."]
    assert comparison.intent == "activity_health_comparison"
    assert sync.references[0].href == "/sync-history/seed-sync-003"


def test_chat_orchestration_handles_paths_missing_data_and_deferred_workouts(
    tmp_path: Path,
) -> None:
    session_factory = _seeded_session_factory(tmp_path)
    runtime_settings = Settings(database_path=tmp_path / "seeded.sqlite3")

    with session_factory() as session:
        service = ChatService(session, runtime_settings, FakeChatProvider())
        created = service.create_session(ChatSessionCreateRequest())
        fastest = service.answer_question(
            created.id,
            ChatQuestionRequest(message="What is my fastest 5K this year?"),
        )
        missing_health = service.answer_question(
            created.id,
            ChatQuestionRequest(message="Show my body battery trend."),
        )
        workout = service.answer_question(
            created.id,
            ChatQuestionRequest(message="Suggest a workout for tomorrow."),
        )

    assert fastest.supporting_data.tool_names == [
        "fastest_run_by_distance_threshold"
    ]
    assert fastest.supporting_data.references[0].id == "seed-activity-002"
    assert missing_health.supporting_data.notes == [
        "Metric 'body_battery' has not been imported."
    ]
    assert "deferred" in workout.answer
    assert workout.supporting_data.intent == "unsupported"


def test_chat_service_maps_model_unavailable_after_storing_user_message(
    tmp_path: Path,
) -> None:
    session_factory = _seeded_session_factory(tmp_path)
    runtime_settings = Settings(database_path=tmp_path / "seeded.sqlite3")

    with session_factory() as session:
        service = ChatService(session, runtime_settings, FailingChatProvider())
        created = service.create_session(ChatSessionCreateRequest())
        with pytest.raises(RunStatsError) as error:
            service.answer_question(
                created.id,
                ChatQuestionRequest(message="How much did I run each week?"),
            )
        stored = service.get_session(created.id)

    assert error.value.code == "CHAT_MODEL_UNAVAILABLE"
    assert error.value.status_code == 503
    assert [message.role for message in stored.messages] == ["user"]


def test_chat_api_sessions_messages_and_delete_history(tmp_path: Path) -> None:
    app = _seeded_app(tmp_path, FakeChatProvider())

    with TestClient(app) as client:
        created = client.post(
            "/api/chat/sessions",
            json={"title": "API training questions"},
        )
        session_id = created.json()["id"]
        answer = client.post(
            f"/api/chat/sessions/{session_id}/messages",
            json={"message": "Show my longest run with heart-rate details."},
        )
        listed = client.get("/api/chat/sessions")
        retrieved = client.get(f"/api/chat/sessions/{session_id}")
        deleted = client.delete(f"/api/chat/sessions/{session_id}")
        delete_all = client.delete("/api/chat/sessions")

    assert created.status_code == 201
    assert answer.status_code == 200
    assert answer.json()["supporting_data"]["tool_names"] == [
        "longest_run",
        "activity_detail_lookup",
    ]
    assert answer.json()["supporting_data"]["references"][0]["href"] == (
        "/activities/seed-activity-003"
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 2
    assert retrieved.status_code == 200
    assert [message["role"] for message in retrieved.json()["messages"]] == [
        "user",
        "assistant",
    ]
    assert deleted.status_code == 204
    assert delete_all.status_code == 204


def test_chat_api_maps_model_errors(tmp_path: Path) -> None:
    app = _seeded_app(tmp_path, FailingChatProvider())

    with TestClient(app) as client:
        created = client.post("/api/chat/sessions", json={})
        response = client.post(
            f"/api/chat/sessions/{created.json()['id']}/messages",
            json={"message": "How much did I run each week?"},
        )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "CHAT_MODEL_UNAVAILABLE"


def _seeded_app(tmp_path: Path, chat_provider: object) -> FastAPI:
    settings = Settings(
        database_path=tmp_path / "api.sqlite3",
        raw_archive_path=tmp_path / "archive",
        watch_provider="fake",
    )
    app = create_test_app(settings, chat_provider)
    Base.metadata.create_all(bind=app.state.engine)
    session_factory: Any = app.state.session_factory
    with session_factory() as session:
        seed_development_data(session, settings.raw_archive_path)
    return app


def create_test_app(settings: Settings, chat_provider: object) -> FastAPI:
    from runstats.main import create_app

    return create_app(
        settings,
        watch_provider=FakeWatchProvider(),
        chat_response_provider=chat_provider,
    )


def _seeded_session_factory(tmp_path: Path) -> SessionFactory:
    session_factory = _session_factory(tmp_path, "seeded.sqlite3")
    with session_factory() as session:
        seed_development_data(session, tmp_path / "archive")
    return session_factory


def _session_factory(tmp_path: Path, filename: str) -> SessionFactory:
    settings = Settings(database_path=tmp_path / filename)
    engine = create_sqlite_engine(settings)
    Base.metadata.create_all(bind=engine)
    return create_session_factory(engine)
