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

### 7. Auth, Uploads, and Analysis Jobs

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

## Phases

1. **Foundation** — Repository, backend shell, database, auth boundary, frontend shell
2. **Async Pipeline** — Job queue, worker scaffolding, status API
3. **Clarity Replay Parser Spike** — Validate skadistats/clarity for Deadlock replays
4. **Structured AI Analysis** — AI schemas, prompt templates, analysis endpoints
5. **RAG System** — Strategy knowledge ingestion, embedding, retrieval
6. **AI Workflow Orchestration** — LangGraph workflows, coaching generation
7. **Replay Intelligence** — Replay parsing, match timeline, coaching insights
8. **Frontend Polish** — Dashboard, history, UX improvements