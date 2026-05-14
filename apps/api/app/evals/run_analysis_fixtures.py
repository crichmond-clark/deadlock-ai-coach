"""Run lightweight structured-analysis evaluation fixtures."""

import argparse
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.ai.providers.base import AIRequestOptions, ChatMessage
from app.ai.providers.mock import MockAIProvider
from app.schemas.ai_analysis import CoachingAnalysisResult


class EvaluationCase(BaseModel):
    """One deterministic evaluation fixture."""

    id: str
    name: str
    input_fixture: dict[str, Any]
    expected_schema_version: str = "coaching-analysis-v1"
    required_sections: list[str] = Field(default_factory=list)
    expected_evidence_source_types: list[str] = Field(default_factory=list)


def load_cases(fixtures_dir: Path | None = None) -> list[EvaluationCase]:
    """Load evaluation cases from JSON fixtures."""
    directory = fixtures_dir or Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "evals"
    return [EvaluationCase.model_validate_json(path.read_text()) for path in sorted(directory.glob("*.json"))]


async def run_case(case: EvaluationCase, *, provider: str) -> CoachingAnalysisResult:
    """Run one evaluation case using the deterministic mock provider."""
    if provider != "mock":
        raise ValueError("Only mock evaluation mode is implemented for deterministic local checks")
    mock = MockAIProvider()
    response = await mock.generate_json(
        messages=[ChatMessage(role="user", content=json.dumps(case.input_fixture))],
        schema_name="CoachingAnalysisResult",
        schema_json=CoachingAnalysisResult.model_json_schema(),
        options=AIRequestOptions(model="mock-model"),
    )
    result = CoachingAnalysisResult.model_validate(response.content)
    assert result.schema_version == case.expected_schema_version
    for section in case.required_sections:
        if not getattr(result, section):
            raise AssertionError(f"{case.id}: required section {section} was empty")
    actual_source_types = {evidence.source_type for evidence in result.evidence}
    missing = set(case.expected_evidence_source_types) - actual_source_types
    if missing:
        raise AssertionError(f"{case.id}: missing evidence source types {sorted(missing)}")
    return result


async def run_all(*, provider: str = "mock") -> list[CoachingAnalysisResult]:
    """Run all local evaluation fixtures."""
    results = []
    for case in load_cases():
        results.append(await run_case(case, provider=provider))
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Run structured analysis evaluation fixtures")
    parser.add_argument("--provider", default="mock", choices=["mock"])
    args = parser.parse_args()

    import asyncio

    results = asyncio.run(run_all(provider=args.provider))
    print(f"Passed {len(results)} evaluation fixture(s)")


if __name__ == "__main__":
    main()
