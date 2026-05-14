"""Tests for lightweight analysis evaluation fixtures."""

import pytest

from app.evals.run_analysis_fixtures import load_cases, run_all


def test_eval_fixtures_load():
    cases = load_cases()

    assert cases
    assert cases[0].id == "match-summary-basic"


@pytest.mark.asyncio
async def test_mock_eval_fixtures_pass():
    results = await run_all(provider="mock")

    assert len(results) == len(load_cases())
    assert all(result.schema_version == "coaching-analysis-v1" for result in results)
