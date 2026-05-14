"""Tests for structured AI analysis schemas and prompt context."""

from __future__ import annotations

from app.db.models import Upload, UploadKind, UploadStatus
from app.schemas.ai_analysis import CoachingAnalysisResult
from app.services.ai_analysis.context import build_analysis_input_context


def test_coaching_analysis_schema_accepts_valid_payload():
    result = CoachingAnalysisResult.model_validate(
        {
            "schema_version": "coaching-analysis-v1",
            "title": "Good match review",
            "executive_summary": "You played well around objectives but overcommitted in late fights.",
            "confidence": "medium",
            "match_context": {"source_mode": "user_summary", "summary": "summary", "match_id": None},
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
    )
    assert result.summary.startswith("You played well")


def test_context_builder_truncates_large_summary():
    upload = Upload(
        user_id="00000000-0000-0000-0000-000000000001",
        kind=UploadKind.MATCH_SUMMARY,
        status=UploadStatus.CREATED,
        summary_text="x" * 5000,
    )
    context = build_analysis_input_context(upload=upload)
    assert context.match_summary_text is not None
    assert len(context.match_summary_text) == 4000
    assert "truncated" in context.source_warnings[0]


def test_context_builder_compacts_replay_summary():
    upload = Upload(
        user_id="00000000-0000-0000-0000-000000000001",
        kind=UploadKind.REPLAY,
        status=UploadStatus.CREATED,
    )
    context = build_analysis_input_context(
        upload=upload,
        replay_parse_summary={"players": list(range(30)), "timeline": list(range(30)), "extra": "omit"},
    )
    assert context.replay_parse_summary is not None
    assert len(context.replay_parse_summary["players"]) == 20
    assert "extra" not in context.replay_parse_summary
