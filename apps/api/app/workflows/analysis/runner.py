"""Analysis workflow runner factory."""

import uuid
from typing import Protocol

from app.core.config import settings
from app.workflows.analysis.simple_runner import SimpleAnalysisWorkflowRunner
from app.workflows.analysis.state import AnalysisWorkflowState


class AnalysisWorkflowRunner(Protocol):
    """App-owned analysis workflow runner interface."""

    async def run(self, *, job_id: uuid.UUID) -> AnalysisWorkflowState:
        """Run the analysis workflow."""
        ...


def get_analysis_workflow_runner() -> AnalysisWorkflowRunner:
    """Return the configured analysis workflow runner."""
    if settings.workflow_engine == "simple":
        return SimpleAnalysisWorkflowRunner()
    # Keep LangGraph behind this interface; implement only after simple runner proves insufficient.
    return SimpleAnalysisWorkflowRunner()


async def run_analysis_workflow(job_id: uuid.UUID) -> AnalysisWorkflowState:
    """Run the configured analysis workflow for one job."""
    return await get_analysis_workflow_runner().run(job_id=job_id)
