"""Tests for structured AI analysis generation service."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai.errors import AISchemaValidationError
from app.ai.providers.base import AIProviderResponse, AIRequestOptions, ChatMessage
from app.db.models import AnalysisJob, Upload, UploadKind, UploadStatus
from app.services.ai_analysis.generator import generate_structured_analysis


class StaticProvider:
    def __init__(self, content: dict):
        self.content = content

    async def generate_json(
        self,
        *,
        messages: list[ChatMessage],
        schema_name: str,
        schema_json: dict,
        options: AIRequestOptions,
    ) -> AIProviderResponse:
        del messages, schema_name, schema_json
        return AIProviderResponse(
            content=self.content,
            model_name=options.model,
            provider="mock",
            latency_ms=12,
            input_tokens=10,
            output_tokens=20,
            total_tokens=30,
        )


def _valid_content() -> dict:
    return {
        "schema_version": "coaching-analysis-v1",
        "title": "Structured review",
        "executive_summary": "A useful structured summary.",
        "confidence": "high",
        "match_context": {"source_mode": "user_summary", "summary": "context"},
        "strengths": [],
        "improvement_areas": [],
        "key_moments": [],
        "build_advice": [],
        "priority_focus": [],
        "evidence": [],
        "source_warnings": [],
        "model_metadata": {
            "provider": "mock",
            "model": "mock-model",
            "prompt_version": "coaching-analysis-prompt-v1",
            "workflow_version": "structured-ai-analysis-v1",
        },
    }


def _job_and_upload():
    user_id = uuid.uuid4()
    job = AnalysisJob(id=uuid.uuid4(), user_id=user_id, upload_id=uuid.uuid4())
    upload = Upload(
        id=job.upload_id,
        user_id=user_id,
        kind=UploadKind.MATCH_SUMMARY,
        status=UploadStatus.CREATED,
        summary_text="I won lane but lost late fights.",
    )
    return job, upload


@pytest.mark.asyncio
async def test_generate_structured_analysis_persists_succeeded_model_run(monkeypatch):
    monkeypatch.setattr("app.services.ai_analysis.generator.settings.ai_provider", "mock")
    monkeypatch.setattr("app.services.ai_analysis.generator.settings.ai_model", "mock-model")
    db = MagicMock()
    db.flush = AsyncMock()
    job, upload = _job_and_upload()

    result = await generate_structured_analysis(
        db,
        job=job,
        upload=upload,
        provider=StaticProvider(_valid_content()),
    )

    assert result.title == "Structured review"
    db.add.assert_called_once()
    model_run = db.add.call_args.args[0]
    assert model_run.status == "succeeded"
    assert model_run.total_tokens == 30
    assert db.flush.await_count == 1


@pytest.mark.asyncio
async def test_generate_structured_analysis_marks_model_run_failed_on_schema_error(monkeypatch):
    monkeypatch.setattr("app.services.ai_analysis.generator.settings.ai_provider", "mock")
    monkeypatch.setattr("app.services.ai_analysis.generator.settings.ai_model", "mock-model")
    db = MagicMock()
    db.flush = AsyncMock()
    job, upload = _job_and_upload()

    with pytest.raises(AISchemaValidationError):
        await generate_structured_analysis(
            db,
            job=job,
            upload=upload,
            provider=StaticProvider({"schema_version": "coaching-analysis-v1"}),
        )

    model_run = db.add.call_args.args[0]
    assert model_run.status == "failed"
    assert model_run.error_message
    assert db.flush.await_count == 1
