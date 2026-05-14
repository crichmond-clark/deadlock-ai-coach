"""Workflow node: retrieve strategy knowledge for AI analysis."""

from app.core.config import settings
from app.services.rag.context import retrieve_strategy_context
from app.workflows.analysis.state import AnalysisWorkflowState, WorkflowNodeResult


def build_retrieval_query_from_state(state: AnalysisWorkflowState) -> str:
    """Build a compact search query from workflow state."""
    if state.upload and state.upload.summary_text:
        return state.upload.summary_text[:1000]
    if state.upload and state.upload.match_id is not None:
        return f"Deadlock match {state.upload.match_id} coaching strategy macro objectives build positioning"
    if state.replay_parse_summary:
        match = state.replay_parse_summary.get("match") if isinstance(state.replay_parse_summary.get("match"), dict) else {}
        return f"Deadlock replay coaching strategy {match}"
    kind = state.upload.kind if state.upload else "match"
    return f"Deadlock {kind} coaching strategy positioning objectives build"


async def retrieve_strategy_if_enabled(db, state: AnalysisWorkflowState) -> WorkflowNodeResult:
    """Retrieve strategy context, degrading through RetrievalContext warnings."""
    if not settings.enable_rag_in_analysis:
        return WorkflowNodeResult(state=state, status="skipped", output_metadata={"reason": "disabled"})

    query = build_retrieval_query_from_state(state)
    state.retrieval_context = await retrieve_strategy_context(
        db,
        user_id=state.user_id,
        query=query,
        top_k=settings.rag_top_k,
    )
    await db.flush()
    return WorkflowNodeResult(
        state=state,
        status="succeeded",
        output_metadata={"result_count": len(state.retrieval_context.results)},
    )
