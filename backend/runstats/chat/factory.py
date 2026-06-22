"""Factory for configured chat response providers."""

from __future__ import annotations

from runstats.chat.ollama import OllamaChatProvider
from runstats.chat.provider import ChatModelUnavailable, ChatResponseProvider
from runstats.config import Settings
from runstats.schemas import AppSettingsResponse


def create_chat_response_provider(
    app_settings: AppSettingsResponse,
    runtime_settings: Settings,
) -> ChatResponseProvider:
    """Build the configured chat provider adapter."""

    if app_settings.chat_provider == "disabled":
        raise ChatModelUnavailable("Chat Assistant is disabled in app settings.")

    if app_settings.chat_provider == "hosted":
        raise ChatModelUnavailable(
            "Hosted chat providers are disabled for this local-first release."
        )

    if app_settings.local_chat_provider == "ollama":
        return OllamaChatProvider(
            base_url=runtime_settings.local_chat_base_url,
            model=runtime_settings.local_chat_model,
            timeout_seconds=runtime_settings.local_chat_timeout_seconds,
        )

    raise ChatModelUnavailable("The configured local chat provider is unsupported.")
