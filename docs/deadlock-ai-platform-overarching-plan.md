# Deadlock AI Platform — Overarching Architecture Plan

## Table of Contents

- [[#1. Product Vision|1. Product Vision]]
- [[#2. Core Principles|2. Core Principles]]
- [[#3. Initial MVP Goals|3. Initial MVP Goals]]
- [[#4. High-Level Architecture|4. High-Level Architecture]]
- [[#5. Application Stack|5. Application Stack]]
  - [[#Frontend|Frontend]]
  - [[#Authentication|Authentication]]
  - [[#Backend API|Backend API]]
  - [[#Database|Database]]
  - [[#Queue / Workers|Queue / Workers]]
  - [[#Object Storage|Object Storage]]
  - [[#AI Stack|AI Stack]]
  - [[#Replay Parsing|Replay Parsing]]
- [[#6. Core Domain Model Direction|6. Core Domain Model Direction]]
- [[#7. Development Phases|7. Development Phases]]
  - [[#Phase 1 — Foundation|Phase 1 — Foundation]]
  - [[#Phase 2 — Async Pipeline|Phase 2 — Async Pipeline]]
  - [[#Phase 2.5 — Clarity Replay Parser Spike|Phase 2.5 — Clarity Replay Parser Spike]]
  - [[#Phase 3 — Structured AI Analysis|Phase 3 — Structured AI Analysis]]
  - [[#Phase 4 — RAG System|Phase 4 — RAG System]]
  - [[#Phase 5 — AI Workflow Orchestration|Phase 5 — AI Workflow Orchestration]]
  - [[#Phase 6 — Replay Intelligence|Phase 6 — Replay Intelligence]]
  - [[#Phase 7 — Frontend Polish|Phase 7 — Frontend Polish]]
- [[#8. Explicit Early Non-Goals|8. Explicit Early Non-Goals]]
- [[#9. Current Recommended Next Step|9. Current Recommended Next Step]]

## 1. Product Vision

Deadlock AI Platform is an AI-powered coaching and match analysis platform for Deadlock players. It combines replay analysis, AI-generated coaching, retrieval-augmented strategy search, match timelines, build recommendations, hero matchup intelligence, vision/screenshot analysis, and long-term player improvement tracking.

The product should demonstrate production-quality AI systems engineering without becoming infrastructure-heavy.

## 2. Core Principles

- AI workflows are the product, not infrastructure.
- Keep operational complexity low.
- Optimize for fast iteration and solo developer productivity.
- Build modularly, not prematurely distributed.
- Prefer managed stateful infrastructure.
- Use async workers for expensive AI/replay jobs.
- Docker-first deployment, no Kubernetes initially.
- Avoid generic chatbot behavior; focus on useful coaching outputs.

## 3. Initial MVP Goals

Users should be able to:

1. Sign in with Discord or GitHub.
2. Upload replay files, screenshots, or match summaries.
3. Trigger asynchronous analysis jobs.
4. Receive structured coaching insights.
5. View AI-generated match summaries.
6. Browse previous analyses.
7. Search strategy knowledge using RAG.

## 4. High-Level Architecture

```txt
Browser
↓
Cloudflare
↓
Caddy
↓
Dokploy
├── Next.js Frontend
├── FastAPI API
├── Worker Containers
├── Redis
└── GlitchTip

External Services
├── Neon PostgreSQL + pgvector
├── Cloudflare R2
├── PostHog
├── OpenAI / Anthropic
└── Resend
```

## 5. Application Stack

### Frontend

- Next.js App Router
- React
- TypeScript
- Tailwind CSS
- shadcn/ui
- TanStack Query
- react-hook-form
- zod
- recharts
- Vercel AI SDK later for streaming UX

### Authentication

- Better Auth inside Next.js
- Initial OAuth providers: Discord and GitHub
- Next.js owns browser auth/session handling
- FastAPI validates signed auth tokens/session-derived JWTs
- Avoid duplicate auth ownership between frontend and backend

### Backend API

- FastAPI
- Versioned API under `/api/v1/`
- Responsibilities:
  - REST API
  - upload coordination
  - job creation
  - AI orchestration entrypoints
  - RAG endpoints
  - match/analysis APIs
  - SSE endpoints later
  - internal auth validation

### Database

- Neon PostgreSQL
- pgvector extension
- SQLModel ORM
- Alembic migrations

### Queue / Workers

- Redis
- Arq async workers
- Worker responsibilities:
  - replay processing
  - screenshot/vision analysis
  - embedding generation
  - AI summaries
  - RAG indexing
  - retry handling
  - notifications later

### Object Storage

- Cloudflare R2
- Use presigned upload URLs where possible
- Stores:
  - replay files
  - screenshots
  - parsed replay artifacts
  - AI artifacts
  - temporary exports

### AI Stack

Initial:

- OpenAI/Anthropic SDKs directly through a thin internal AI client
- Instructor for structured outputs
- Pydantic schemas for reliable persisted results
- OpenAI `text-embedding-3-small` for embeddings
- pgvector for retrieval

Later:

- LangGraph for multi-step workflows
- LiteLLM if provider routing/cost controls become necessary
- Ragas/DeepEval once real RAG workflows exist

### Replay Parsing

Use Clarity as the first replay parser candidate.

- Clarity is Java-based and supports Deadlock replay files.
- Do not couple the app directly to Clarity internals.
- Build a Java parser CLI/container that emits app-owned normalized JSON.
- Python workers call the parser and consume the normalized output.

Preferred flow:

```txt
Replay uploaded to R2
↓
FastAPI creates analysis job
↓
Arq worker starts job
↓
Clarity parser reads replay
↓
Parser emits normalized JSON artifact
↓
Python AI workflow reads parsed artifact
↓
Structured coaching result is persisted
↓
Frontend displays result
```

## 6. Core Domain Model Direction

Initial tables likely include:

- `users`
- `auth_identities` or provider account mapping
- `uploads`
- `matches`
- `analysis_jobs`
- `analysis_results`
- `analysis_events`
- `knowledge_sources`
- `knowledge_chunks`
- `embeddings`
- `heroes`
- `patch_versions`

Important design rules:

- Every upload belongs to a user.
- Every analysis job has status, progress, error, and retry metadata.
- AI outputs should record model, prompt version, workflow version, and schema version.
- Parsed replay artifacts should be stored separately from coaching outputs.
- RAG knowledge should be source-linked and eventually patch-aware.

## 7. Development Phases

### Phase 1 — Foundation

Goal: create the working full-stack shell and prove the app can authenticate users, talk to the backend, persist data, use Redis, and coordinate file uploads.

Build:

- repository/project structure
- Next.js shell
- FastAPI shell
- Docker Compose for local Postgres and Redis
- SQLModel + Alembic setup
- Better Auth proof-of-concept
- backend auth validation boundary
- base DB models
- R2 signed upload design/proof
- health checks
- basic CI checks

Done when:

- frontend runs locally
- backend runs locally
- Postgres and Redis run via Docker Compose
- migrations apply cleanly
- frontend can call backend health endpoint
- authenticated user identity can be represented consistently
- upload records can be created

### Phase 2 — Async Pipeline

Goal: prove the core product architecture without real AI dependency.

Build:

```txt
Upload replay/screenshot/summary
→ create upload record
→ create analysis job
→ enqueue Arq task
→ worker processes fake analysis
→ save structured fake result
→ frontend polls status
→ result page displays output
```

Done when:

- a user can submit an input
- job status progresses through queued/running/succeeded/failed
- worker result is persisted
- old analyses can be browsed

### Phase 2.5 — Clarity Replay Parser Spike

Goal: prove Deadlock replay parsing before building product features around it.

Build:

- small Java CLI using Clarity
- parse one Deadlock replay file
- emit normalized JSON with match overview and basic events
- call parser from a Python worker, likely via subprocess first
- store parsed artifact

Done when:

- one real replay can produce normalized JSON
- parser failures are captured cleanly
- downstream Python code does not depend on Clarity-specific objects

### Phase 3 — Structured AI Analysis

Goal: first real intelligent workflow.

Build:

- Instructor/Pydantic output schemas
- AI client abstraction
- match summary generation
- coaching insight generation
- persisted structured AI results
- prompt/model/workflow version metadata

Done when:

- an uploaded match summary or parsed artifact produces useful structured coaching output
- frontend renders the structured result cleanly

### Phase 4 — RAG System

Goal: searchable strategy knowledge and retrieval-augmented coaching.

Build:

- knowledge source ingestion
- chunking
- embeddings
- pgvector search
- citation/source display
- strategy search endpoint and UI
- retrieval context injection into coaching workflow

Done when:

- user can search strategy knowledge
- AI coaching can cite retrieved sources

### Phase 5 — AI Workflow Orchestration

Goal: make AI workflows more robust and multi-step.

Build:

- LangGraph workflows where useful
- analysis graph for normalization → retrieval → coaching → validation
- retry/fallback behavior
- basic evaluation datasets
- Ragas/DeepEval for regression checks

Done when:

- workflows are observable, typed, repeatable, and testable

### Phase 6 — Replay Intelligence

Goal: move beyond summaries into match understanding.

Build:

- richer Clarity event extraction
- death/timing/objective/teamfight timeline events
- item/build progression extraction where possible
- semantic timeline analysis
- hero/matchup-specific coaching

Done when:

- replay-derived timelines produce meaningful coaching without manual summaries

### Phase 7 — Frontend Polish

Goal: portfolio-quality product experience.

Build:

- dashboard views
- rich analysis pages
- charts and timelines
- match history
- trends over time
- PostHog funnels/events
- SSE progress/streaming UX where useful

Done when:

- the product feels coherent, fast, and demo-ready

## 8. Explicit Early Non-Goals

Do not add early:

- Kubernetes
- service mesh
- Kafka
- complex microservices
- multi-region infrastructure
- heavy OpenTelemetry setup
- separate vector database
- autonomous agent gimmicks
- full replay parsing as a blocking MVP dependency

## 9. Current Recommended Next Step

Start with a detailed Phase 1 foundation plan, then implement in small commits. Phase 1 should prove the full-stack skeleton and development workflow before adding real AI or replay complexity.
