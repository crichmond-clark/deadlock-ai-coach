"""Deterministic mock chat provider for tests and local development."""

from __future__ import annotations

from app.ai.providers.base import AIProviderResponse, AIRequestOptions, ChatMessage


class MockAIProvider:
    """Return schema-valid coaching analysis without calling an external provider."""

    async def generate_json(
        self,
        *,
        messages: list[ChatMessage],
        schema_name: str,
        schema_json: dict,
        options: AIRequestOptions,
    ) -> AIProviderResponse:
        del messages, schema_name, schema_json
        content = {
            "schema_version": "coaching-analysis-v1",
            "title": "Mock Deadlock Coaching Analysis",
            "executive_summary": "Mock provider generated deterministic coaching from the available match context.",
            "confidence": "medium",
            "match_context": {
                "hero": None,
                "match_id": None,
                "source_mode": "mock",
                "duration_seconds": None,
                "summary": "Deterministic mock analysis context.",
            },
            "strengths": [
                {
                    "title": "Reliable baseline play",
                    "description": "The submitted context contains enough signal for a baseline coaching pass.",
                    "impact": "medium",
                    "category": "macro",
                    "evidence_refs": ["mock-1"],
                }
            ],
            "improvement_areas": [
                {
                    "title": "Improve decision review",
                    "description": "Review key fight and objective decisions once richer replay evidence is available.",
                    "impact": "medium",
                    "category": "fighting",
                    "evidence_refs": ["mock-1"],
                }
            ],
            "key_moments": [],
            "build_advice": [],
            "priority_focus": [
                {
                    "title": "Review one replay segment",
                    "description": "Pick one major fight and identify the earliest avoidable mistake.",
                    "timebox_minutes": 15,
                    "evidence_refs": ["mock-1"],
                }
            ],
            "evidence": [
                {
                    "ref_id": "mock-1",
                    "source_type": "ai_inference",
                    "description": "Deterministic mock provider output for local/test execution.",
                    "data_path": None,
                }
            ],
            "source_warnings": [],
            "model_metadata": {
                "provider": "mock",
                "model": options.model,
                "prompt_version": "coaching-analysis-prompt-v1",
                "workflow_version": "structured-ai-analysis-v1",
            },
        }
        return AIProviderResponse(
            content=content,
            raw_text=None,
            model_name=options.model,
            provider="mock",
            latency_ms=0,
            response_metadata={"mock": True},
        )
