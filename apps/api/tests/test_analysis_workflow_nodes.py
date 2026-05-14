"""Tests for analysis workflow nodes."""

from app.workflows.analysis.nodes.generate_analysis import parse_provider_fallbacks
from app.workflows.analysis.nodes.retrieve_strategy import build_retrieval_query_from_state
from app.workflows.analysis.state import AnalysisWorkflowState, UploadSnapshot


def test_parse_provider_fallbacks_keeps_primary_first():
    attempts = parse_provider_fallbacks(
        "openai_compatible:qwen,minimax:abab",
        primary_provider="openai",
        primary_model="gpt-4o-mini",
    )

    assert [(attempt.provider, attempt.model) for attempt in attempts] == [
        ("openai", "gpt-4o-mini"),
        ("openai_compatible", "qwen"),
        ("minimax", "abab"),
    ]


def test_build_retrieval_query_prefers_summary_text():
    state = AnalysisWorkflowState(
        workflow_run_id="00000000-0000-0000-0000-000000000001",
        job_id="00000000-0000-0000-0000-000000000002",
        user_id="00000000-0000-0000-0000-000000000003",
        upload=UploadSnapshot(
            id="00000000-0000-0000-0000-000000000004",
            kind="match_summary",
            summary_text="Focus on lane pressure and rotations.",
        ),
    )

    assert build_retrieval_query_from_state(state) == "Focus on lane pressure and rotations."
