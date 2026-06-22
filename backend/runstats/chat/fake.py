"""Deterministic chat provider used by tests."""

from __future__ import annotations

from collections.abc import Sequence

from runstats.schemas import ChatToolResult


class FakeChatProvider:
    """Return stable prose from tool summaries without calling a model."""

    provider_name = "fake"

    def generate_answer(
        self,
        *,
        question: str,
        tool_results: Sequence[ChatToolResult],
    ) -> str:
        """Build a deterministic answer for tests and local service coverage."""

        if not tool_results:
            return (
                "I can answer descriptive questions about imported runs, health "
                "metrics, and sync history. I could not match that question to an "
                "approved read-only tool yet."
            )

        summaries = [result.summary for result in tool_results]
        answer = " ".join(summaries)
        if any(result.tool_name.startswith("health") for result in tool_results):
            answer = (
                f"{answer} Health-related results describe observed local data "
                "only and are not medical advice."
            )
        if "workout" in question.lower() or "training plan" in question.lower():
            answer = (
                f"{answer} Suggested workout generation is intentionally deferred "
                "for this release."
            )
        return answer
