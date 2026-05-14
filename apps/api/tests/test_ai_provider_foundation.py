"""Tests for AI provider foundation."""

from __future__ import annotations

import json

import pytest
from pytest_httpx import HTTPXMock

from app.ai.errors import AIProviderInvalidResponseError
from app.ai.providers.base import AIRequestOptions, ChatMessage
from app.ai.providers.mock import MockAIProvider
from app.ai.providers.openai_compatible import OpenAICompatibleProvider, extract_json_object


def test_extract_json_object_from_plain_json():
    assert extract_json_object('{"ok": true}') == {"ok": True}


def test_extract_json_object_from_fenced_json():
    assert extract_json_object('```json\n{"ok": true}\n```') == {"ok": True}


def test_extract_json_object_rejects_non_json():
    with pytest.raises(AIProviderInvalidResponseError):
        extract_json_object("not json")


@pytest.mark.asyncio
async def test_mock_provider_returns_schema_valid_payload():
    provider = MockAIProvider()
    response = await provider.generate_json(
        messages=[ChatMessage(role="user", content="hello")],
        schema_name="CoachingAnalysisResult",
        schema_json={},
        options=AIRequestOptions(model="mock-model"),
    )
    assert response.provider == "mock"
    assert response.content["schema_version"] == "coaching-analysis-v1"
    assert response.content["model_metadata"]["model"] == "mock-model"


@pytest.mark.asyncio
async def test_openai_compatible_provider_success(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://example.test/v1/chat/completions",
        json={
            "model": "test-model",
            "choices": [{"message": {"content": json.dumps({"ok": True})}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        },
    )
    provider = OpenAICompatibleProvider(base_url="https://example.test/v1", api_key="test-key")
    response = await provider.generate_json(
        messages=[ChatMessage(role="user", content="hello")],
        schema_name="TestSchema",
        schema_json={},
        options=AIRequestOptions(model="test-model"),
    )
    assert response.content == {"ok": True}
    assert response.total_tokens == 15


@pytest.mark.asyncio
async def test_openai_compatible_provider_invalid_json(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://example.test/v1/chat/completions",
        json={"choices": [{"message": {"content": "not json"}}]},
    )
    provider = OpenAICompatibleProvider(base_url="https://example.test/v1", api_key="test-key")
    with pytest.raises(AIProviderInvalidResponseError):
        await provider.generate_json(
            messages=[ChatMessage(role="user", content="hello")],
            schema_name="TestSchema",
            schema_json={},
            options=AIRequestOptions(model="test-model"),
        )
