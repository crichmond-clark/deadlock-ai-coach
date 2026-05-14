"""Provider factory for configured AI chat providers."""

from __future__ import annotations

from typing import Literal

from app.ai.errors import AIProviderConfigurationError
from app.ai.providers.base import ChatModelProvider
from app.ai.providers.mock import MockAIProvider
from app.ai.providers.openai import OpenAIProvider
from app.ai.providers.openai_compatible import OpenAICompatibleProvider
from app.core.config import settings

AIProviderName = Literal["openai", "openai_compatible", "minimax", "mock"]


def get_chat_provider(provider_name: str | None = None) -> ChatModelProvider:
    """Build the configured chat provider."""
    name = provider_name or settings.ai_provider
    if name == "mock":
        return MockAIProvider()
    if name == "openai":
        return OpenAIProvider(api_key=settings.openai_api_key or settings.ai_api_key, base_url=settings.ai_base_url or None)
    if name == "openai_compatible":
        if not settings.ai_base_url:
            raise AIProviderConfigurationError("AI_BASE_URL is required for openai_compatible provider")
        return OpenAICompatibleProvider(base_url=settings.ai_base_url, api_key=settings.ai_api_key or settings.openai_api_key)
    if name == "minimax":
        if not settings.ai_base_url:
            raise AIProviderConfigurationError("AI_BASE_URL is required for minimax provider")
        return OpenAICompatibleProvider(provider_name="minimax", base_url=settings.ai_base_url, api_key=settings.ai_api_key)
    raise AIProviderConfigurationError(f"unsupported AI provider: {name}")
