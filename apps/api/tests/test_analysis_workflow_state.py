"""Tests for analysis workflow state contracts."""

import uuid

from app.workflows.analysis.state import AnalysisWorkflowState, UploadSnapshot, WorkflowWarning


def test_workflow_state_safe_snapshot_redacts_summary_text():
    state = AnalysisWorkflowState(
        workflow_run_id=uuid.uuid4(),
        job_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        upload=UploadSnapshot(
            id=uuid.uuid4(),
            kind="match_summary",
            summary_text="private match notes",
        ),
        warnings=[WorkflowWarning(code="test", message="warning", step_name="load_input")],
    )

    snapshot = state.safe_snapshot()

    assert snapshot["upload"]["summary_text"] == "[redacted]"
    assert snapshot["warnings"][0]["code"] == "test"
