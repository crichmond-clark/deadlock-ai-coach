"""Tests for analysis workflow runner factory."""

import uuid

from app.workflows.analysis.runner import get_analysis_workflow_runner
from app.workflows.analysis.simple_runner import SimpleAnalysisWorkflowRunner, _duration_ms


def test_runner_factory_returns_simple_runner(monkeypatch):
    monkeypatch.setattr("app.workflows.analysis.runner.settings.workflow_engine", "simple")

    runner = get_analysis_workflow_runner()

    assert isinstance(runner, SimpleAnalysisWorkflowRunner)


def test_duration_ms_is_non_negative():
    assert _duration_ms(0) >= 0


def test_runner_protocol_method_exists():
    runner = SimpleAnalysisWorkflowRunner()

    assert callable(runner.run)
    assert uuid.uuid4()
