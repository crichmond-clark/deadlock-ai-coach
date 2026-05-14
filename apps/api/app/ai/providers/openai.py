"""OpenAI provider adapter."""

from app.ai.providers.openai_compatible import OpenAICompatibleProvider


class OpenAIProvider(OpenAICompatibleProvider):
    """OpenAI chat provider using the OpenAI-compatible HTTP API."""

    def __init__(self, *, api_key: str | None = None, base_url: str | None = None) -> None:
        super().__init__(provider_name="openai", base_url=base_url or "https://api.openai.com/v1", api_key=api_key)
