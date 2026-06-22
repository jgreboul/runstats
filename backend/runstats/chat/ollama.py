"""Ollama-compatible local HTTP chat provider."""

from __future__ import annotations

import json
from collections.abc import Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from runstats.chat.provider import ChatModelUnavailable
from runstats.schemas import ChatToolResult


class OllamaChatProvider:
    """Generate grounded answers through a local Ollama-compatible endpoint."""

    provider_name = "ollama"

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: float,
    ) -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self.model = model
        self.timeout_seconds = timeout_seconds

    def generate_answer(
        self,
        *,
        question: str,
        tool_results: Sequence[ChatToolResult],
    ) -> str:
        """Call the local model with summarized read-only tool results only."""

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are RunStats Chat Assistant. Answer only from the "
                        "provided local tool summaries. Be concise. Do not invent "
                        "data. For health metrics, describe observed trends and "
                        "avoid diagnosis, prescriptions, or medical advice."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "question": question,
                            "tool_results": [
                                result.model_dump(mode="json")
                                for result in tool_results
                            ],
                        },
                        sort_keys=True,
                    ),
                },
            ],
            "stream": False,
        }
        request = Request(
            urljoin(self.base_url, "api/chat"),
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw_payload = response.read().decode("utf-8")
        except (HTTPError, URLError, OSError) as exc:
            raise ChatModelUnavailable(
                "The local chat model is unavailable."
            ) from exc

        try:
            response_payload = json.loads(raw_payload)
        except json.JSONDecodeError as exc:
            raise ChatModelUnavailable(
                "The local chat model returned invalid JSON."
            ) from exc

        answer = _extract_answer(response_payload)
        if answer is None:
            raise ChatModelUnavailable(
                "The local chat model returned an empty answer."
            )
        return answer


def _extract_answer(payload: object) -> str | None:
    if not isinstance(payload, dict):
        return None
    message = payload.get("message")
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    if not isinstance(content, str):
        return None
    stripped = content.strip()
    return stripped or None
