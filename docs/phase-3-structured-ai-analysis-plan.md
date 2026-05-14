# Phase 3 Structured AI Analysis Plan

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

Phase 2 proves the asynchronous analysis pipeline, Phase 2.5 produces replay parse artifacts, and Phase 2.6 enriches jobs with Deadlock API match/asset context. The product still returns deterministic fake coaching. Phase 3 replaces the fake coaching payload with validated, structured AI analysis that can use match summaries, match IDs, replay parse artifacts, and enriched Deadlock API context.

The result must be provider-flexible: OpenAI should work out of the box, but the app should be able to use OpenAI-compatible and open-source model endpoints such as Ollama Cloud, local/vLLM-compatible endpoints, Minimax-compatible endpoints, and similar providers without changing the rest of the app.

## 2. Goals & Non-Goals

- Goals:
  - Add a thin internal AI provider abstraction with OpenAI as the default provider.
  - Support configurable OpenAI-compatible chat endpoints for open-source/provider-compatible models.
  - Add a mock provider for deterministic tests and local development without API keys.
  - Define Pydantic schemas for structured coaching output and source evidence.
  - Generate match summaries and coaching insights from the best available input: match summary text, replay parse artifact, and/or enriched Deadlock API context.
  - Persist structured AI results in `analysis_results` with explicit schema/model/prompt/workflow metadata.
  - Add AI model run audit records for provider, model, prompt version, latency, token usage, validation status, and errors.
  - Preserve the Phase 2 fake analysis fallback when no AI provider is configured or when `ANALYSIS_MODE=fake`.
  - Render the structured coaching result cleanly in the existing analysis detail page.
  - Keep external provider response shapes out of the rest of the app.

- Non-Goals:
  - RAG retrieval and citations from strategy knowledge. That is Phase 4.
  - LangGraph or multi-step workflow orchestration. That is Phase 5.
  - Deep replay-derived intelligence beyond the normalized artifact already available. That is Phase 6.
  - Streaming token responses or SSE progress.
  - Storing raw prompts that may include user/private content unless explicitly enabled for local debugging.
  - Adding every provider SDK. The first implementation should support OpenAI and generic OpenAI-compatible HTTP APIs; provider-specific adapters can be added only when needed.

## 3. Proposed Architecture

Use Pydantic schemas as the app-owned structured output contract. The analysis worker will continue to own job execution, but instead of always calling `build_fake_analysis_payload`, it will call an AI analysis service when configured.

```txt
AnalysisJob
↓
Worker loads Upload + optional ReplayParseArtifact + optional EnrichedMatchContext
↓
Analysis input builder creates compact prompt context
↓
AI provider adapter generates JSON matching CoachingAnalysisResult schema
↓
Pydantic validates, normalizes, and rejects malformed output
↓
AIModelRun audit row records provider/model/prompt/workflow metadata
↓
AnalysisResult persists validated payload with result_kind="structured_ai_analysis"
↓
Frontend renders structured sections
```

Provider strategy:

- `AI_PROVIDER=openai` uses the OpenAI SDK/client and defaults to `gpt-4o-mini` or the configured `AI_MODEL`.
- `AI_PROVIDER=openai_compatible` uses an OpenAI-compatible `base_url`, `api_key`, and model name. This covers Ollama Cloud, OpenRouter, vLLM, LM Studio, and many hosted open-source gateways if they expose `/chat/completions`.
- `AI_PROVIDER=minimax` is planned as a provider-specific adapter only if Minimax is not usable through the OpenAI-compatible path.
- `AI_PROVIDER=mock` returns deterministic schema-valid output for tests.

Structured output strategy:

- The app prompt asks for strict JSON only.
- OpenAI/native structured-output support can be used by the OpenAI adapter when available.
- Generic/open-source adapters still return text, but the service extracts JSON and validates with Pydantic.
- Invalid JSON or schema errors produce controlled AI provider errors and mark the model run failed.

This keeps the rest of the app dependent only on app-owned models, not provider SDK response objects.

## 4. Component Breakdown

- AI configuration:
  - Environment-driven provider/model settings.
  - Safe defaults: `ANALYSIS_MODE=fake`, `AI_PROVIDER=openai`, no raw prompt persistence by default.

- Provider abstraction:
  - Internal protocol for chat completion with JSON output.
  - OpenAI adapter.
  - OpenAI-compatible adapter.
  - Mock adapter for tests.
  - Optional Minimax adapter after confirming API compatibility.

- Structured schemas:
  - Pydantic output models for coaching analysis.
  - Input context models for prompt construction.
  - Version constants for schema, prompt, and workflow.

- Prompt layer:
  - Versioned prompt templates stored in Python modules, not inline in the worker.
  - Prompt builder compresses enriched context and replay parse summaries into a bounded prompt context.

- Analysis service:
  - Builds input context.
  - Calls provider.
  - Validates output.
  - Persists model run metadata.
  - Returns an `AnalysisResult`-ready payload.

- Worker integration:
  - Maintains existing job state/progress/error behavior.
  - Uses AI analysis when enabled.
  - Falls back to fake analysis only when explicitly configured to do so.

- Frontend rendering:
  - Adds typed support for `structured_ai_analysis` payloads.
  - Renders summary, strengths, improvement areas, priorities, evidence, warnings, and model metadata.

## 5. Data Flow

### Flow A: Match Summary Input

```txt
User submits Upload(kind=match_summary, summary_text)
↓
Analysis job enqueued
↓
Worker builds AnalysisInputContext from summary_text
↓
AI provider generates CoachingAnalysisResult
↓
Result persisted and displayed
```

### Flow B: Match ID Input

```txt
User submits Upload(kind=match_id, match_id)
↓
Worker calls Phase 2.6 enrichment service
↓
EnrichedMatchContext(source_mode="api_only") added to prompt context
↓
AI provider generates API-aware coaching result
↓
Result persisted and displayed
```

### Flow C: Replay Input

```txt
User submits Upload(kind=replay)
↓
Worker optionally invokes replay parser
↓
ReplayParseArtifact persisted
↓
EnrichedMatchContext(source_mode="replay_only" or "replay_plus_api") built when possible
↓
AI provider generates coaching result grounded in available replay/API evidence
↓
Result persisted and displayed
```

## 6. Interface Contracts

### Environment Settings

- `ANALYSIS_MODE`: `fake | ai`, default `fake` for safe local operation.
- `AI_PROVIDER`: `openai | openai_compatible | minimax | mock`, default `openai`.
- `AI_MODEL`: default `gpt-4o-mini` for OpenAI; required for compatible providers.
- `AI_API_KEY`: generic key used by compatible providers.
- `AI_BASE_URL`: required for `openai_compatible` and provider-specific gateways.
- `AI_TIMEOUT_SECONDS`: float, default `45.0`.
- `AI_MAX_OUTPUT_TOKENS`: int, default `2500`.
- `AI_TEMPERATURE`: float, default `0.2`.
- `AI_STORE_RAW_PROMPTS`: bool, default `false`.
- Existing `OPENAI_API_KEY` remains supported.

### Pydantic Models

`AnalysisInputContext`

```python
class AnalysisInputContext(BaseModel):
    upload_kind: str
    match_summary_text: str | None = None
    replay_parse_summary: dict[str, Any] | None = None
    enriched_context: EnrichedMatchContext | None = None
    source_warnings: list[str] = []
```

`CoachingAnalysisResult`

```python
class CoachingAnalysisResult(BaseModel):
    schema_version: Literal["coaching-analysis-v1"]
    title: str
    executive_summary: str
    confidence: Literal["low", "medium", "high"]
    match_context: MatchContextSummary
    strengths: list[CoachingPoint]
    improvement_areas: list[CoachingPoint]
    key_moments: list[KeyMoment]
    build_advice: list[BuildAdvice]
    priority_focus: list[PracticeFocus]
    evidence: list[SourceEvidence]
    source_warnings: list[SourceWarning]
    model_metadata: ModelMetadata
```

`CoachingPoint`

```python
class CoachingPoint(BaseModel):
    title: str
    description: str
    impact: Literal["low", "medium", "high"]
    category: Literal["laning", "fighting", "objectives", "economy", "positioning", "build", "macro", "other"]
    evidence_refs: list[str] = []
```

`SourceEvidence`

```python
class SourceEvidence(BaseModel):
    ref_id: str
    source_type: Literal["user_summary", "replay_parse", "deadlock_api", "ai_inference"]
    description: str
    data_path: str | None = None
```

### Provider Protocol

```python
class ChatModelProvider(Protocol):
    async def generate_json(
        self,
        *,
        messages: list[ChatMessage],
        schema_name: str,
        schema_json: dict[str, Any],
        options: AIRequestOptions,
    ) -> AIProviderResponse: ...
```

### Analysis Service

```python
async def generate_structured_analysis(
    db: AsyncSession,
    *,
    job: AnalysisJob,
    upload: Upload,
    replay_artifact: ReplayParseArtifact | None,
    enriched_context: EnrichedMatchContext | None,
    replay_parse_summary: dict[str, Any] | None,
) -> CoachingAnalysisResult: ...
```

### Database Model: `ai_model_runs`

Columns:

- `id UUID primary key`
- `user_id UUID not null`
- `job_id UUID not null`
- `analysis_result_id UUID nullable`
- `provider str`
- `model_name str`
- `prompt_version str`
- `workflow_version str`
- `schema_version str`
- `status str`: `succeeded | failed`
- `latency_ms int nullable`
- `input_tokens int nullable`
- `output_tokens int nullable`
- `total_tokens int nullable`
- `request_metadata JSONB`
- `response_metadata JSONB`
- `error_message text nullable`
- `created_at/updated_at`

### AnalysisResult Contract

For structured AI results:

- `result_kind = "structured_ai_analysis"`
- `schema_version = "coaching-analysis-v1"`
- `payload = CoachingAnalysisResult.model_dump(mode="json")`

No new public endpoint is required in Phase 3; existing analysis job/result endpoints should return the structured payload.

## 7. File Changes

- Create:
  - `apps/api/app/ai/__init__.py` — AI package exports.
  - `apps/api/app/ai/config.py` — provider/model settings helpers.
  - `apps/api/app/ai/errors.py` — normalized AI exceptions.
  - `apps/api/app/ai/providers/base.py` — provider protocol and request/response models.
  - `apps/api/app/ai/providers/openai.py` — OpenAI adapter.
  - `apps/api/app/ai/providers/openai_compatible.py` — generic OpenAI-compatible adapter.
  - `apps/api/app/ai/providers/mock.py` — deterministic mock adapter.
  - `apps/api/app/ai/providers/registry.py` — provider factory.
  - `apps/api/app/schemas/ai_analysis.py` — structured coaching schemas.
  - `apps/api/app/services/ai_analysis/prompts.py` — versioned prompt templates.
  - `apps/api/app/services/ai_analysis/context.py` — input context builder.
  - `apps/api/app/services/ai_analysis/generator.py` — orchestration service for one AI call.
  - `apps/api/app/db/models/ai_model_run.py` — AI call audit table.
  - `apps/api/alembic/versions/0007_ai_model_runs.py` — migration.
  - `apps/api/tests/test_ai_provider_*.py` — provider/registry tests.
  - `apps/api/tests/test_ai_analysis_schemas.py` — schema validation tests.
  - `apps/api/tests/test_ai_analysis_generator.py` — service tests with mock provider.

- Modify:
  - `apps/api/app/core/config.py` — add AI provider settings.
  - `apps/api/app/db/models/__init__.py` — export `AIModelRun`.
  - `apps/api/app/db/models/user.py` — relationship to AI model runs.
  - `apps/api/app/db/models/analysis_job.py` — relationship to AI model runs.
  - `apps/api/app/db/models/analysis_result.py` — update docstring and optional relationship.
  - `apps/api/app/workers/analysis.py` — switch between fake and AI analysis.
  - `apps/api/pyproject.toml` — add `openai`, keep `httpx`; add optional provider deps only if necessary.
  - `.env.example` — AI provider settings.
  - `apps/web/src/lib/api.ts` — typed structured result payload.
  - `apps/web/src/app/analyses/[jobId]/page.tsx` — render structured AI sections.
  - `README.md` and `docs/testing-guide.md` — setup/testing docs.

- Delete:
  - None.

## 8. Implementation Phases

Branching rule:

- Branch: `feature/phase-3-structured-ai-analysis`
- Create this branch from `feature/deadlock-api-integration` if Phase 2.6 has not merged yet; otherwise create it from the target integration branch/main.
- Subphases should be commits on this branch, not extra branches.

### Phase 3A — Provider Foundation

- Branch: `feature/phase-3-structured-ai-analysis`
- Commits:
  - [ ] Add AI settings and `.env.example` entries.
  - [ ] Add provider protocol, request/response models, normalized errors.
  - [ ] Add mock provider and registry.
  - [ ] Add OpenAI and OpenAI-compatible provider adapters.
  - [ ] Add provider tests with mocked HTTP/client responses.
- Done when:
  - Mock/OpenAI-compatible providers can return JSON through the same interface.
  - Provider errors normalize into app exceptions.
  - Tests pass without real API keys.

### Phase 3B — Structured Schemas and Prompt Context

- Commits:
  - [ ] Add `CoachingAnalysisResult` and nested Pydantic schemas.
  - [ ] Add `AnalysisInputContext` builder for match summary, replay artifact, and enriched context.
  - [ ] Add versioned prompt templates and prompt tests.
- Done when:
  - Fixtures for match summary, api-only context, and replay-plus-api context produce bounded prompt contexts.
  - Schema validation rejects malformed AI output.

### Phase 3C — Persistence and Generator Service

- Commits:
  - [ ] Add `AIModelRun` model and migration.
  - [ ] Add `generate_structured_analysis` service.
  - [ ] Persist provider/model/prompt/schema/workflow metadata.
  - [ ] Add service tests using the mock provider.
- Done when:
  - A mock AI response creates a schema-valid payload and an `ai_model_runs` audit row.
  - Invalid provider output marks the model run failed and surfaces a safe error.

### Phase 3D — Worker Integration

- Commits:
  - [ ] Add `ANALYSIS_MODE=fake|ai` worker switch.
  - [ ] Replace fake payload path with structured AI path when enabled.
  - [ ] Preserve job progress, idempotency, and failure handling.
  - [ ] Add worker tests for fake mode, AI success, AI schema failure, and provider failure.
- Done when:
  - Existing fake analysis still works by default.
  - AI mode produces `result_kind="structured_ai_analysis"`.
  - Provider failures mark the job failed with safe error messages unless explicit fake fallback is enabled.

### Phase 3E — Frontend Structured Result Rendering

- Commits:
  - [ ] Add TypeScript interfaces for structured AI results.
  - [ ] Render executive summary, strengths, improvement areas, key moments, build advice, priorities, warnings, and model metadata.
  - [ ] Keep fallback rendering for fake analysis payloads.
- Done when:
  - Existing fake result pages still render.
  - Structured AI payload fixture renders without type errors.
  - `npm run type-check` and `npm run build` pass.

### Phase 3F — Documentation and Validation

- Commits:
  - [ ] Document AI provider configuration.
  - [ ] Add local mock-provider testing instructions.
  - [ ] Add optional live smoke instructions gated by real API keys.
- Done when:
  - `uv run pytest` passes.
  - `uv run ruff check .` passes.
  - `npm run type-check` and `npm run build` pass.

### Subagent Orchestration Strategy

After Phase 3A defines provider contracts and Phase 3B defines schemas, implementation can use subagents safely:

- Backend AI subagent: provider adapters, generator service, model run persistence.
- Frontend subagent: structured result renderer from agreed TypeScript fixtures.
- Testing/docs subagent: fixtures, mock-provider tests, documentation.

Do not run worker-integration changes in parallel with persistence changes until `AIModelRun` and generator interfaces are finalized.

## 9. Testing Strategy

- Unit tests:
  - Provider registry chooses correct provider from settings.
  - Mock provider returns deterministic schema-valid JSON.
  - OpenAI-compatible provider handles success, invalid JSON, timeout, 4xx/5xx.
  - Pydantic schemas accept valid fixtures and reject invalid fixtures.
  - Prompt context builder redacts/limits large raw payloads.
  - Generator persists succeeded/failed `AIModelRun` rows.

- Integration tests:
  - Worker in fake mode preserves Phase 2 behavior.
  - Worker in AI mode with mock provider produces `structured_ai_analysis` result.
  - Match ID job uses enriched context in prompt input.
  - Replay job uses replay artifact summary and enriched context when available.

- Edge cases:
  - Missing API key.
  - Provider timeout.
  - Provider returns prose instead of JSON.
  - Provider returns schema-invalid JSON.
  - Very large enriched context.
  - No replay/API context, only user summary.

- Validation before merge:
  - `cd apps/api && uv run pytest -v`
  - `cd apps/api && uv run ruff check .`
  - `cd apps/web && npm run type-check`
  - `cd apps/web && npm run build`
  - Optional live smoke with `AI_PROVIDER=openai` and real key, not required in CI.

## 10. Security Implications

- User-controlled data:
  - `summary_text`, filenames, match IDs, and external API payloads may enter prompts.
  - Prompt construction must treat all input as untrusted and avoid executing/rendering it.

- Secrets:
  - API keys must remain backend/worker environment variables.
  - Do not expose provider keys to the frontend.
  - Do not persist raw prompts by default; if enabled locally, clearly document the privacy risk.

- Prompt injection:
  - The model can be instructed by user summaries or external metadata. Prompts must explicitly separate untrusted match data from system/developer instructions.
  - The output must be validated by Pydantic before persistence.

- External API/provider risk:
  - Enforce request timeouts.
  - Do not include secrets in model metadata returned to the browser.
  - Log safe error categories, not full provider payloads, by default.

- Authorization:
  - No new public data access is introduced. Existing analysis job ownership checks continue to apply.

## 11. Risks & Tradeoffs

| Risk | Mitigation |
|---|---|
| Open-source models may not reliably follow JSON schemas | Use Pydantic validation, JSON extraction, retry once with a repair prompt only if safe, and surface controlled failures. |
| Provider abstraction becomes too broad | Implement OpenAI + OpenAI-compatible + mock first; defer provider-specific adapters until proven necessary. |
| AI costs or latency surprise users | Add timeouts, token limits, model metadata, and keep fake/mock mode for development. |
| Prompt context becomes too large | Build compact context summaries, omit raw arrays, and keep raw payloads in DB for future workflows. |
| Hallucinated coaching not grounded in evidence | Require `evidence_refs` and `SourceEvidence`; render warnings when evidence is weak. |
| Phase 3 conflicts with Phase 4 RAG result shape | Keep citations/evidence generic so Phase 4 can add RAG evidence without changing frontend structure. |

## 12. Open Questions

All questions must be resolved or accepted as risks before implementation starts.

1. Should `ANALYSIS_MODE` default to `fake` for local/dev and `ai` only when explicitly set? Recommended: yes.
2. Is OpenAI-compatible support sufficient for Minimax/Ollama Cloud/opencode-go in the first slice, or do you want a provider-specific adapter for any one of them immediately? Recommended: OpenAI-compatible first, provider-specific later only if needed.
3. Should raw prompts/responses ever be persisted for debugging? Recommended: no by default; optional local-only toggle.
4. Which default OpenAI model should be used? Recommended: `gpt-4o-mini` for cost/speed unless you prefer another.
5. Should provider failures hard-fail the job or fall back to fake analysis? Recommended: hard-fail in `ANALYSIS_MODE=ai`, fake only in `ANALYSIS_MODE=fake`.
