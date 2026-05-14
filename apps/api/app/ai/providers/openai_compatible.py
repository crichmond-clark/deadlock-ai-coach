"""OpenAI-compatible chat completion provider."""

from __future__ import annotations

import json
import time
from typing import Any

import httpx

from app.ai.errors import (
    AIProviderConfigurationError,
    AIProviderError,
    AIProviderInvalidResponseError,
    AIProviderTimeoutError,
)
from app.ai.providers.base import AIProviderResponse, AIRequestOptions, ChatMessage

_DEFAULT_BASE_URL = "https://api.openai.com/v1"


def extract_json_object(text: str) -> dict[str, Any]:
    """Extract the first JSON object from provider text output."""
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise AIProviderInvalidResponseError("provider response did not contain JSON") from None
        try:
            parsed = json.loads(stripped[start : end + 1])
        except json.JSONDecodeError as exc:
            raise AIProviderInvalidResponseError("provider response contained invalid JSON") from exc
    if not isinstance(parsed, dict):
        raise AIProviderInvalidResponseError("provider JSON response must be an object")
    return parsed


class OpenAICompatibleProvider:
    """Chat provider for OpenAI and OpenAI-compatible /chat/completions APIs."""

    def __init__(
        self,
        *,
        provider_name: str = "openai_compatible",
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.provider_name = provider_name
        self.base_url = (base_url or _DEFAULT_BASE_URL).rstrip("/")
        self.api_key = api_key

    async def generate_json(
        self,
        *,
        messages: list[ChatMessage],
        schema_name: str,
        schema_json: dict[str, Any],
        options: AIRequestOptions,
    ) -> AIProviderResponse:
        """Request one JSON chat completion and normalize the provider response."""
        if not self.api_key:
            raise AIProviderConfigurationError(f"{self.provider_name} API key is not configured")

        payload = {
            "model": options.model,
            "messages": [message.model_dump() for message in messages],
            "temperature": options.temperature,
            "max_tokens": options.max_output_tokens,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "schema": schema_json,
                    "strict": True,
                },
            },
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=options.timeout_seconds) as client:
                response = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
        except httpx.TimeoutException:
            raise AIProviderTimeoutError(f"timeout requesting {self.base_url}/chat/completions") from None
        except httpx.HTTPError as exc:
            raise AIProviderError(str(exc)[:500]) from exc

        latency_ms = int((time.perf_counter() - started) * 1000)
        if response.status_code >= 400:
            raise AIProviderError(response.text[:500] or f"provider status {response.status_code}")

        try:
            body = response.json()
            choice = body["choices"][0]
            raw_text = choice["message"]["content"]
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise AIProviderInvalidResponseError("provider response shape was invalid") from exc

        if not isinstance(raw_text, str):
            raise AIProviderInvalidResponseError("provider message content was not text")

        usage = body.get("usage") if isinstance(body, dict) else None
        usage = usage if isinstance(usage, dict) else {}
        return AIProviderResponse(
            content=extract_json_object(raw_text),
            raw_text=raw_text,
            model_name=str(body.get("model") or options.model),
            provider=self.provider_name,
            latency_ms=latency_ms,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            total_tokens=usage.get("total_tokens"),
            response_metadata={"finish_reason": choice.get("finish_reason")},
        )
