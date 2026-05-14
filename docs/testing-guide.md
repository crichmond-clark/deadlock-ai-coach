# Testing Guide — Phase 1 through 3

## Quick Reference

| Layer | Command | Requires |
|---|---|---|
| Python unit/component tests | `uv run pytest tests/test_ai_provider_foundation.py tests/test_ai_analysis_schemas.py tests/test_ai_analysis_generator.py -v` | Python venv |
| Full Python tests | `uv run pytest -v` | Python venv + Postgres for integration-sensitive tests |
| Java parser tests | `gradle test` | Java 17+, Gradle |
| TypeScript typecheck | `npx tsc --noEmit` | Node.js, npm install |
| Web build check | `npm run build` | Node.js, npm install |
| Full integration | needs Docker | Postgres + Redis containers |

---

## 1. Prerequisites

### Docker (for integration tests)
```bash
docker compose -f infra/docker-compose.yml up -d
docker compose -f infra/docker-compose.yml ps
```
Services: PostgreSQL `localhost:5433`, Redis `localhost:6379`

### Python venv + deps
```bash
cd apps/api
uv sync --extra dev
```

### Environment
```bash
cp .env.example .env.local
# DATABASE_URL and REDIS_URL in .env.local should match docker-compose
```

### Java + Gradle (for Phase 2.5 replay parser)
```bash
java -version   # need 17+
gradle --version
```
Install via Homebrew: `brew install openjdk@17 gradle`

### Frontend (for Phase 1 web shell)
```bash
cd apps/web
npm install
```

---

## 2. Test Layers

### Layer 1: Unit Tests (no Docker needed)

```bash
cd apps/api
uv run pytest -v
```

Phase 1-3 component tests cover these files:

| File | Tests | Covers |
|---|---|---|
| `test_health.py` | 1 | Health check endpoint |
| `test_analysis_jobs.py` | 8 | Upload validation, auth, job/upload CRUD |
| `test_replay_parser_service.py` | 5 | Subprocess wrapper: success, config, exit codes, JSON, timeout |
| `test_deadlock_api_client.py` | 14 | HTTP clients: success, 4xx, 5xx, rate limits, timeout |
| `test_deadlock_api_assets.py` | 13 | Catalog sync, hero resolution, bulk resolve |
| `test_deadlock_api_metadata.py` | 7 | Match metadata normalize, cache hit/stale, force-refresh |
| `test_deadlock_api_enrichment.py` | 9 | Extract IDs, source warnings, replay-only, api-only, failure handling |
| `test_ai_provider_foundation.py` | 6 | Mock/OpenAI-compatible provider behavior, JSON extraction |
| `test_ai_analysis_schemas.py` | 3 | Structured coaching schema and prompt context compaction |
| `test_ai_analysis_generator.py` | 2 | Structured analysis generation and AI model run audit behavior |

Most component tests mock external dependencies (HTTP + DB). Endpoint tests in `test_health.py` and `test_analysis_jobs.py` need local PostgreSQL because dev-auth auto-creates users.

### Layer 2: Replay Parser Java Tests

```bash
cd apps/replay-parser
gradle test
```

Tests validate CLI argument parsing, exit codes, and JSON schema output shape.

### Layer 3: Linting + Typechecking

```bash
# Python
cd apps/api && uv run ruff check .

# Frontend typecheck
cd apps/web && npx tsc --noEmit

# Frontend build (catches more issues)
cd apps/web && npm run build
```

### Layer 4: Integration Tests (needs Docker)

```bash
# Start infra
docker compose -f infra/docker-compose.yml up -d

# Run migrations
cd apps/api
uv run alembic upgrade head

# Run all tests including those that hit real DB
uv run pytest -v

# Or target just integration-sensitive tests
uv run pytest tests/test_health.py tests/test_analysis_jobs.py -v
```

Integration tests use the real PostgreSQL at `localhost:5433` and require the database to exist with migrations applied.

### Layer 5: Manual API Smoke Tests

**Server start:**
```bash
cd apps/api && uv run fastapi dev --port 8000
```

**Swagger:** http://localhost:8000/docs

**Manual curl workflow:**
```bash
# Health
curl http://localhost:8000/api/v1/health

# Create upload (dev auth via header)
curl -X POST http://localhost:8000/api/v1/uploads \
  -H "X-Dev-User-Id: dev-user-00000000-0000-0000-0000-000000000001" \
  -H "Content-Type: application/json" \
  -d '{"kind":"replay","filename":"match.dem","size_bytes":123456}'

# List uploads
curl http://localhost:8000/api/v1/uploads \
  -H "X-Dev-User-Id: dev-user-00000000-0000-0000-0000-000000000001"

# Create analysis job (use upload id from previous response)
curl -X POST http://localhost:8000/api/v1/analysis-jobs \
  -H "X-Dev-User-Id: dev-user-00000000-0000-0000-0000-000000000001" \
  -H "Content-Type: application/json" \
  -d '{"upload_id":"<uuid>"}'

# Poll job status
curl http://localhost:8000/api/v1/analysis-jobs/<job-uuid> \
  -H "X-Dev-User-Id: dev-user-00000000-0000-0000-0000-000000000001"
```

**Worker (in separate terminal):**
```bash
cd apps/api && uv run arq app.workers.worker.WorkerSettings
```

### Layer 6: Structured AI Mock Smoke Check

Use the mock provider to exercise Phase 3 without external AI calls:

```env
ANALYSIS_MODE=ai
AI_PROVIDER=mock
AI_MODEL=mock-model
```

Then start API + worker, create a match summary upload, create an analysis job, and open `/analyses/<job-id>`. The result should have `result_kind=structured_ai_analysis` and schema `coaching-analysis-v1`.

Run Phase 3 component checks directly:

```bash
cd apps/api
uv run pytest tests/test_ai_provider_foundation.py tests/test_ai_analysis_schemas.py tests/test_ai_analysis_generator.py -v
uv run ruff check .
cd ../web
npm run type-check
npm run build
```

### Layer 7: Deadlock API Live Smoke Checks

Run these ad-hoc to validate the external API is still reachable. These hit the real internet and are not in CI:

```bash
# Match metadata
curl "https://api.deadlock-api.com/v1/matches/44009651/metadata?disable_steam=true"

# Hero by name
curl "https://assets.deadlock-api.com/v2/heroes/63" | jq '.name'
# → "Mina"

# Item by ID
curl "https://assets.deadlock-api.com/v2/items/1233782561" | jq '.name'
# → "Love Bites"
```

These endpoints have no auth required but are rate-limited. An optional `DEADLOCK_API_KEY` in `.env.local` raises the limit.

---

## 3. Phase-by-Phase Test Coverage

### Phase 1 — Foundation
- `test_health.py`: API health check
- `test_analysis_jobs.py`: Auth boundary (8 tests)

### Phase 2 — Async Pipeline
- `test_analysis_jobs.py`: Upload CRUD, analysis job create/poll

### Phase 2.5 — Replay Parser
- `test_replay_parser_service.py` (Python): 5 tests
- `apps/replay-parser/` (Java): `./gradlew test`

### Phase 2.6 — Deadlock API Integration
- `test_deadlock_api_client.py`: 14 tests — Game API + Assets API clients
- `test_deadlock_api_assets.py`: 13 tests — catalog sync + resolution
- `test_deadlock_api_metadata.py`: 7 tests — fetch, cache, normalize
- `test_deadlock_api_enrichment.py`: 9 tests — enrichment pipeline

### Phase 3 — Structured AI Analysis
- `test_ai_provider_foundation.py`: provider protocol, mock provider, OpenAI-compatible HTTP behavior
- `test_ai_analysis_schemas.py`: coaching output schema and bounded input context
- `test_ai_analysis_generator.py`: structured generation and `ai_model_runs` audit persistence

---

## 4. Common Issues

| Problem | Fix |
|---|---|
| `ConnectionRefusedError` on 5433 | `docker compose -f infra/docker-compose.yml up -d` |
| `ModuleNotFoundError` | `cd apps/api && uv sync --extra dev` |
| `gradle: command not found` | `brew install gradle` |
| `java: command not found` | `brew install openjdk@17` |
| TypeScript errors | `cd apps/web && npm install` |
| Alembic migration errors | Run migrations: `uv run alembic upgrade head` |
| `X-Dev-User-Id` not found | Seed DB first — dev user is auto-created on first request |
