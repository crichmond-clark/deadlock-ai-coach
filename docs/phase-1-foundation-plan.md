# Phase 1 Foundation Plan

## Table of Contents

- [[#1. Problem Statement|1. Problem Statement]]
- [[#2. Goals & Non-Goals|2. Goals & Non-Goals]]
- [[#3. Proposed Architecture|3. Proposed Architecture]]
- [[#4. Component Breakdown|4. Component Breakdown]]
- [[#5. Data Flow|5. Data Flow]]
  - [[#Health Check Flow|Health Check Flow]]
  - [[#Database Flow|Database Flow]]
  - [[#Auth Boundary Flow|Auth Boundary Flow]]
  - [[#Upload Metadata Flow|Upload Metadata Flow]]
- [[#6. Interface Contracts|6. Interface Contracts]]
  - [[#Endpoint: `GET /api/v1/health`|GET /api/v1/health]]
  - [[#Endpoint: `GET /api/v1/ready`|GET /api/v1/ready]]
  - [[#Endpoint: `GET /api/v1/me`|GET /api/v1/me]]
  - [[#Endpoint: `POST /api/v1/uploads`|POST /api/v1/uploads]]
  - [[#Initial Data Models|Initial Data Models]]
    - [[#Model Scope Rules|Model Scope Rules]]
    - [[#User|User]]
    - [[#AuthIdentity|AuthIdentity]]
    - [[#Upload|Upload]]
    - [[#AnalysisJob|AnalysisJob]]
- [[#7. File Changes|7. File Changes]]
- [[#8. Implementation Phases|8. Implementation Phases]]
  - [[#Phase 1A — Repository and Local Infrastructure|Phase 1A — Repository and Local Infrastructure]]
  - [[#Phase 1B — FastAPI Backend Shell|Phase 1B — FastAPI Backend Shell]]
  - [[#Phase 1C — Database Models and Migrations|Phase 1C — Database Models and Migrations]]
  - [[#Phase 1D — Auth Boundary and Upload Metadata API|Phase 1D — Auth Boundary and Upload Metadata API]]
  - [[#Phase 1E — Next.js Frontend Shell|Phase 1E — Next.js Frontend Shell]]
  - [[#Phase 1F — Better Auth Integration Skeleton|Phase 1F — Better Auth Integration Skeleton]]
  - [[#Phase 1G — Foundation Review and Cleanup|Phase 1G — Foundation Review and Cleanup]]
- [[#9. Testing Strategy|9. Testing Strategy]]
- [[#10. Security Implications|10. Security Implications]]
- [[#11. Risks & Tradeoffs|11. Risks & Tradeoffs]]
- [[#12. Open Questions|12. Open Questions]]

## 1. Problem Statement

The project currently needs a working full-stack foundation before AI, replay parsing, or async analysis features can be built safely. Phase 1 establishes the repository structure, local development environment, frontend shell, backend API shell, database/migration setup, Redis connectivity, auth boundary, and upload metadata model.

This phase matters because every later feature depends on stable development ergonomics and clear boundaries between Next.js, FastAPI, PostgreSQL, Redis, and object storage.

## 2. Goals & Non-Goals

- Goals:
  - Create a monorepo-style app structure for frontend and backend.
  - Add a Next.js App Router frontend shell.
  - Add a FastAPI backend shell under `/api/v1`.
  - Add Docker Compose for local PostgreSQL and Redis.
  - Add SQLModel database setup and Alembic migrations.
  - Define the initial core database models needed for users, uploads, and jobs.
  - Establish the auth boundary between Better Auth in Next.js and FastAPI.
  - Add basic health/readiness checks.
  - Add basic frontend-to-backend connectivity.
  - Add initial environment variable examples and developer documentation.
  - Add lightweight lint/type/test commands where practical.

- Non-Goals:
  - Real AI analysis.
  - LangGraph workflows.
  - RAG ingestion or embeddings.
  - Clarity replay parsing.
  - Production deployment automation.
  - Full OAuth production setup.
  - Full R2 uploads, unless implemented as a local/interface stub.
  - WebSockets or SSE streaming.
  - Complex observability beyond basic logging.

## 3. Proposed Architecture

Use a simple monorepo layout:

```txt
deadlock-ai-coach/
  apps/
    web/          # Next.js App Router frontend
    api/          # FastAPI backend
  infra/
    docker-compose.yml
  docs/
  README.md
```

Local development should run stateful dependencies in Docker and application processes natively:

```txt
Docker Compose:
├── postgres
└── redis

Native processes:
├── Next.js dev server
└── FastAPI dev server
```

The initial auth architecture should be explicit but minimal:

```txt
Browser
↓
Next.js / Better Auth owns OAuth + browser session
↓
Next.js calls FastAPI with signed internal auth token or session-derived bearer token
↓
FastAPI validates token and maps external auth identity to backend user record
```

For Phase 1, if real OAuth credentials are not ready, implement the structure and local development path without blocking the rest of the foundation. The backend should still have a clear `current_user` dependency boundary so later auth hardening does not require changing endpoint code.

## 4. Component Breakdown

- `apps/web`: Next.js frontend shell, app routes, base layout, environment config, API client helper, health/status page.
- `apps/api`: FastAPI app, settings, database session management, models, migrations, API routers, auth dependency boundary.
- PostgreSQL: local database for app data and future pgvector use.
- Redis: local cache/queue dependency for Phase 2 worker pipeline.
- Alembic: migration management for SQLModel tables.
- Better Auth: frontend-owned auth framework; Phase 1 establishes integration structure.
- Upload metadata model: records user-submitted replay/screenshot/summary metadata without full R2 implementation.
- Documentation: README updates and env examples so the project can be run from a fresh checkout.

## 5. Data Flow

### Health Check Flow

1. Browser loads the Next.js app.
2. Frontend calls FastAPI `/api/v1/health`.
3. FastAPI returns API status.
4. Frontend displays connected/disconnected state.

### Database Flow

1. Developer starts PostgreSQL via Docker Compose.
2. Backend reads `DATABASE_URL`.
3. Alembic applies migrations.
4. FastAPI uses SQLModel sessions for DB access.

### Auth Boundary Flow

1. User signs in through Better Auth in Next.js.
2. Next.js stores/maintains browser session.
3. Frontend/backend API call includes an auth token or local dev placeholder token.
4. FastAPI auth dependency validates identity.
5. FastAPI resolves or creates a backend `User` record.
6. Protected endpoints receive the backend user object.

### Upload Metadata Flow

1. Authenticated user opens upload page.
2. User submits file metadata or match summary metadata.
3. Frontend calls FastAPI upload endpoint.
4. FastAPI validates payload.
5. FastAPI creates an `Upload` row linked to the user.
6. FastAPI returns upload ID/status.

## 6. Interface Contracts

### Endpoint: `GET /api/v1/health`

- Input: none
- Output:

```json
{
  "status": "ok",
  "service": "deadlock-ai-api",
  "version": "0.1.0"
}
```

- Error cases:
  - `500` if the app cannot initialize.

### Endpoint: `GET /api/v1/ready`

- Input: none
- Output:

```json
{
  "status": "ok",
  "database": "ok",
  "redis": "ok"
}
```

- Error cases:
  - `503` if database or Redis connectivity fails.

### Endpoint: `GET /api/v1/me`

- Input:
  - Authorization header or local dev auth header.
- Output:

```json
{
  "id": "uuid",
  "email": "user@example.com",
  "display_name": "Connor",
  "avatar_url": null,
  "created_at": "2026-05-11T00:00:00Z"
}
```

- Error cases:
  - `401` if auth token/session is missing or invalid.

### Endpoint: `POST /api/v1/uploads`

- Input:

```json
{
  "kind": "replay",
  "filename": "match.dem",
  "content_type": "application/octet-stream",
  "size_bytes": 123456,
  "storage_key": "local/dev/or/r2/key",
  "summary_text": null
}
```

`kind` enum:

- `replay`
- `screenshot`
- `match_summary`

- Output:

```json
{
  "id": "uuid",
  "kind": "replay",
  "status": "created",
  "filename": "match.dem",
  "created_at": "2026-05-11T00:00:00Z"
}
```

- Error cases:
  - `400` for invalid payload.
  - `401` for unauthenticated request.
  - `413` if declared size exceeds configured limit.

### Initial Data Models

Phase 1 should add only foundation models that Phase 1 or Phase 2 will definitely read/write. Do not model matches, replay events, RAG data, heroes, patches, or AI result schemas yet.

#### Model Scope Rules

Add now:

- `User` — backend-owned user identity.
- `AuthIdentity` — external provider identity mapping.
- `Upload` — user-submitted input metadata.
- `AnalysisJob` — minimal placeholder for Phase 2 async processing.

Do not add in Phase 1:

- `Match`
- `AnalysisResult`
- `AnalysisEvent`
- `KnowledgeSource`
- `KnowledgeChunk`
- `Embedding`
- `Hero`
- `PatchVersion`

Those models should be designed in the phase that actually uses them, once the required fields are known.

#### User

Backend-owned user record. This should stay provider-agnostic.

Fields:

- `id: UUID` — primary key, generated by backend.
- `email: str | None` — nullable because some providers may not return an email.
- `display_name: str | None` — user-facing name from provider or local profile.
- `avatar_url: str | None` — optional provider avatar URL.
- `created_at: datetime` — timezone-aware timestamp.
- `updated_at: datetime` — timezone-aware timestamp.

Indexes / constraints:

- Primary key on `id`.
- Optional non-unique index on `email` for lookup/debugging.

Do not add yet:

- roles/permissions
- subscription/billing fields
- player MMR/rank fields
- personalized coaching memory

#### AuthIdentity

Maps an external OAuth/auth provider identity to one backend `User`.

Fields:

- `id: UUID` — primary key.
- `user_id: UUID` — foreign key to `users.id`, required.
- `provider: str` — provider name, initially `discord`, `github`, or `dev`.
- `provider_subject: str` — stable provider user ID / subject claim.
- `email: str | None` — provider email at time of linking, optional.
- `created_at: datetime` — timezone-aware timestamp.

Indexes / constraints:

- Unique constraint on `(provider, provider_subject)`.
- Index on `user_id`.

Do not add yet:

- OAuth access tokens
- refresh tokens
- provider profile JSON blobs

Reason: Better Auth/Next.js owns browser auth; the backend only needs stable identity mapping.

#### Upload

Represents an input artifact submitted by a user. In Phase 1 this stores metadata only; real R2 presigned upload flow can be added later.

Fields:

- `id: UUID` — primary key.
- `user_id: UUID` — foreign key to `users.id`, required.
- `kind: UploadKind` — enum: `replay`, `screenshot`, `match_summary`.
- `filename: str | None` — display filename only; never use as a filesystem path.
- `content_type: str | None` — client-declared MIME type, informational only.
- `size_bytes: int | None` — declared size; validate against configured limit when present.
- `storage_key: str | None` — object storage key or local placeholder; should be server-generated in production.
- `summary_text: str | None` — required only when `kind = match_summary`.
- `status: UploadStatus` — enum: `created`, `uploaded`, `failed`.
- `created_at: datetime` — timezone-aware timestamp.
- `updated_at: datetime` — timezone-aware timestamp.

Indexes / constraints:

- Index on `user_id`.
- Index on `(user_id, created_at)` for browsing uploads.
- Application validation:
  - `match_summary` requires `summary_text`.
  - `replay` / `screenshot` require `filename` and eventually `storage_key` once real uploads exist.
  - `size_bytes` must be non-negative and below configured maximum.

Do not add yet:

- parsed replay fields
- match duration
- hero names
- map/objective state
- screenshot OCR/vision outputs

Reason: those belong to replay parsing, vision, and AI analysis phases.

#### AnalysisJob

Minimal placeholder for Phase 2 async processing. Phase 1 creates the table so API and worker boundaries have a stable target later, but it does not implement queue behavior yet.

Fields:

- `id: UUID` — primary key.
- `user_id: UUID` — foreign key to `users.id`, required.
- `upload_id: UUID | None` — foreign key to `uploads.id`, nullable for future non-upload jobs.
- `status: AnalysisJobStatus` — enum: `queued`, `running`, `succeeded`, `failed`, `cancelled`.
- `progress: int` — integer `0` to `100`, default `0`.
- `error_message: str | None` — short safe error message for display/debugging.
- `created_at: datetime` — timezone-aware timestamp.
- `updated_at: datetime` — timezone-aware timestamp.
- `started_at: datetime | None` — set when worker starts in Phase 2.
- `completed_at: datetime | None` — set when worker finishes in Phase 2.

Indexes / constraints:

- Index on `user_id`.
- Index on `upload_id`.
- Index on `(user_id, created_at)` for job history.
- Application validation: `progress` must be between `0` and `100`.

Do not add yet:

- model names
- prompt versions
- workflow versions
- token/cost tracking
- structured AI output JSON
- retry schedule metadata

Reason: these fields should be added with the real Phase 2/3 worker and AI workflow design.

## 7. File Changes

- Create:
  - `apps/web/` — Next.js frontend application.
  - `apps/web/package.json` — frontend scripts/dependencies.
  - `apps/web/src/app/page.tsx` — initial landing/dashboard page.
  - `apps/web/src/app/layout.tsx` — root layout.
  - `apps/web/src/lib/api.ts` — frontend API helper.
  - `apps/web/.env.example` — frontend environment template.
  - `apps/api/` — FastAPI backend application.
  - `apps/api/pyproject.toml` — backend dependencies and scripts.
  - `apps/api/app/main.py` — FastAPI app entrypoint.
  - `apps/api/app/core/config.py` — settings management.
  - `apps/api/app/db/session.py` — database engine/session setup.
  - `apps/api/app/db/models.py` — initial SQLModel models.
  - `apps/api/app/api/v1/router.py` — API v1 router.
  - `apps/api/app/api/v1/health.py` — health/readiness endpoints.
  - `apps/api/app/api/v1/me.py` — current-user endpoint.
  - `apps/api/app/api/v1/uploads.py` — upload metadata endpoint.
  - `apps/api/app/auth/dependencies.py` — auth boundary/current-user dependency.
  - `apps/api/alembic/` — migration environment.
  - `apps/api/alembic.ini` — Alembic config.
  - `apps/api/tests/` — initial backend tests.
  - `infra/docker-compose.yml` — local Postgres and Redis.
  - `.gitignore` — Python/Node/env ignore rules if missing.
  - `.env.example` — root environment overview if useful.
  - `docs/phase-1-foundation-plan.md` — this plan.

- Modify:
  - `README.md` — update from placeholder to real project overview and local setup instructions.

- Delete:
  - None.

## 8. Implementation Phases

Use one branch for all Phase 1 foundation work:

- Branch: `feature/foundation-phase-1`
- Each subphase below should be implemented as one or more focused commits on that branch.
- Do not create separate branches for Phase 1A/1B/1C/etc. unless a subphase becomes large enough to need independent review.

### Phase 1A — Repository and Local Infrastructure
- Commits:
  - [ ] Add monorepo folders and root ignore/env files.
  - [ ] Add Docker Compose for Postgres and Redis.
  - [ ] Update README with local dependency startup instructions.
- Done when:
  - `docker compose -f infra/docker-compose.yml up` starts Postgres and Redis.
  - README explains the local foundation architecture.

### Phase 1B — FastAPI Backend Shell
- Commits:
  - [ ] Add FastAPI project with settings and app factory/entrypoint.
  - [ ] Add `/api/v1/health` and `/api/v1/ready` endpoints.
  - [ ] Add pytest smoke tests for health endpoints.
- Done when:
  - FastAPI runs locally.
  - Health endpoint returns `200`.
  - Readiness endpoint checks database and Redis.
  - Backend tests pass.

### Phase 1C — Database Models and Migrations
- Commits:
  - [ ] Add SQLModel session setup and shared timestamp/UUID conventions.
  - [ ] Add only the foundation models: `User`, `AuthIdentity`, `Upload`, and `AnalysisJob`.
  - [ ] Add Alembic configuration.
  - [ ] Add initial migration with fields, indexes, and constraints defined in [[#Initial Data Models|Initial Data Models]].
  - [ ] Add migration/model smoke tests.
- Explicitly out of scope:
  - `Match`, `AnalysisResult`, `AnalysisEvent`, `KnowledgeSource`, `KnowledgeChunk`, `Embedding`, `Hero`, and `PatchVersion`.
- Done when:
  - Alembic migration applies cleanly to local Postgres.
  - Only the four foundation tables are created.
  - Expected indexes/constraints exist.
  - Backend can open and close DB sessions successfully.

### Phase 1D — Auth Boundary and Upload Metadata API
- Commits:
  - [ ] Add FastAPI current-user dependency with local dev token strategy.
  - [ ] Add `/api/v1/me` endpoint.
  - [ ] Add upload metadata schema and `POST /api/v1/uploads` endpoint.
  - [ ] Add tests for auth-required endpoints and upload validation.
- Done when:
  - Protected endpoints reject missing auth.
  - Local dev auth resolves to a backend user.
  - Authenticated requests can create upload records.

### Phase 1E — Next.js Frontend Shell
- Commits:
  - [ ] Add Next.js App Router project with TypeScript and Tailwind.
  - [ ] Add base layout and landing/dashboard page.
  - [ ] Add API client helper and health status card.
  - [ ] Add simple upload metadata form.
- Done when:
  - Next.js runs locally.
  - Frontend can display API health status.
  - Upload metadata form can call the backend in local dev.

### Phase 1F — Better Auth Integration Skeleton
- Commits:
  - [ ] Add Better Auth dependencies/config structure.
  - [ ] Add Discord/GitHub provider env placeholders.
  - [ ] Add sign-in/sign-out UI placeholders.
  - [ ] Document local auth setup and unresolved production token validation details.
- Done when:
  - Auth integration points are in place.
  - OAuth credentials can be added through environment variables.
  - The auth boundary decision is documented clearly.

### Phase 1G — Foundation Review and Cleanup
- Commits:
  - [ ] Add final README setup verification steps.
  - [ ] Add minimal CI workflow if desired.
  - [ ] Run formatting, linting, type checks, and tests.
- Done when:
  - A fresh developer can follow README to run the app.
  - Frontend, backend, Postgres, and Redis all work together locally.
  - The project is ready for Phase 2 async pipeline work.

## 9. Testing Strategy

- Unit tests:
  - Backend settings loading.
  - Auth dependency behavior.
  - Upload payload validation.

- Integration tests:
  - FastAPI health/readiness endpoints.
  - Database session smoke test.
  - Upload creation with local dev auth.

- Frontend tests:
  - Defer comprehensive frontend testing until UI stabilizes.
  - At minimum, ensure TypeScript/build passes.

- Edge cases to cover:
  - Missing auth header.
  - Invalid upload kind.
  - Oversized upload metadata.
  - Missing filename/storage key for replay/screenshot upload.
  - Missing summary text for match summary upload.
  - Database unavailable readiness failure.
  - Redis unavailable readiness failure.

- How each phase will be validated before merging:
  - Phase 1A: Docker services start.
  - Phase 1B: backend tests pass.
  - Phase 1C: migrations apply and DB smoke checks pass.
  - Phase 1D: auth/upload tests pass.
  - Phase 1E: frontend runs and connects to backend.
  - Phase 1F: auth skeleton documented and env-driven.
  - Phase 1G: full local setup verified from README.

## 10. Security Implications

- Data exposed or processed:
  - User profile metadata.
  - OAuth provider identity metadata.
  - Upload metadata.
  - Future replay/screenshot data references.

- Access control:
  - Upload and user endpoints must require authentication.
  - Users must only access their own uploads/jobs.

- User-controlled inputs:
  - Upload filename.
  - Content type.
  - File size metadata.
  - Storage key.
  - Match summary text.

- Validation requirements:
  - Validate enum values.
  - Limit summary text size.
  - Limit declared upload size.
  - Do not trust content type from the client for security decisions.
  - Avoid path traversal by treating filenames as display metadata only.
  - Generate storage keys server-side later; do not trust arbitrary storage keys in production.

- Injection risks:
  - SQL injection risk is low if using SQLModel parameterized queries.
  - XSS risk exists if filenames/summary text are rendered unsafely; frontend must render as text, not raw HTML.
  - Path traversal risk exists if filenames are ever used as filesystem paths; avoid this.

- Sensitive data:
  - OAuth secrets and auth signing secrets must stay in env vars and never be committed.
  - Replay/screenshot files may contain user-identifying data and should be treated as private.

## 11. Risks & Tradeoffs

- Risk: Better Auth + FastAPI token validation boundary may require adjustment once real OAuth is configured.
  Mitigation: Keep auth behind a FastAPI dependency and document the contract clearly.

- Risk: Monorepo tooling can become messy if frontend/backend scripts are not documented.
  Mitigation: Keep independent app-level scripts and simple README commands first.

- Risk: Adding upload metadata before real R2 upload flow may require schema changes.
  Mitigation: Store generic `storage_key` and metadata now; add presigned upload fields later.

- Risk: Creating `AnalysisJob` in Phase 1 could overreach into Phase 2.
  Mitigation: Keep it as a minimal placeholder table only, with no worker behavior yet.

- Risk: Local dev auth shortcuts could leak into production.
  Mitigation: Gate local dev auth by environment and document that production must validate signed tokens only.

## 12. Open Questions

1. Package manager preference:
   - Frontend: npm, pnpm, or bun?
   - Backend: poetry, uv, or plain pip?
   - Proposed default: npm for frontend and uv or poetry for backend. Needs confirmation.

2. Auth implementation detail:
   - Should FastAPI validate a JWT issued by Next.js/Better Auth, or should Next.js proxy authenticated backend calls?
   - Proposed default: signed bearer token/session-derived JWT to FastAPI. Needs confirmation during Phase 1F.

3. App naming:
   - Repository is currently `deadlock-ai-coach`; product name is `Deadlock AI Platform`.
   - Proposed default: keep repo name, use product display name in UI/docs.

4. R2 in Phase 1:
   - Should Phase 1 include real presigned R2 upload URL generation, or only metadata and interface design?
   - Proposed default: metadata/interface only in Phase 1; real R2 presigned upload can be Phase 2 or 2A.

5. CI in Phase 1:
   - Should GitHub Actions be added immediately?
   - Proposed default: add only if it stays minimal: backend tests + frontend type/build check.

Open questions must be resolved or accepted as risks before implementation begins.
