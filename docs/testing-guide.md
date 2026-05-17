# Full Testing Guide — Phases 1 through 6

## Table of Contents

- [Purpose](#purpose)
- [Phase Map](#phase-map)
- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Quick Validation Matrix](#quick-validation-matrix)
- [Backend Test Commands](#backend-test-commands)
- [Frontend Test Commands](#frontend-test-commands)
- [Replay Parser Test Commands](#replay-parser-test-commands)
- [Phase-by-Phase Testing](#phase-by-phase-testing)
  - [Phase 1 — Foundation](#phase-1--foundation)
  - [Phase 2 — Async Analysis Pipeline](#phase-2--async-analysis-pipeline)
  - [Phase 2.5 — Clarity Replay Parser Spike](#phase-25--clarity-replay-parser-spike)
  - [Phase 2.6 — Deadlock API Integration](#phase-26--deadlock-api-integration)
  - [Phase 3 — Structured AI Analysis](#phase-3--structured-ai-analysis)
  - [Phase 4 — RAG System](#phase-4--rag-system)
  - [Phase 5 — AI Workflow Orchestration](#phase-5--ai-workflow-orchestration)
  - [Phase 6 — Replay Intelligence Validation Gate](#phase-6--replay-intelligence-validation-gate)
- [Manual End-to-End Smoke Tests](#manual-end-to-end-smoke-tests)
- [External Service Smoke Tests](#external-service-smoke-tests)
- [Before Opening a PR](#before-opening-a-pr)
- [Common Issues](#common-issues)

## Purpose

This document is the full local testing guide for the Deadlock AI Platform from Phase 1 through the Phase 6 validation gate. It covers:

- required local services,
- exact test commands,
- which tests map to each phase,
- manual smoke checks for API, worker, frontend, replay parser, AI, RAG, and workflow orchestration,
- known limitations where tests require Docker, real API keys, or real local replay files.

Phase 6 is currently a validation gate, not a full Replay Intelligence implementation. It should not be considered complete until real Deadlock `.dem` parsing produces verified replay-derived data beyond file metadata.

## Phase Map

| Phase | Scope | Status in current code |
|---|---|---|
| Phase 1 | Foundation: monorepo, FastAPI shell, DB, auth boundary, upload metadata, Next.js shell | Implemented |
| Phase 2 | Async pipeline: Arq worker, analysis jobs, fake persisted result, polling UI | Implemented |
| Phase 2.5 | Clarity replay parser spike: Java CLI + Python subprocess wrapper + persisted artifacts | Implemented as parser skeleton/spike |
| Phase 2.6 | Deadlock API integration: clients, assets, metadata cache, enrichment, match ID path | Implemented |
| Phase 3 | Structured AI analysis: provider abstraction, schemas, prompts, audit model, frontend rendering | Implemented |
| Phase 4 | RAG: knowledge ingestion, embeddings, pgvector search, strategy search UI, AI context injection | Implemented |
| Phase 5 | Workflow orchestration: typed workflow state, workflow telemetry, simple runner, eval fixtures | Implemented |
| Phase 6 | Replay Intelligence | Validation gate only; real Clarity extraction still required |

## Prerequisites

Install these locally:

- Docker + Docker Compose
- Python 3.12+
- `uv`
- Node.js 20+
- npm
- Java 17+
- Gradle

Optional for live smoke tests:

- OpenAI or OpenAI-compatible API key
- Deadlock API key for higher external API limits
- Real local Deadlock `.dem` replay file for Phase 6 validation

## Environment Setup

From the repository root:

```bash
cp .env.example .env.local
```

Start stateful services:

```bash
docker compose -f infra/docker-compose.yml up -d
docker compose -f infra/docker-compose.yml ps
```

Expected local services:

| Service | URL / Port |
|---|---|
| PostgreSQL | `localhost:5433` |
| Redis | `localhost:6379` |
| FastAPI | `http://localhost:8000` |
| Next.js | `http://localhost:3000` |

Install backend dependencies and migrate:

```bash
cd apps/api
uv sync --extra dev
uv run alembic upgrade head
```

Install frontend dependencies:

```bash
cd apps/web
npm install
```

Build replay parser distribution when testing parser integration:

```bash
cd apps/replay-parser
gradle test
gradle installDist
```

For local parser worker integration, set:

```env
REPLAY_PARSER_COMMAND=/absolute/path/to/apps/replay-parser/build/install/replay-parser/bin/replay-parser
LOCAL_REPLAY_SAMPLE_PATH=/absolute/path/to/match.dem
ALLOW_LOCAL_REPLAY_PATHS=true
```

Do not commit `.dem` files or generated parser artifacts.

## Quick Validation Matrix

Run these before handing off a broad feature branch:

```bash
# Backend component tests and lint
cd apps/api
uv run ruff check .
uv run pytest tests/test_replay_parser_service.py \
  tests/test_deadlock_api_client.py \
  tests/test_deadlock_api_assets.py \
  tests/test_deadlock_api_metadata.py \
  tests/test_deadlock_api_enrichment.py \
  tests/test_ai_provider_foundation.py \
  tests/test_ai_analysis_schemas.py \
  tests/test_ai_analysis_generator.py \
  tests/test_rag_chunking.py \
  tests/test_embedding_providers.py \
  tests/test_rag_search.py \
  tests/test_analysis_workflow_state.py \
  tests/test_analysis_workflow_nodes.py \
  tests/test_analysis_workflow_runner.py \
  tests/test_analysis_evals.py \
  -q

# Workflow eval fixtures
uv run python -m app.evals.run_analysis_fixtures --provider mock

# Frontend
cd ../web
npm run type-check
npm run build

# Replay parser
cd ../replay-parser
gradle test
```

Run the full backend suite when PostgreSQL/Redis are available:

```bash
cd apps/api
uv run pytest -v
```

## Backend Test Commands

### Lint

```bash
cd apps/api
uv run ruff check .
```

### Component tests that do not need live external APIs

```bash
cd apps/api
uv run pytest tests/test_replay_parser_service.py \
  tests/test_deadlock_api_client.py \
  tests/test_deadlock_api_assets.py \
  tests/test_deadlock_api_metadata.py \
  tests/test_deadlock_api_enrichment.py \
  tests/test_ai_provider_foundation.py \
  tests/test_ai_analysis_schemas.py \
  tests/test_ai_analysis_generator.py \
  tests/test_rag_chunking.py \
  tests/test_embedding_providers.py \
  tests/test_rag_search.py \
  tests/test_analysis_workflow_state.py \
  tests/test_analysis_workflow_nodes.py \
  tests/test_analysis_workflow_runner.py \
  tests/test_analysis_evals.py \
  -v
```

### Full backend suite

Requires PostgreSQL on `localhost:5433` and migrations applied:

```bash
cd apps/api
uv run alembic upgrade head
uv run pytest -v
```

Endpoint tests such as `test_health.py` and `test_analysis_jobs.py` exercise the app with real local database access.

## Frontend Test Commands

```bash
cd apps/web
npm run type-check
npm run build
```

Optional lint:

```bash
cd apps/web
npm run lint
```

Manual frontend smoke:

```bash
cd apps/web
npm run dev
```

Open `http://localhost:3000`.

## Replay Parser Test Commands

```bash
cd apps/replay-parser
gradle test
gradle installDist
```

Run the parser against a local file:

```bash
build/install/replay-parser/bin/replay-parser \
  --input /absolute/path/to/match.dem \
  --pretty \
  --max-events 500
```

Run Phase 6 bounded debug discovery:

```bash
build/install/replay-parser/bin/replay-parser \
  --input "$LOCAL_REPLAY_SAMPLE_PATH" \
  --pretty \
  --max-events 500 \
  --debug-discovery
```

## Phase-by-Phase Testing

### Phase 1 — Foundation

Phase 1 proves the repository, local infrastructure, FastAPI shell, DB migrations, auth boundary, upload metadata, and basic frontend shell.

Automated checks:

```bash
cd apps/api
uv run pytest tests/test_health.py tests/test_analysis_jobs.py -v
```

Manual checks:

```bash
# Start infra and migrate
cd /path/to/deadlock-ai-coach
docker compose -f infra/docker-compose.yml up -d
cd apps/api
uv run alembic upgrade head
uv run fastapi dev --port 8000
```

In another terminal:

```bash
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/ready
curl http://localhost:8000/api/v1/me \
  -H "X-Dev-User-Id: dev-user-00000000-0000-0000-0000-000000000001"
```

Expected results:

- `/health` returns API status.
- `/ready` confirms database/Redis readiness when services are up.
- `/me` resolves or creates a local dev user through the auth boundary.
- Frontend starts at `http://localhost:3000` and can reach the API.

Frontend foundation checks:

```bash
cd apps/web
npm run type-check
npm run build
```

### Phase 2 — Async Analysis Pipeline

Phase 2 proves uploads can create analysis jobs, jobs are queued through Redis/Arq, the worker persists a deterministic result, and the frontend polls/displays it.

Automated checks:

```bash
cd apps/api
uv run pytest tests/test_analysis_jobs.py -v
```

Manual worker smoke:

Terminal 1:

```bash
cd apps/api
uv run fastapi dev --port 8000
```

Terminal 2:

```bash
cd apps/api
uv run arq app.workers.worker.WorkerSettings
```

Create an upload:

```bash
curl -X POST http://localhost:8000/api/v1/uploads \
  -H "X-Dev-User-Id: dev-user-00000000-0000-0000-0000-000000000001" \
  -H "Content-Type: application/json" \
  -d '{"kind":"match_summary","summary_text":"Won lane, lost late fights around mid boss."}'
```

Create a job using the returned upload ID:

```bash
curl -X POST http://localhost:8000/api/v1/analysis-jobs \
  -H "X-Dev-User-Id: dev-user-00000000-0000-0000-0000-000000000001" \
  -H "Content-Type: application/json" \
  -d '{"upload_id":"<upload-uuid>"}'
```

Poll the job:

```bash
curl http://localhost:8000/api/v1/analysis-jobs/<job-uuid> \
  -H "X-Dev-User-Id: dev-user-00000000-0000-0000-0000-000000000001"
```

Expected results:

- Job transitions from `queued` to `running` to `succeeded`.
- Progress reaches `100`.
- One `analysis_results` row exists for the job.
- `/analyses/<job-id>` renders the result.

### Phase 2.5 — Clarity Replay Parser Spike

Phase 2.5 proves the Python API can call a Java CLI parser and persist parser artifacts. The Java parser currently emits schema-valid metadata/placeholder output unless real Clarity extraction is added.

Automated checks:

```bash
cd apps/replay-parser
gradle test

cd ../api
uv run pytest tests/test_replay_parser_service.py -v
```

Manual Java CLI check:

```bash
cd apps/replay-parser
gradle installDist
build/install/replay-parser/bin/replay-parser \
  --input /absolute/path/to/local-match.dem \
  --pretty \
  --max-events 500
```

Manual Python wrapper check:

```bash
cd apps/api
REPLAY_PARSER_COMMAND=/absolute/path/to/apps/replay-parser/build/install/replay-parser/bin/replay-parser \
ALLOW_LOCAL_REPLAY_PATHS=true \
LOCAL_REPLAY_SAMPLE_PATH=/absolute/path/to/local-match.dem \
uv run pytest tests/test_replay_parser_service.py -v
```

Expected results:

- Parser exits with code `0` for readable input.
- Output validates as `deadlock-replay-parse-v1` JSON.
- Python wrapper handles success, missing config, non-zero exit, invalid JSON, and timeout.
- Parser artifacts can be fetched through the replay artifact endpoint after a replay analysis job succeeds.

### Phase 2.6 — Deadlock API Integration

Phase 2.6 adds app-owned clients around `deadlock-api.com`, asset catalog caching/resolution, match metadata caching, enrichment, and match ID upload support.

Automated checks:

```bash
cd apps/api
uv run pytest tests/test_deadlock_api_client.py \
  tests/test_deadlock_api_assets.py \
  tests/test_deadlock_api_metadata.py \
  tests/test_deadlock_api_enrichment.py \
  -v
```

Optional live checks against external services:

```bash
curl "https://api.deadlock-api.com/v1/matches/44009651/metadata?disable_steam=true"
curl "https://assets.deadlock-api.com/v2/heroes/63" | jq '.name'
curl "https://assets.deadlock-api.com/v2/items/1233782561" | jq '.name'
```

Expected results:

- HTTP clients normalize 4xx/5xx/rate-limit/timeout errors.
- Asset catalog sync and resolution work with mocked API payloads.
- Match metadata fetch/cache honors stale vs fresh cache behavior.
- Enrichment degrades non-fatally when external API calls fail and replay data exists.
- Match ID uploads are accepted and can drive API-only enrichment.

### Phase 3 — Structured AI Analysis

Phase 3 adds AI provider abstraction, structured coaching schemas, prompt/context building, AI run auditing, worker integration, and frontend rendering for `structured_ai_analysis`.

Automated checks:

```bash
cd apps/api
uv run pytest tests/test_ai_provider_foundation.py \
  tests/test_ai_analysis_schemas.py \
  tests/test_ai_analysis_generator.py \
  -v

cd ../web
npm run type-check
npm run build
```

Mock AI smoke configuration:

```env
ANALYSIS_MODE=ai
AI_PROVIDER=mock
AI_MODEL=mock-model
```

Manual smoke:

1. Start Postgres/Redis, API, worker, and frontend.
2. Create a `match_summary` upload.
3. Create an analysis job.
4. Open `/analyses/<job-id>`.

Expected results:

- `analysis_results.result_kind` is `structured_ai_analysis`.
- `schema_version` is `coaching-analysis-v1`.
- `ai_model_runs` records provider/model/status metadata.
- Frontend renders strengths, improvement areas, priority focus, evidence, and model metadata.

Live provider smoke, optional:

```env
ANALYSIS_MODE=ai
AI_PROVIDER=openai
AI_MODEL=gpt-4o-mini
OPENAI_API_KEY=<real-key>
```

Use live providers sparingly; component tests should remain deterministic with mocks.

### Phase 4 — RAG System

Phase 4 adds knowledge source ingestion, text chunking, embeddings, pgvector-backed strategy retrieval, `/strategy-search`, and retrieval context injection into AI analysis.

Automated checks:

```bash
cd apps/api
uv run pytest tests/test_rag_chunking.py \
  tests/test_embedding_providers.py \
  tests/test_rag_search.py \
  -v

cd ../web
npm run type-check
npm run build
```

Mock embedding smoke configuration:

```env
EMBEDDING_PROVIDER=mock
EMBEDDING_MODEL=mock-embedding
```

Manual smoke:

1. Run migrations with pgvector enabled.
2. Start API and frontend.
3. Open `http://localhost:3000/strategy-search`.
4. Paste a strategy note and ingest it.
5. Search for a related query.

Expected results:

- Source is stored as a `knowledge_sources` row.
- Content is chunked into `knowledge_chunks`.
- Embeddings are stored in `knowledge_embeddings`.
- Search returns ranked, citation-ready chunks.
- AI analysis can include retrieval context when enabled.

### Phase 5 — AI Workflow Orchestration

Phase 5 moves analysis execution behind a typed app-owned workflow with persisted `workflow_runs` and `workflow_steps` telemetry. The worker now delegates to the workflow runner.

Automated checks:

```bash
cd apps/api
uv run pytest tests/test_analysis_workflow_state.py \
  tests/test_analysis_workflow_nodes.py \
  tests/test_analysis_workflow_runner.py \
  tests/test_analysis_evals.py \
  -v
```

Eval fixture command:

```bash
cd apps/api
uv run python -m app.evals.run_analysis_fixtures --provider mock
```

Workflow smoke configuration:

```env
WORKFLOW_ENGINE=simple
WORKFLOW_VERSION=analysis-workflow-v1
ENABLE_RAG_IN_ANALYSIS=true
ENABLE_DEADLOCK_API_ENRICHMENT=true
AI_PROVIDER_FALLBACKS=openai_compatible:qwen-model,minimax:abab-model
```

Manual smoke:

1. Start Postgres/Redis, API, worker, and frontend.
2. Run an analysis job using `ANALYSIS_MODE=fake` and confirm fake workflow output.
3. Run an analysis job using `ANALYSIS_MODE=ai` and `AI_PROVIDER=mock`.
4. Inspect `workflow_runs` and `workflow_steps`.

Expected results:

- One workflow run is created per new job.
- Each node records step telemetry.
- State snapshots redact long/private summary text.
- Provider fallback parsing keeps the primary provider first.
- Eval fixtures pass deterministically with the mock provider.

### Phase 6 — Replay Intelligence Validation Gate

Phase 6 is not fully implemented. Current work is a validation spike to prove whether Clarity can extract meaningful Deadlock replay data before building Replay Intelligence features.

Automated checks:

```bash
cd apps/replay-parser
gradle test

cd ../api
uv run pytest tests/test_replay_parser_service.py -v
```

Debug discovery smoke with a real local replay:

```bash
cd apps/replay-parser
gradle installDist
build/install/replay-parser/bin/replay-parser \
  --input "$LOCAL_REPLAY_SAMPLE_PATH" \
  --pretty \
  --max-events 500 \
  --debug-discovery
```

Expected current results:

- Output remains compatible with `deadlock-replay-parse-v1`.
- Debug mode includes bounded discovery metadata such as `debug_discovery`, `sample_bytes`, and `first_bytes_hex`.
- `validated_real_events` is empty until real Clarity event extraction is wired.

Gate criteria before Phase 6 implementation can start:

- At least one real local `.dem` is parsed.
- Parser output includes verified replay-derived data beyond file metadata.
- Findings are recorded in `docs/phase-6-replay-intelligence-readiness-findings.md`.
- Recommendation is one of:
  - proceed with Clarity,
  - switch parser strategy,
  - postpone Replay Intelligence.

Minimum useful proof should include one or more of:

- match ID / duration / tick count,
- player slot / account / hero identity,
- death/combat/objective timeline events,
- item or build progression events.

## Manual End-to-End Smoke Tests

### Start the full local stack

Terminal 1:

```bash
docker compose -f infra/docker-compose.yml up -d
```

Terminal 2:

```bash
cd apps/api
uv run alembic upgrade head
uv run fastapi dev --port 8000
```

Terminal 3:

```bash
cd apps/api
uv run arq app.workers.worker.WorkerSettings
```

Terminal 4:

```bash
cd apps/web
npm run dev
```

### Full fake-analysis smoke

Recommended env:

```env
ANALYSIS_MODE=fake
EMBEDDING_PROVIDER=mock
WORKFLOW_ENGINE=simple
```

Steps:

1. Open `http://localhost:3000`.
2. Submit a match summary.
3. Create/start an analysis job.
4. Open the analysis detail page.
5. Confirm job completion and result rendering.

### Full AI + RAG mock smoke

Recommended env:

```env
ANALYSIS_MODE=ai
AI_PROVIDER=mock
AI_MODEL=mock-model
EMBEDDING_PROVIDER=mock
EMBEDDING_MODEL=mock-embedding
ENABLE_RAG_IN_ANALYSIS=true
WORKFLOW_ENGINE=simple
```

Steps:

1. Open `/strategy-search` and ingest a strategy note.
2. Search for that note to verify retrieval.
3. Submit a match summary from the homepage.
4. Run analysis.
5. Confirm structured AI result renders on `/analyses/<job-id>`.
6. Confirm workflow telemetry was written.

### Replay upload smoke

Recommended env:

```env
REPLAY_PARSER_COMMAND=/absolute/path/to/apps/replay-parser/build/install/replay-parser/bin/replay-parser
LOCAL_REPLAY_SAMPLE_PATH=/absolute/path/to/local-match.dem
ALLOW_LOCAL_REPLAY_PATHS=true
```

Steps:

1. Build parser with `gradle installDist`.
2. Start API and worker.
3. Create a replay upload metadata record.
4. Create an analysis job.
5. Confirm a replay parse artifact is persisted or a safe parser error is recorded.

## External Service Smoke Tests

These are not CI tests. Run them manually only when validating live integrations.

### Deadlock API

```bash
curl "https://api.deadlock-api.com/v1/matches/44009651/metadata?disable_steam=true"
curl "https://assets.deadlock-api.com/v2/heroes/63" | jq '.name'
curl "https://assets.deadlock-api.com/v2/items/1233782561" | jq '.name'
```

### OpenAI-compatible chat provider

```env
ANALYSIS_MODE=ai
AI_PROVIDER=openai_compatible
AI_BASE_URL=https://your-provider.example/v1
AI_API_KEY=<real-key>
AI_MODEL=<model-name>
```

Run one match-summary analysis and confirm schema validation succeeds.

### OpenAI-compatible embedding provider

```env
EMBEDDING_PROVIDER=openai_compatible
EMBEDDING_BASE_URL=https://your-provider.example/v1
EMBEDDING_API_KEY=<real-key>
EMBEDDING_MODEL=<embedding-model>
```

Ingest one note through `/strategy-search` and confirm search returns results.

## Before Opening a PR

Use this checklist:

- [ ] `cd apps/api && uv run ruff check .`
- [ ] Backend component tests pass.
- [ ] Full backend tests pass if Docker/Postgres is available.
- [ ] `cd apps/web && npm run type-check`
- [ ] `cd apps/web && npm run build`
- [ ] `cd apps/replay-parser && gradle test`
- [ ] `cd apps/api && uv run python -m app.evals.run_analysis_fixtures --provider mock`
- [ ] Migrations are included for DB model changes.
- [ ] `.env.example` documents any new config.
- [ ] Docs are updated for changed behavior.
- [ ] No `.dem`, parser artifact, `.env.local`, `__pycache__`, Gradle cache, or build output files are staged.

## Common Issues

| Problem | Likely cause | Fix |
|---|---|---|
| `ConnectionRefusedError` on port `5433` | PostgreSQL is not running | `docker compose -f infra/docker-compose.yml up -d` |
| Redis queue errors | Redis is not running | Start Docker Compose and verify `localhost:6379` |
| Alembic cannot connect | Wrong `DATABASE_SYNC_URL` | Copy `.env.example` and verify local DB credentials |
| Endpoint tests fail but component tests pass | DB integration dependency missing | Start Postgres and run `uv run alembic upgrade head` |
| `ModuleNotFoundError: app...` | Running tests from wrong directory or missing deps | `cd apps/api && uv sync --extra dev` |
| `gradle: command not found` | Gradle missing | `brew install gradle` |
| `java: command not found` | Java missing | `brew install openjdk@17` and set `JAVA_HOME` if needed |
| TypeScript errors after frontend changes | Dependencies or types stale | `cd apps/web && npm install && npm run type-check` |
| AI provider returns invalid JSON | Live model not following schema | Re-run with `AI_PROVIDER=mock`, then inspect provider response handling |
| RAG search returns no results | No sources ingested or embeddings not configured | Use `EMBEDDING_PROVIDER=mock`, ingest a note, then search again |
| Replay parser says input unreadable | Bad local path or permissions | Use an absolute path and do not rely on shell-specific shortcuts |
| Phase 6 output has no real events | Real Clarity extraction not wired yet | Treat as not ready; update findings only when real replay data is verified |
