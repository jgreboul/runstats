"""Chat assistant APIs."""

from __future__ import annotations

from typing import Annotated, cast

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.orm import Session
from starlette import status

from runstats.chat import ChatResponseProvider
from runstats.config import Settings
from runstats.db.session import get_db_session
from runstats.schemas import (
    ChatAnswerResponse,
    ChatQuestionRequest,
    ChatSessionCreateRequest,
    ChatSessionListResponse,
    ChatSessionResponse,
)
from runstats.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])
SessionDep = Annotated[Session, Depends(get_db_session)]


@router.post("/sessions", response_model=ChatSessionResponse, status_code=201)
def create_chat_session(
    request_body: ChatSessionCreateRequest,
    request: Request,
    session: SessionDep,
) -> ChatSessionResponse:
    """Create a local chat session."""

    return _service(request, session).create_session(request_body)


@router.get("/sessions", response_model=ChatSessionListResponse)
def list_chat_sessions(
    request: Request,
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ChatSessionListResponse:
    """List recent local chat sessions."""

    return _service(request, session).list_sessions(limit=limit, offset=offset)


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
def get_chat_session(
    session_id: str,
    request: Request,
    session: SessionDep,
) -> ChatSessionResponse:
    """Return one chat session and its messages."""

    return _service(request, session).get_session(session_id)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat_session(
    session_id: str,
    request: Request,
    session: SessionDep,
) -> Response:
    """Delete one chat session and its messages."""

    _service(request, session).delete_session(session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/sessions", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat_history(request: Request, session: SessionDep) -> Response:
    """Delete all local chat sessions and messages."""

    _service(request, session).delete_all_sessions()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/sessions/{session_id}/messages",
    response_model=ChatAnswerResponse,
)
def ask_chat_question(
    session_id: str,
    question: ChatQuestionRequest,
    request: Request,
    session: SessionDep,
) -> ChatAnswerResponse:
    """Ask the assistant a question about local data."""

    return _service(request, session).answer_question(session_id, question)


def _service(request: Request, session: Session) -> ChatService:
    runtime_settings = cast(Settings, request.app.state.settings)
    provider = cast(
        ChatResponseProvider | None,
        getattr(request.app.state, "chat_response_provider", None),
    )
    return ChatService(session, runtime_settings, provider)
