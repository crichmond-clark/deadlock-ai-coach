# Phase 5 AI Workflow Orchestration Plan

## Table of Contents

- [1. Problem Statement](#1-problem-statement)
- [2. Goals & Non-Goals](#2-goals-non-goals)
- [3. Proposed Architecture](#3-proposed-architecture)
- [4. Component Breakdown](#4-component-breakdown)
- [5. Data Flow](#5-data-flow)
- [6. Interface Contracts](#6-interface-contracts)
- [7. File Changes](#7-file-changes)
- [8. Implementation Phases](#8-implementation-phases)
- [9. Testing Strategy](#9-testing-strategy)
- [10. Security Implications](#10-security-implications)
- [11. Risks & Tradeoffs](#11-risks-tradeoffs)
- [12. Open Questions](#12-open-questions)

## 1. Problem Statement

After Phase 3, analysis can make a single structured AI call. After Phase 4, strategy knowledge can be retrieved. As the product grows, the worker should not become a long linear script that mixes loading, parsing, enrichment, retrieval, generation, validation, fallback, and persistence.

Phase 5 introduces a typed workflow orchestration layer so analysis is observable, repeatable, testable, and resilient. It should coordinate Phase 2.5 replay parsing, Phase 2.6 metadata enrichment, Phase 4 retrieval, and Phase 3 structured coaching through explicit workflow nodes and persisted workflow step telemetry.

## 2. Goals & Non-Goals

- Goals:
  - Introduce an internal analysis workflow runner with typed state and explicit nodes.
  - Use LangGraph where it adds value, but hide it behind an app-owned interface.
  - Replace worker inline analysis logic with a workflow call.
  - Persist workflow run and step status for observability/debugging.
  - Add retry/fallback behavior for non-fatal steps such as Deadlock API enrichment and RAG retrieval.
  - Add provider fallback chain support for AI generation, compatible with Phase 3's provider abstraction.
  - Add basic evaluation fixtures and regression checks for structured coaching output.
  - Keep all existing API contracts stable.

- Non-Goals:
  - Autonomous agents or tool-use loops.
  - Streaming workflows/SSE progress.
  - Full Ragas/DeepEval adoption if lightweight fixtures are enough for the first slice.
  - Phase 6 deep replay intelligence.
  - A generic workflow engine for unrelated app features.
  - Complex distributed tracing/observability infrastructure.

## 3. Proposed Architecture

Create an app-owned workflow interface and implementation. The worker calls `run_analysis_workflow(job_id)`. The workflow loads the job, executes typed nodes, persists step telemetry, and returns a final `AnalysisResult`.

```txt
Arq worker
↓
run_analysis_workflow(job_id)
↓
WorkflowRun row created
↓
Nodes execute:
  load_input
  parse_replay_if_needed
  enrich_match_context
  retrieve_strategy_context
  generate_structured_analysis
  validate_and_persist_result
↓
WorkflowStep rows record status/timing/errors
↓
AnalysisJob status/result updated
```

LangGraph strategy:

- Phase 5 should define app-owned `AnalysisWorkflowRunner` and `AnalysisWorkflowState` first.
- LangGraph can be used internally for node sequencing and conditional edges.
- The rest of the code should not import LangGraph directly.
- If LangGraph adds unnecessary complexity during implementation, the fallback is a simple in-process typed runner with the same interface. The plan accepts this tradeoff as long as state, steps, and tests remain explicit.

Provider fallback strategy:

- Phase 3 provider abstraction remains the source of truth.
- Add `AI_PROVIDER_FALLBACKS`, e.g. `openai:gpt-4o-mini,openai_compatible:qwen2.5-coder,minimax:...`.
- The generation node tries configured providers in order only for transient/provider errors.
- Schema validation failure can retry once with the same provider using a repair instruction, then optionally fallback.

## 4. Component Breakdown

- Workflow state:
  - Pydantic model carrying job, upload, replay artifact, enriched context, retrieval context, analysis result, warnings, and errors.

- Workflow runner:
  - App-owned interface for starting/resuming workflows.
  - Handles node sequencing, progress updates, and final result.

- Workflow nodes:
  - `load_input`: load job/upload and enforce ownership/idempotency.
  - `parse_replay_if_needed`: call replay parser for replay uploads.
  - `enrich_match_context`: call Phase 2.6 enrichment.
  - `retrieve_strategy_context`: call Phase 4 retrieval.
  - `generate_structured_analysis`: call Phase 3 AI analysis with fallback chain.
  - `validate_and_persist_result`: final schema validation and persistence.

- Persistence:
  - `workflow_runs` table for one execution attempt.
  - `workflow_steps` table for per-node status, timing, warnings, and error categories.

- Evaluations:
  - Small fixture dataset with expected structural assertions.
  - Deterministic mock provider output checks.
  - Optional live eval command gated by provider env vars.

- Worker integration:
  - Worker becomes a thin job runner.
  - Existing progress/status semantics remain compatible.

## 5. Data Flow

### Flow A: Successful Replay Analysis

```txt
Worker receives job_id
↓
Workflow creates WorkflowRun(status="running")
↓
load_input loads AnalysisJob + Upload
↓
parse_replay_if_needed creates ReplayParseArtifact
↓
enrich_match_context combines replay + API metadata
↓
retrieve_strategy_context gets top-k strategy snippets
↓
generate_structured_analysis creates CoachingAnalysisResult
↓
validate_and_persist_result creates AnalysisResult
↓
WorkflowRun and AnalysisJob marked succeeded
```

### Flow B: Match ID Analysis with External API Failure

```txt
load_input finds Upload(kind=match_id)
↓
enrich_match_context fails because Deadlock API is unavailable
↓
workflow marks enrichment step warning/failure as non-fatal based on policy
↓
retrieve_strategy_context may still run from available query terms
↓
generate_structured_analysis runs with source warnings or fails if no usable context
```

### Flow C: AI Provider Fallback

```txt
generate_structured_analysis tries primary provider/model
↓
provider timeout or 5xx
↓
AIModelRun row records failed attempt
↓
workflow tries next configured provider/model
↓
second provider succeeds
↓
final result includes model metadata and fallback warning
```

## 6. Interface Contracts

### Environment Settings

- `WORKFLOW_ENGINE`: `simple | langgraph`, default `simple` until LangGraph is proven worthwhile.
- `WORKFLOW_VERSION`: default `analysis-workflow-v1`.
- `WORKFLOW_STEP_TIMEOUT_SECONDS`: default `120`.
- `AI_PROVIDER_FALLBACKS`: comma-separated provider/model entries, optional.
- `AI_SCHEMA_REPAIR_RETRIES`: int, default `1`.
- `ENABLE_RAG_IN_ANALYSIS`: bool, default `true` once Phase 4 is merged.
- `ENABLE_DEADLOCK_API_ENRICHMENT`: bool, default `true`.

### Pydantic Models

`AnalysisWorkflowState`

```python
class AnalysisWorkflowState(BaseModel):
    workflow_run_id: UUID
    job_id: UUID
    user_id: UUID
    upload: UploadSnapshot | None = None
    replay_artifact_id: UUID | None = None
    replay_parse_summary: dict[str, Any] | None = None
    enriched_context: EnrichedMatchContext | None = None
    retrieval_context: RetrievalContext | None = None
    ai_result: CoachingAnalysisResult | None = None
    warnings: list[WorkflowWarning] = []
    fatal_error: WorkflowError | None = None
```

`WorkflowWarning`

```python
class WorkflowWarning(BaseModel):
    code: str
    message: str
    step_name: str
    recoverable: bool = True
```

`WorkflowNodeResult`

```python
class WorkflowNodeResult(BaseModel):
    state: AnalysisWorkflowState
    status: Literal["succeeded", "failed", "skipped"]
    warnings: list[WorkflowWarning] = []
```

### Workflow Runner

```python
class AnalysisWorkflowRunner(Protocol):
    async def run(self, *, job_id: UUID) -> AnalysisWorkflowState: ...
```

```python
async def run_analysis_workflow(job_id: UUID) -> None: ...
```

### Database Models

`WorkflowRun`

- `id UUID primary key`
- `user_id UUID not null`
- `job_id UUID not null`
- `workflow_name str` — `analysis`.
- `workflow_version str`
- `engine str` — `simple | langgraph`.
- `status str` — `running | succeeded | failed`.
- `started_at datetime`
- `completed_at datetime nullable`
- `duration_ms int nullable`
- `state_snapshot JSONB nullable` — compact, safe snapshot only.
- `error_message text nullable`
- timestamps.

`WorkflowStep`

- `id UUID primary key`
- `workflow_run_id UUID not null`
- `step_name str`
- `status str` — `pending | running | succeeded | failed | skipped`.
- `started_at datetime`
- `completed_at datetime nullable`
- `duration_ms int nullable`
- `input_metadata JSONB`
- `output_metadata JSONB`
- `warnings JSONB`
- `error_message text nullable`
- timestamps.

### Worker Contract

Existing Arq task remains:

```python
async def process_analysis_job(ctx: dict, job_id: str) -> None:
    await run_analysis_workflow(uuid.UUID(job_id))
```

The worker must preserve:

- idempotent no-op for already succeeded jobs with a result.
- `AnalysisJobStatus.RUNNING/SUCCEEDED/FAILED` transitions.
- progress updates.
- `mark_job_failed` behavior.

### Evaluation Contracts

`EvaluationCase`

```python
class EvaluationCase(BaseModel):
    id: str
    name: str
    input_fixture: dict[str, Any]
    expected_schema_version: str
    required_sections: list[str]
    expected_evidence_source_types: list[str]
```

Evaluation command:

```bash
uv run python -m app.evals.run_analysis_fixtures --provider mock
```

## 7. File Changes

- Create:
  - `apps/api/app/workflows/__init__.py`
  - `apps/api/app/workflows/analysis/__init__.py`
  - `apps/api/app/workflows/analysis/state.py` — workflow state schemas.
  - `apps/api/app/workflows/analysis/runner.py` — app-owned runner interface/factory.
  - `apps/api/app/workflows/analysis/simple_runner.py` — first implementation.
  - `apps/api/app/workflows/analysis/langgraph_runner.py` — optional internal implementation if enabled.
  - `apps/api/app/workflows/analysis/nodes/load_input.py`
  - `apps/api/app/workflows/analysis/nodes/parse_replay.py`
  - `apps/api/app/workflows/analysis/nodes/enrich_match.py`
  - `apps/api/app/workflows/analysis/nodes/retrieve_strategy.py`
  - `apps/api/app/workflows/analysis/nodes/generate_analysis.py`
  - `apps/api/app/workflows/analysis/nodes/persist_result.py`
  - `apps/api/app/db/models/workflow_run.py`
  - `apps/api/app/db/models/workflow_step.py`
  - `apps/api/alembic/versions/0009_workflow_runs.py`
  - `apps/api/app/evals/__init__.py`
  - `apps/api/app/evals/run_analysis_fixtures.py`
  - `apps/api/tests/fixtures/evals/*.json`
  - `apps/api/tests/test_analysis_workflow_state.py`
  - `apps/api/tests/test_analysis_workflow_runner.py`
  - `apps/api/tests/test_analysis_workflow_nodes.py`
  - `apps/api/tests/test_analysis_evals.py`

- Modify:
  - `apps/api/app/core/config.py` — workflow/fallback/eval settings.
  - `apps/api/app/db/models/__init__.py` — export workflow models.
  - `apps/api/app/db/models/user.py`, `analysis_job.py` — relationships.
  - `apps/api/app/workers/analysis.py` — delegate to workflow runner.
  - Phase 3 generator service — accept retrieval context and fallback chain.
  - Phase 4 retrieval service — expose analysis-friendly query helper.
  - `apps/api/pyproject.toml` — add `langgraph` only if using the LangGraph runner in the first implementation.
  - `docs/testing-guide.md` — workflow/eval commands.

- Delete:
  - No files. Existing worker logic should be moved into nodes rather than duplicated; remove dead inline code only after tests prove parity.

## 8. Implementation Phases

Branching rule:

- Branch: `feature/phase-5-ai-workflow-orchestration`
- This branch should start only after Phase 3 is merged. It should start after Phase 4 is merged if RAG retrieval is included in the first workflow implementation.
- If Phase 4 is not merged, implement the retrieval node as a no-op with a documented follow-up, but do not pretend RAG is complete.

### Phase 5A — Workflow Persistence and State Contracts

- Branch: `feature/phase-5-ai-workflow-orchestration`
- Commits:
  - [ ] Add workflow settings.
  - [ ] Add `WorkflowRun` and `WorkflowStep` models and migration.
  - [ ] Add workflow state/warning/error schemas.
  - [ ] Add state serialization tests.
- Done when:
  - Migration applies cleanly.
  - Workflow state can be serialized without leaking raw prompts/secrets.

### Phase 5B — Simple Runner and Step Telemetry

- Commits:
  - [ ] Add app-owned runner protocol/factory.
  - [ ] Add simple sequential runner.
  - [ ] Add helpers for starting/completing/failing workflow steps.
  - [ ] Add tests for successful, failed, and skipped steps.
- Done when:
  - A test workflow records run/step rows with durations and statuses.

### Phase 5C — Analysis Nodes

- Commits:
  - [ ] Extract worker input loading into `load_input` node.
  - [ ] Extract replay parsing into `parse_replay_if_needed` node.
  - [ ] Extract Deadlock API enrichment into `enrich_match_context` node.
  - [ ] Add retrieval node using Phase 4 service or no-op if Phase 4 is unavailable.
  - [ ] Add generation and persistence nodes using Phase 3 service.
  - [ ] Add node-level tests with mocks.
- Done when:
  - Nodes can be tested independently.
  - Non-fatal nodes emit warnings instead of failing the workflow when configured.

### Phase 5D — Worker Replacement

- Commits:
  - [ ] Update Arq worker task to call `run_analysis_workflow`.
  - [ ] Preserve idempotency and job status/progress behavior.
  - [ ] Add integration tests comparing worker success/failure behavior to previous implementation.
- Done when:
  - Analysis jobs still progress to succeeded/failed correctly.
  - Workflow telemetry is created for each job attempt.

### Phase 5E — Provider Fallback and Schema Repair

- Commits:
  - [ ] Add `AI_PROVIDER_FALLBACKS` parsing.
  - [ ] Add transient provider fallback logic to generation node.
  - [ ] Add one schema-repair retry for invalid JSON/schema output.
  - [ ] Add tests for primary failure/secondary success and repair success/failure.
- Done when:
  - Provider failures are recorded in `AIModelRun` and `WorkflowStep` rows.
  - Successful fallback still produces one final `AnalysisResult`.

### Phase 5F — Evaluation Fixtures and Regression Command

- Commits:
  - [ ] Add evaluation fixture schema.
  - [ ] Add small fixture set for match summary, match-id/api-only, and replay-plus-api cases.
  - [ ] Add `app.evals.run_analysis_fixtures` command with mock provider.
  - [ ] Add optional live eval mode gated by env vars.
- Done when:
  - Mock eval command passes deterministically in CI/local.
  - Live eval instructions are documented but not mandatory.

### Phase 5G — Optional LangGraph Internal Runner

- Commits:
  - [ ] Add `langgraph` dependency only if the simple runner shows clear limitations.
  - [ ] Implement `LangGraphAnalysisRunner` behind the same runner interface.
  - [ ] Add parity tests against the simple runner for core flows.
- Done when:
  - `WORKFLOW_ENGINE=langgraph` produces the same persisted result and telemetry as `WORKFLOW_ENGINE=simple` for fixture flows.

### Subagent Orchestration Strategy

Phase 5 should not be implemented in parallel with Phase 3/4 because it depends on their contracts. Once Phase 3 and Phase 4 are merged, subagents can work in parallel inside Phase 5 after Phase 5A defines state contracts:

- Workflow persistence subagent: models, migrations, telemetry helpers.
- Node extraction subagent: convert existing worker logic into nodes.
- Evaluation subagent: fixtures and regression command.
- Optional LangGraph subagent: internal runner parity after simple runner is stable.

Do not start the LangGraph runner before the simple runner and node tests are passing.

## 9. Testing Strategy

- Unit tests:
  - Workflow state serialization.
  - Step start/succeed/fail helpers.
  - Each workflow node with mocked dependencies.
  - Provider fallback parsing and execution.
  - Schema-repair retry behavior.

- Integration tests:
  - Worker calls workflow runner and creates telemetry.
  - Successful match summary analysis persists `AnalysisResult`.
  - Match ID analysis records enrichment step and source warnings.
  - Replay analysis records parser and enrichment steps.
  - Failed provider marks job/workflow failed with safe error.

- Evaluation tests:
  - Mock provider fixtures produce schema-valid results.
  - Required sections/evidence source types are present.
  - Optional live eval command can run locally with real provider keys.

- Edge cases:
  - Already-succeeded job is idempotent.
  - Replay parser unavailable.
  - Deadlock API unavailable.
  - RAG unavailable/no results.
  - Primary AI provider timeout and fallback success.
  - All providers fail.

- Validation before merge:
  - `cd apps/api && uv run pytest -v`
  - `cd apps/api && uv run ruff check .`
  - `cd apps/api && uv run alembic upgrade head`
  - `cd apps/api && uv run python -m app.evals.run_analysis_fixtures --provider mock`
  - `cd apps/web && npm run type-check`
  - `cd apps/web && npm run build`

## 10. Security Implications

- Secrets:
  - Workflow state snapshots must not include API keys or full raw provider responses.
  - Provider fallback config must not be returned to frontend.

- User data:
  - Workflow telemetry should store compact metadata, not raw user summaries or full prompts by default.

- Prompt injection:
  - Orchestration increases the number of context sources. Each node must preserve source boundaries and label untrusted source text.

- Authorization:
  - Workflow runs are tied to `user_id` and `job_id`. Any future endpoint exposing workflow telemetry must enforce job ownership.

- Reliability:
  - Retry/fallback logic must avoid duplicate `AnalysisResult` rows. Existing unique constraint on job result helps; runner must remain idempotent.

## 11. Risks & Tradeoffs

| Risk | Mitigation |
|---|---|
| LangGraph adds complexity too early | Build app-owned runner interface and simple runner first; add LangGraph only behind the same interface. |
| Workflow telemetry stores too much sensitive data | Store compact metadata and warnings only; no raw prompts unless local debug explicitly enables it. |
| Node extraction breaks existing worker behavior | Add parity tests and preserve job status/progress semantics. |
| Provider fallback hides real quality issues | Record all failed attempts and fallback warnings in model run/workflow metadata. |
| Evaluation scope becomes a research project | Start with structural fixture checks; defer Ragas/DeepEval depth until real data exists. |
| Phase 5 blocked by Phase 4 | Allow retrieval node no-op only if explicitly accepted, but prefer waiting for Phase 4 merge. |

## 12. Open Questions

All questions must be resolved or accepted as risks before implementation starts.

1. Should Phase 5 wait for both Phase 3 and Phase 4 to merge? Recommended: yes.
2. Should LangGraph be mandatory in the first implementation? Recommended: no; simple runner first, LangGraph optional behind interface.
3. Should workflow telemetry be exposed in an API/UI now? Recommended: no, DB-only first.
4. What fallback provider chain should be used for your open-source preference? Recommended: configure after Phase 3 proves OpenAI-compatible providers.
5. Should schema repair retry be enabled for all providers? Recommended: one retry for invalid JSON/schema, then fail/fallback.
