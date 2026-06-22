"""Provider-neutral chatbot response generation contracts."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from runstats.schemas import ChatToolResult


class ChatModelUnavailable(Exception):
    """Raised when the configured chat model cannot produce an answer."""


class ChatResponseProvider(Protocol):
    """Generate an answer from a user question and approved tool summaries."""

    provider_name: str

    def generate_answer(
        self,
        *,
        question: str,
        tool_results: Sequence[ChatToolResult],
    ) -> str:
        """Return concise answer text for the user."""
        ...
