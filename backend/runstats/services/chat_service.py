"""Chat assistant persistence, tool orchestration, and response storage."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import cast

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload
from starlette import status

from runstats.api.errors import RunStatsError
from runstats.chat import ChatModelUnavailable, ChatResponseProvider
from runstats.chat.factory import create_chat_response_provider
from runstats.chat.tools import ChatToolRegistry
from runstats.config import Settings
from runstats.db.models import ChatMessage, ChatSession
from runstats.schemas import (
    AppSettingsResponse,
    ChatAnswerResponse,
    ChatMessageResponse,
    ChatMessageRole,
    ChatQuestionRequest,
    ChatReference,
    ChatSessionCreateRequest,
    ChatSessionListItem,
    ChatSessionListResponse,
    ChatSessionResponse,
    ChatSupportingData,
    ChatToolResult,
)
from runstats.services.settings_service import SettingsService

HEALTH_METRIC_ALIASES = {
    "body battery": "body_battery",
    "body_battery": "body_battery",
    "hrv": "hrv",
    "pulse ox": "pulse_ox",
    "pulse_ox": "pulse_ox",
    "respiration": "respiration",
    "resting heart rate": "resting_hr",
    "resting hr": "resting_hr",
    "resting_hr": "resting_hr",
    "sleep": "sleep",
    "steps": "steps",
    "stress": "stress",
}


@dataclass(frozen=True)
class ChatIntent:
    """Tool choice inferred from a user question."""

    name: str
    metric_type: str | None = None
    min_distance_meters: float | None = None
    include_activity_detail: bool = False


class ChatService:
    """Persist chat history and answer questions through approved tools."""

    def __init__(
        self,
        session: Session,
        runtime_settings: Settings,
        provider: ChatResponseProvider | None = None,
    ) -> None:
        self.session = session
        self.runtime_settings = runtime_settings
        self.provider = provider

    def create_session(
        self,
        request: ChatSessionCreateRequest,
    ) -> ChatSessionResponse:
        """Create a local chat session."""

        self._app_settings()
        now = datetime.now(UTC)
        chat_session = ChatSession(
            title=request.title,
            created_at=now,
            updated_at=now,
        )
        self.session.add(chat_session)
        self.session.commit()
        self.session.refresh(chat_session)
        return _session_response(chat_session)

    def list_sessions(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> ChatSessionListResponse:
        """Return recent chat sessions with lightweight previews."""

        total = int(
            self.session.scalar(select(func.count()).select_from(ChatSession)) or 0
        )
        sessions = list(
            self.session.scalars(
                select(ChatSession)
                .options(selectinload(ChatSession.messages))
                .order_by(ChatSession.updated_at.desc(), ChatSession.id)
                .limit(limit)
                .offset(offset)
            ).all()
        )
        return ChatSessionListResponse(
            items=[_session_list_item(chat_session) for chat_session in sessions],
            total=total,
            limit=limit,
            offset=offset,
        )

    def get_session(self, session_id: str) -> ChatSessionResponse:
        """Return one chat session with ordered messages."""

        return _session_response(self._get_session(session_id))

    def delete_session(self, session_id: str) -> None:
        """Delete one chat session and its messages."""

        chat_session = self._get_session(session_id)
        self.session.delete(chat_session)
        self.session.commit()

    def delete_all_sessions(self) -> None:
        """Delete all local chat history."""

        sessions = list(self.session.scalars(select(ChatSession)).all())
        for chat_session in sessions:
            self.session.delete(chat_session)
        self.session.commit()

    def answer_question(
        self,
        session_id: str,
        request: ChatQuestionRequest,
    ) -> ChatAnswerResponse:
        """Store a user question and assistant answer for one session."""

        app_settings = self._app_settings()
        chat_session = self._get_session(session_id)
        question = request.message.strip()
        now = datetime.now(UTC)
        user_message = ChatMessage(
            session=chat_session,
            role="user",
            content=question,
            created_at=now,
        )
        self.session.add(user_message)
        if chat_session.title is None:
            chat_session.title = _title_from_question(question)
        chat_session.updated_at = now
        self.session.commit()
        self.session.refresh(chat_session)

        tool_results = self._run_tools(question)
        supporting_data = _supporting_data_from_results(tool_results)
        answer = self._generate_answer(question, tool_results, app_settings)

        assistant_message = ChatMessage(
            session=chat_session,
            role="assistant",
            content=answer,
            tool_trace_json=supporting_data.model_dump_json(),
            created_at=datetime.now(UTC),
        )
        chat_session.updated_at = assistant_message.created_at
        self.session.add(assistant_message)
        self.session.commit()
        self.session.refresh(assistant_message)
        return ChatAnswerResponse(
            message_id=assistant_message.id,
            answer=assistant_message.content,
            supporting_data=supporting_data,
        )

    def _run_tools(self, question: str) -> list[ChatToolResult]:
        intent = _classify_question(question)
        if intent.name == "unsupported":
            return []

        start_at, end_at = _date_range_for_question(question)
        tools = ChatToolRegistry(self.session)

        if intent.name == "weekly_running_summary":
            return [
                tools.weekly_running_summary(start_at=start_at, end_at=end_at),
            ]
        if intent.name == "monthly_running_summary":
            return [
                tools.monthly_running_summary(start_at=start_at, end_at=end_at),
            ]
        if intent.name == "fastest_run_by_distance_threshold":
            threshold = intent.min_distance_meters or 5000.0
            results = [
                tools.fastest_run_by_distance_threshold(
                    min_distance_meters=threshold,
                    start_at=start_at,
                    end_at=end_at,
                )
            ]
            if intent.include_activity_detail and results[0].references:
                results.append(tools.activity_detail_lookup(results[0].references[0].id))
            return results
        if intent.name == "longest_run":
            results = [tools.longest_run(start_at=start_at, end_at=end_at)]
            if intent.include_activity_detail and results[0].references:
                results.append(tools.activity_detail_lookup(results[0].references[0].id))
            return results
        if intent.name == "activity_detail_lookup":
            activity_id = _activity_id_from_question(question)
            if activity_id is None:
                return [tools.longest_run(start_at=start_at, end_at=end_at)]
            return [tools.activity_detail_lookup(activity_id)]
        if intent.name == "health_metric_trend" and intent.metric_type is not None:
            return [
                tools.health_metric_trend(
                    metric_type=intent.metric_type,
                    start_at=start_at,
                    end_at=end_at,
                )
            ]
        if (
            intent.name == "activity_health_comparison"
            and intent.metric_type is not None
        ):
            return [tools.activity_health_comparison(metric_type=intent.metric_type)]
        if intent.name == "sync_status_lookup":
            return [tools.sync_status_lookup()]

        return []

    def _generate_answer(
        self,
        question: str,
        tool_results: list[ChatToolResult],
        app_settings: AppSettingsResponse,
    ) -> str:
        if not tool_results:
            return _unsupported_answer(question)

        provider = self.provider
        if provider is None:
            try:
                provider = create_chat_response_provider(
                    app_settings,
                    self.runtime_settings,
                )
            except ChatModelUnavailable as exc:
                raise _model_unavailable(exc) from exc

        try:
            return provider.generate_answer(
                question=question,
                tool_results=tool_results,
            )
        except ChatModelUnavailable as exc:
            raise _model_unavailable(exc) from exc

    def _get_session(self, session_id: str) -> ChatSession:
        chat_session = self.session.scalar(
            select(ChatSession)
            .where(ChatSession.id == session_id)
            .options(selectinload(ChatSession.messages))
        )
        if chat_session is None:
            raise RunStatsError(
                "CHAT_SESSION_NOT_FOUND",
                "Chat session not found.",
                details={"session_id": session_id},
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return chat_session

    def _app_settings(self) -> AppSettingsResponse:
        return SettingsService(self.session, self.runtime_settings).get_settings()


def _classify_question(question: str) -> ChatIntent:
    normalized = question.lower()
    metric_type = _metric_from_question(normalized)
    wants_detail = any(
        token in normalized for token in ("detail", "heart-rate", "heart rate")
    )

    if "workout" in normalized or "training plan" in normalized:
        return ChatIntent("unsupported")
    if "sync" in normalized:
        return ChatIntent("sync_status_lookup")
    if metric_type is not None and any(
        token in normalized
        for token in ("compare", "correlat", "improve", "during weeks")
    ):
        return ChatIntent("activity_health_comparison", metric_type=metric_type)
    if "fastest" in normalized or "best pace" in normalized:
        return ChatIntent(
            "fastest_run_by_distance_threshold",
            min_distance_meters=_distance_threshold_from_question(normalized),
            include_activity_detail=wants_detail,
        )
    if "longest" in normalized:
        return ChatIntent("longest_run", include_activity_detail=wants_detail)
    if metric_type is not None:
        return ChatIntent("health_metric_trend", metric_type=metric_type)
    if (
        _activity_id_from_question(question) is not None
        or "activity detail" in normalized
    ):
        return ChatIntent("activity_detail_lookup")
    if "monthly" in normalized or "month" in normalized:
        return ChatIntent("monthly_running_summary")
    if any(token in normalized for token in ("weekly", "week", "mileage")):
        return ChatIntent("weekly_running_summary")
    if "how much" in normalized and "run" in normalized:
        return ChatIntent("weekly_running_summary")
    if "summary" in normalized and "run" in normalized:
        return ChatIntent("weekly_running_summary")
    return ChatIntent("unsupported")


def _metric_from_question(normalized_question: str) -> str | None:
    for alias, metric_type in HEALTH_METRIC_ALIASES.items():
        if alias in normalized_question:
            return metric_type
    return None


def _distance_threshold_from_question(normalized_question: str) -> float:
    if "10k" in normalized_question:
        return 10000.0
    if "5k" in normalized_question:
        return 5000.0
    match = re.search(
        r"over\s+(\d+(?:\.\d+)?)\s*(?:km|kilometers)",
        normalized_question,
    )
    if match is not None:
        return float(match.group(1)) * 1000.0
    return 5000.0


def _activity_id_from_question(question: str) -> str | None:
    matches: list[str] = re.findall(
        r"\b[\w-]*activity[\w-]*\b",
        question,
        flags=re.IGNORECASE,
    )
    for match in matches:
        if match.lower() != "activity":
            return match
    return None


def _date_range_for_question(
    question: str,
    now: datetime | None = None,
) -> tuple[datetime | None, datetime | None]:
    normalized = question.lower()
    current = now or datetime.now(UTC)

    if "this year" in normalized:
        return datetime(current.year, 1, 1, tzinfo=UTC), current
    if "last 12 weeks" in normalized:
        return current - timedelta(weeks=12), current
    if "last 30 days" in normalized or "past month" in normalized:
        return current - timedelta(days=30), current
    if "last month" in normalized:
        month_start = current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        previous_month_end = month_start - timedelta(microseconds=1)
        previous_month_start = previous_month_end.replace(
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        return previous_month_start, previous_month_end
    return None, None


def _supporting_data_from_results(
    tool_results: list[ChatToolResult],
) -> ChatSupportingData:
    if not tool_results:
        return ChatSupportingData(
            intent="unsupported",
            tool_names=[],
            time_range=None,
            metrics=[],
            row_count=0,
            references=[],
            notes=[],
        )

    references = _dedupe_references(
        [
            reference
            for result in tool_results
            for reference in result.references
        ]
    )
    return ChatSupportingData(
        intent=tool_results[0].intent if len(tool_results) == 1 else "combined",
        tool_names=[result.tool_name for result in tool_results],
        time_range=_combine_ranges(
            [result.time_range for result in tool_results if result.time_range]
        ),
        metrics=_dedupe_strings(
            [metric for result in tool_results for metric in result.metrics]
        ),
        row_count=sum(result.row_count for result in tool_results),
        references=references,
        notes=_dedupe_strings(
            [note for result in tool_results for note in result.notes]
        ),
    )


def _dedupe_references(references: list[ChatReference]) -> list[ChatReference]:
    seen: set[tuple[str, str]] = set()
    deduped: list[ChatReference] = []
    for reference in references:
        key = (reference.type, reference.id)
        if key not in seen:
            seen.add(key)
            deduped.append(reference)
    return deduped


def _dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            deduped.append(value)
    return deduped


def _combine_ranges(ranges: list[str]) -> str | None:
    deduped = _dedupe_strings(ranges)
    if not deduped:
        return None
    return "; ".join(deduped)


def _session_response(chat_session: ChatSession) -> ChatSessionResponse:
    return ChatSessionResponse(
        id=chat_session.id,
        title=chat_session.title,
        created_at=chat_session.created_at,
        updated_at=chat_session.updated_at,
        messages=[_message_response(message) for message in chat_session.messages],
    )


def _session_list_item(chat_session: ChatSession) -> ChatSessionListItem:
    last_message = chat_session.messages[-1] if chat_session.messages else None
    return ChatSessionListItem(
        id=chat_session.id,
        title=chat_session.title,
        created_at=chat_session.created_at,
        updated_at=chat_session.updated_at,
        message_count=len(chat_session.messages),
        last_message_preview=(
            _preview(last_message.content) if last_message is not None else None
        ),
    )


def _message_response(message: ChatMessage) -> ChatMessageResponse:
    return ChatMessageResponse(
        id=message.id,
        session_id=message.session_id,
        role=cast(ChatMessageRole, message.role),
        content=message.content,
        tool_trace=_trace_from_json(message.tool_trace_json),
        created_at=message.created_at,
    )


def _trace_from_json(raw_trace: str | None) -> ChatSupportingData | None:
    if raw_trace is None:
        return None
    try:
        payload = json.loads(raw_trace)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    references = payload.get("references", [])
    parsed_references = [
        ChatReference.model_validate(reference)
        for reference in references
        if isinstance(reference, dict)
    ]
    return ChatSupportingData(
        intent=str(payload.get("intent", "unknown")),
        tool_names=[
            str(tool_name)
            for tool_name in payload.get("tool_names", [])
            if isinstance(tool_name, str)
        ],
        time_range=(
            str(payload["time_range"])
            if payload.get("time_range") is not None
            else None
        ),
        metrics=[
            str(metric)
            for metric in payload.get("metrics", [])
            if isinstance(metric, str)
        ],
        row_count=int(payload.get("row_count", 0) or 0),
        references=parsed_references,
        notes=[
            str(note)
            for note in payload.get("notes", [])
            if isinstance(note, str)
        ],
    )


def _preview(content: str) -> str:
    collapsed = " ".join(content.split())
    if len(collapsed) <= 100:
        return collapsed
    return f"{collapsed[:97].rstrip()}..."


def _title_from_question(question: str) -> str:
    title = _preview(question)
    if len(title) <= 60:
        return title
    return f"{title[:57].rstrip()}..."


def _unsupported_answer(question: str) -> str:
    if "workout" in question.lower() or "training plan" in question.lower():
        return (
            "Suggested workout generation is deferred for a later release. I can "
            "summarize recent training data now, but I will not present workout "
            "ideas as medical guidance."
        )
    return (
        "I can answer descriptive questions about imported runs, health metrics, "
        "and sync history. I could not match that question to an approved "
        "read-only tool yet."
    )


def _model_unavailable(exc: ChatModelUnavailable) -> RunStatsError:
    return RunStatsError(
        "CHAT_MODEL_UNAVAILABLE",
        str(exc) or "The configured chat model is unavailable.",
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    )
