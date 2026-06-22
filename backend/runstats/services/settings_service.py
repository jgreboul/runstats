"""Application settings service."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

from sqlalchemy.orm import Session

from runstats.config import Settings
from runstats.db.models import AppSettings
from runstats.schemas import (
    AppSettingsPatchRequest,
    AppSettingsResponse,
    ChatProvider,
    ChatRetentionPolicy,
    HostedChatProvider,
    LocalChatProvider,
)


class SettingsService:
    """Read and update single-row local application settings."""

    def __init__(self, session: Session, runtime_settings: Settings) -> None:
        self.session = session
        self.runtime_settings = runtime_settings

    def get_settings(self) -> AppSettingsResponse:
        """Return persisted settings, creating design defaults when absent."""

        settings = self._ensure_settings()
        return _settings_response(settings)

    def update_settings(
        self,
        patch: AppSettingsPatchRequest,
    ) -> AppSettingsResponse:
        """Apply a validated partial settings update."""

        settings = self._ensure_settings()
        update_data = patch.model_dump(exclude_unset=True)
        for field_name, value in update_data.items():
            setattr(settings, field_name, value)
        settings.updated_at = datetime.now(UTC)
        self.session.commit()
        self.session.refresh(settings)
        return _settings_response(settings)

    def _ensure_settings(self) -> AppSettings:
        settings = self.session.get(AppSettings, 1)
        if settings is not None:
            return settings

        now = datetime.now(UTC)
        settings = AppSettings(
            id=1,
            raw_archive_path=str(self.runtime_settings.raw_archive_path),
            chat_provider="local",
            local_chat_provider="ollama",
            hosted_chat_provider=None,
            chat_retention_policy="retain_until_deleted",
            created_at=now,
            updated_at=now,
        )
        self.session.add(settings)
        self.session.commit()
        self.session.refresh(settings)
        return settings


def _settings_response(settings: AppSettings) -> AppSettingsResponse:
    return AppSettingsResponse(
        raw_archive_path=settings.raw_archive_path,
        chat_provider=cast(ChatProvider, settings.chat_provider),
        local_chat_provider=cast(LocalChatProvider, settings.local_chat_provider),
        hosted_chat_provider=cast(
            HostedChatProvider | None,
            settings.hosted_chat_provider,
        ),
        chat_retention_policy=cast(
            ChatRetentionPolicy,
            settings.chat_retention_policy,
        ),
        created_at=settings.created_at,
        updated_at=settings.updated_at,
    )
