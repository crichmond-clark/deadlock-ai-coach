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

### Deadlock API Integration

Use the [deadlock-api.com](https://deadlock-api.com) open-source API (MIT, 69+ endpoints) as a complementary data source alongside replay parsing.

- **Match Metadata**: Structured post-match data (item/ability entries, deaths, stats, positions, objectives) — available with just a `match_id`, no replay needed.
- **Asset Resolution**: Resolve raw hero/item/ability/upgrade IDs from replay output to names, images, stats, and descriptions via the Assets API.
- **Global Analytics**: Hero win rates, counter stats, synergy stats, item win rates, build stats, ability order stats — later provides meta-aware context for AI coaching.
- **Player History**: `/v1/players/{id}/match-history` enables long-term tracking without per-match replay uploads.
- **Data Seeding**: Database dumps and SQL endpoint may later seed the RAG knowledge base with real match data.

Integration approach:

- Thin Python clients for separate hosts: `https://api.deadlock-api.com` for game/stat data and `https://assets.deadlock-api.com` for heroes/items/assets.
- Background sync jobs to keep hero/game-asset catalog data fresh; analytics sync is a later slice after core metadata/enrichment works.
- Match metadata fetched lazily when users provide a `match_id` (with or without a replay), cached by match ID, and stored as raw JSONB plus a small normalized summary.
- API data enriches replay-derived artifacts without replacing the replay parser as the source of mechanical/tick-level learning.

This API is not a replacement for replay parsing — it provides the global context and structured summary layer that makes AI coaching intelligent, while Clarity provides the tick-level mechanical data for deep analysis.

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

### Phase 2.6 — Deadlock API Integration

Goal: add structured match data and asset resolution as a complementary data layer alongside replay parsing.

Build:

- Separate Python clients for `api.deadlock-api.com` and `assets.deadlock-api.com`
- Hero/game-asset resolution service (raw hero/item/ability/upgrade ID → name, image, metadata where available)
- Match metadata service (fetch/cache structured post-match data given a `match_id`)
- Background sync for hero/game-asset catalog data (scheduled Arq tasks)
- Match metadata fetch integrated into the existing analysis pipeline (with or without replay)
- API enrichment layer that augments Clarity replay output with resolved names and source warnings
- Optional follow-up analytics slice for hero win rates, counters, synergies, item stats, and build stats

Done when:

- hero/game-asset IDs from replay output are resolved to names and images in the app
- a `match_id` alone (no replay) can produce cached structured match metadata and an enriched context
- enrichment gracefully degrades when the external API is unavailable
- the API clients handle rate limits, caching, and errors gracefully

### Phase 3 — Structured AI Analysis

Goal: first real intelligent workflow — now enriched with global analytics context.

Build:

- Instructor/Pydantic output schemas
- AI client abstraction
- match summary generation
- coaching insight generation using both replay data (Clarity) and meta context (deadlock-api.com)
- persisted structured AI results
- prompt/model/workflow version metadata

Done when:

- an uploaded match summary or parsed artifact produces useful structured coaching output
- coaching includes meta-aware context (e.g., "your hero has 47% win rate at your rank against this matchup")
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

Goal: move beyond summaries into deep match understanding, combining replay data with API analytics.

Build:

- richer Clarity event extraction (ability casts, projectiles, modifiers, damage instances)
- death/timing/objective/teamfight timeline events
- item/build progression extraction with API-resolved item details
- cross-reference replay mechanics against API global stats (e.g., "your hook accuracy is 33% vs rank average of 41%")
- teamfight detection via clustered damage events + death proximity
- semantic timeline analysis
- hero/matchup-specific coaching with API win-rate context

Done when:

- replay-derived timelines produce meaningful coaching without manual summaries
- coaching insights combine mechanical analysis (replay) with meta analysis (API)

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

Phase 1 and 2 are complete. Phase 2.5 (Clarity Replay Parser) has the Java CLI skeleton and Python integration built but real Clarity extraction from a `.dem` file has not been verified yet — the next step is to parse one real Deadlock replay with Clarity and update the findings doc.

Phase 2.6 (Deadlock API Integration) can proceed in parallel with the Clarity spike, since it does not depend on replay parsing. It provides immediate value by resolving IDs from existing replay artifacts and enabling match_id-based analysis without replays.
