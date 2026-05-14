# Deadlock AI Platform

AI-powered coaching and match analysis platform for Deadlock players.

## Overview

Combines replay analysis, AI-generated coaching, retrieval-augmented strategy search, match timelines, build recommendations, hero matchup intelligence, vision/screenshot analysis, and long-term player improvement tracking.

## Tech Stack

- **Frontend**: Next.js (App Router), React, TypeScript, Tailwind CSS, shadcn/ui, TanStack Query
- **Backend**: FastAPI, SQLModel, Alembic, Arq workers
- **Database**: Neon PostgreSQL + pgvector
- **Queue**: Redis + Arq
- **Storage**: Cloudflare R2
- **Auth**: Better Auth (Discord, GitHub OAuth)

## Local Development Setup

### 1. Prerequisites

- Docker + Docker Compose
- Node.js 20+
- Python 3.12+
- Java 17+ for the Phase 2.5 replay parser spike
- (Optional for AI work) OpenAI / Anthropic API keys

### 2. Start Infrastructure

```bash
# Start Postgres and Redis
docker compose -f infra/docker-compose.yml up -d

# Verify services are healthy
docker compose -f infra/docker-compose.yml ps
```

Services will be available at:
- **PostgreSQL**: `localhost:5433` (user: `deadlock_ai`, password: `deadlock_ai_local`, db: `deadlock_ai`)
- **Redis**: `localhost:6379`

### 3. Configure Environment

```bash
# Copy environment template
cp .env.example .env.local

# Edit .env.local with your values
```

### 4. Run Backend

```bash
cd apps/api
uv sync --extra dev
uv run alembic upgrade head
uv run fastapi dev --port 8000
```

API docs available at `http://localhost:8000/docs`

### 5. Run Frontend

```bash
cd apps/web
npm install
npm run dev
```

App available at `http://localhost:3000`

### 6. Run Async Worker

Phase 2 uses Arq + Redis for fake asynchronous analysis jobs.

```bash
cd apps/api
uv run arq app.workers.worker.WorkerSettings
```

### 7. Replay Parser Spike

Build and run the local parser CLI:

```bash
cd apps/replay-parser
gradle test
gradle installDist
build/install/replay-parser/bin/replay-parser --input /path/to/match.dem --pretty
```

For worker integration, set local-only parser variables in `.env.local`:

```env
REPLAY_PARSER_COMMAND=/absolute/path/to/apps/replay-parser/build/install/replay-parser/bin/replay-parser
LOCAL_REPLAY_SAMPLE_PATH=/absolute/path/to/match.dem
ALLOW_LOCAL_REPLAY_PATHS=true
```

Replay files are ignored by git. Do not commit `.dem` files or parser output artifacts.

### 8. Structured AI Analysis

By default local analysis stays deterministic:

```env
ANALYSIS_MODE=fake
```

To run Phase 3 structured AI analysis without external model calls, use the mock provider:

```env
ANALYSIS_MODE=ai
AI_PROVIDER=mock
AI_MODEL=mock-model
```

For OpenAI:

```env
ANALYSIS_MODE=ai
AI_PROVIDER=openai
AI_MODEL=gpt-4o-mini
OPENAI_API_KEY=your_key
```

For OpenAI-compatible providers such as Ollama Cloud, OpenRouter, vLLM, or LM Studio:

```env
ANALYSIS_MODE=ai
AI_PROVIDER=openai_compatible
AI_BASE_URL=https://your-provider.example/v1
AI_API_KEY=your_key
AI_MODEL=your-model
```

Structured AI results are persisted as `result_kind=structured_ai_analysis` with schema `coaching-analysis-v1`. Raw prompts are not stored unless `AI_STORE_RAW_PROMPTS=true`.

### 9. Strategy Knowledge / RAG

Phase 4 adds pasted-note ingestion and semantic strategy search backed by PostgreSQL + pgvector.

For local no-cost testing:

```env
EMBEDDING_PROVIDER=mock
EMBEDDING_MODEL=mock-embedding
```

For OpenAI embeddings:

```env
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
OPENAI_API_KEY=your_key
```

For OpenAI-compatible embedding endpoints:

```env
EMBEDDING_PROVIDER=openai_compatible
EMBEDDING_BASE_URL=https://your-provider.example/v1
EMBEDDING_API_KEY=your_key
EMBEDDING_MODEL=your-embedding-model
```

Run migrations to enable pgvector and create the knowledge tables:

```bash
cd apps/api
uv run alembic upgrade head
```

The frontend strategy search UI is available at `/strategy-search`.

### 10. AI Workflow Orchestration

Phase 5 moves analysis execution behind a typed workflow runner with DB telemetry in `workflow_runs` and `workflow_steps`.

Default local settings:

```env
WORKFLOW_ENGINE=simple
WORKFLOW_VERSION=analysis-workflow-v1
ENABLE_RAG_IN_ANALYSIS=true
ENABLE_DEADLOCK_API_ENRICHMENT=true
```

Optional provider fallback chain for structured AI generation:

```env
AI_PROVIDER_FALLBACKS=openai_compatible:qwen-model,minimax:abab-model
```

Run the deterministic workflow eval fixtures:

```bash
cd apps/api
uv run python -m app.evals.run_analysis_fixtures --provider mock
```

### 11. Auth, Uploads, and Analysis Jobs

- Local dev API calls use `X-Dev-User-Id` until production token validation is wired.
- Better Auth is mounted at `/api/auth/[...all]` with Discord/GitHub provider configuration from environment variables.
- Add OAuth credentials to `.env.local` using `.env.example` or `apps/web/.env.example`.
- The frontend shell includes a basic upload metadata form backed by `POST /api/v1/uploads`.
- Phase 2 adds fake async analysis: `POST /api/v1/analysis-jobs` enqueues a worker task, the frontend polls job status, and `/analyses/[jobId]` displays the persisted fake result.

## Project Structure

```
deadlock-ai-coach/
├── apps/
│   ├── api/           # FastAPI backend
│   └── web/           # Next.js frontend
├── infra/             # Docker Compose, infrastructure config
├── docs/             # Architecture and phase plans
├── .env.example       # Environment variable template
├── .gitignore
└── README.md
```

## Documentation

- [[docs/deadlock-ai-platform-overarching-plan|Overarching Architecture Plan]]
- [[docs/phase-1-foundation-plan|Phase 1 Foundation Plan]]
- [[docs/phase-2-async-pipeline-plan|Phase 2 Async Pipeline Plan]]
- [[docs/phase-3-structured-ai-analysis-plan|Phase 3 Structured AI Analysis Plan]]
- [[docs/phase-4-rag-system-plan|Phase 4 RAG System Plan]]
- [[docs/phase-5-ai-workflow-orchestration-plan|Phase 5 AI Workflow Orchestration Plan]]

## Phases

1. **Foundation** — Repository, backend shell, database, auth boundary, frontend shell
2. **Async Pipeline** — Job queue, worker scaffolding, status API
3. **Clarity Replay Parser Spike** — Validate skadistats/clarity for Deadlock replays
4. **Structured AI Analysis** — AI schemas, prompt templates, analysis endpoints
5. **RAG System** — Strategy knowledge ingestion, embedding, retrieval
6. **AI Workflow Orchestration** — LangGraph workflows, coaching generation
7. **Replay Intelligence** — Replay parsing, match timeline, coaching insights
8. **Frontend Polish** — Dashboard, history, UX improvements