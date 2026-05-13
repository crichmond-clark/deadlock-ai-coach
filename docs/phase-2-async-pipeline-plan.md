# Phase 2 Async Pipeline Plan

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

Phase 1 proves the full-stack shell: Next.js can call FastAPI, FastAPI can persist users/uploads/jobs, Redis is available locally, and upload metadata can be created. Phase 2 must prove the core product architecture: user input should create an analysis job, the job should be processed asynchronously by an Arq worker, progress should be visible to the frontend, and a persisted structured result should be browsable after completion.

This phase intentionally avoids real AI, real replay parsing, and real file processing. The goal is to make the asynchronous pipeline reliable before expensive or uncertain analysis logic is added.

## 2. Goals & Non-Goals

- Goals:
  - Add a Redis/Arq queue client and worker entrypoint.
  - Add an API endpoint that creates an `AnalysisJob` for an authenticated user's upload and enqueues worker processing.
  - Add deterministic fake analysis processing that exercises real job state transitions.
  - Persist a structured fake analysis result in PostgreSQL.
  - Add job status and result APIs for polling and history browsing.
  - Update the frontend upload flow so creating an upload can start analysis.
  - Add a frontend analysis detail page that polls job status and displays the fake result.
  - Add a simple analysis history/dashboard list so old analyses can be browsed.
  - Add tests for job creation, authorization, queue enqueue behavior, worker state transitions, and frontend type/build checks.
  - Document how to run the API, worker, Redis/Postgres, and frontend locally.

- Non-Goals:
  - Real AI analysis.
  - Instructor/Pydantic AI output schemas beyond the fake result schema needed for Phase 2.
  - LangGraph workflows.
  - Clarity replay parsing.
  - Cloudflare R2 presigned upload implementation.
  - Actual file upload streaming or binary processing.
  - Screenshot vision/OCR.
  - RAG ingestion, embeddings, or pgvector queries.
  - Production deployment automation.
  - SSE/WebSocket streaming; Phase 2 uses polling.
  - Full production Better Auth token validation; Phase 2 continues using the existing FastAPI `current_user` boundary and local dev auth path unless auth hardening is approved as a separate prerequisite.

## 3. Proposed Architecture

Use the existing Phase 1 foundation and add one minimal async processing layer:

```txt
Browser / Next.js
  ↓
POST /api/v1/uploads
  ↓
POST /api/v1/analysis-jobs
  ↓
FastAPI creates AnalysisJob(status=queued)
  ↓
FastAPI enqueues Arq task in Redis
  ↓
Arq worker picks up process_analysis_job(job_id)
  ↓
Worker updates job running/progress
  ↓
Worker writes AnalysisResult(payload=structured fake result)
  ↓
Worker marks job succeeded/failed
  ↓
Frontend polls GET /api/v1/analysis-jobs/{job_id}
  ↓
Frontend displays status/result and history
```

Key decisions:

- Keep the queue implementation inside `apps/api` for now. There is no separate worker package yet; Arq imports the same app settings, models, and service functions.
- Keep fake analysis deterministic and cheap. It should depend only on the upload metadata/summary text and never call external AI providers.
- Add only one new result table now: `analysis_results`. Do not add matches, events, heroes, RAG tables, or real AI metadata until the phases that need them.
- Keep status polling simple. SSE can be added later after the job lifecycle is proven.
- Put database/queue orchestration in service modules so routes and worker functions stay thin.
- Keep user authorization in the API layer. Worker functions operate on trusted job IDs created by the API.

## 4. Component Breakdown

- `apps/api/app/api/v1/analysis_jobs.py`
  - Owns HTTP contracts for creating jobs, listing jobs, and fetching job status.
  - Verifies the current user owns the upload/job.
  - Delegates queue and DB operations to services.

- `apps/api/app/api/v1/analysis_results.py`
  - Owns HTTP contract for fetching a completed result by job ID or result ID.
  - Verifies user ownership through the job/result relationship.

- `apps/api/app/db/models/analysis_job.py`
  - Extends the existing Phase 1 job model with queue traceability fields.
  - Keeps lifecycle status/progress timestamps.

- `apps/api/app/db/models/analysis_result.py`
  - Stores the Phase 2 structured fake result.
  - Links one result to one job and the owning user.
  - Uses JSONB for the fake structured payload so Phase 3 can replace/extend schemas without over-modeling now.

- `apps/api/app/services/analysis_jobs.py`
  - Creates jobs.
  - Enqueues Arq tasks.
  - Reads/list jobs for the authenticated user.
  - Centralizes job lifecycle transitions.

- `apps/api/app/services/fake_analysis.py`
  - Builds deterministic fake result payloads from upload metadata.
  - Contains no database or queue code.

- `apps/api/app/queue/client.py`
  - Wraps Arq Redis pool creation and enqueue calls.
  - Keeps routes/services from depending directly on Arq details.

- `apps/api/app/workers/analysis.py`
  - Contains the Arq task function `process_analysis_job(ctx, job_id)`.
  - Updates job status and persists the fake result.
  - Handles failures by storing safe error messages.

- `apps/api/app/workers/worker.py`
  - Defines Arq `WorkerSettings` and Redis settings.
  - Provides the worker import path for the CLI command.

- `apps/web/src/lib/api.ts`
  - Adds typed functions for creating/listing/fetching analysis jobs and results.

- `apps/web/src/app/page.tsx`
  - Updates the upload flow to enqueue an analysis job after upload creation.
  - Shows recent analysis jobs and links to detail pages.

- `apps/web/src/app/analyses/[jobId]/page.tsx`
  - Polls job status until terminal state.
  - Displays progress, errors, and the persisted fake result.

## 5. Data Flow

1. User opens the dashboard.
2. Frontend loads existing uploads and recent analysis jobs for the current user.
3. User submits upload metadata or a match summary.
4. Frontend calls `POST /api/v1/uploads`.
5. FastAPI validates the payload and creates an `Upload` row.
6. Frontend calls `POST /api/v1/analysis-jobs` with the new `upload_id`.
7. FastAPI verifies the upload belongs to the current user.
8. FastAPI creates an `AnalysisJob` with:
   - `status = queued`
   - `progress = 0`
   - `upload_id = <upload>`
   - `user_id = <current user>`
9. FastAPI enqueues `process_analysis_job` through Arq and stores the returned queue job ID.
10. Frontend navigates to `/analyses/{job_id}` or shows an inline link.
11. Analysis detail page polls `GET /api/v1/analysis-jobs/{job_id}` every 2 seconds while status is `queued` or `running`.
12. Worker picks up the task, loads the job and upload, and transitions the job to:
    - `running`, `progress = 10`, `started_at = now()`
    - intermediate progress values while fake analysis is generated
    - `succeeded`, `progress = 100`, `completed_at = now()` on success
    - `failed`, `error_message = <safe message>`, `completed_at = now()` on failure
13. Worker inserts one `AnalysisResult` for the job.
14. Frontend sees `status = succeeded` and displays the result payload.
15. User can revisit old jobs from the dashboard/history list.

## 6. Interface Contracts

### Data Model: `AnalysisJob` additions

Modify the existing `analysis_jobs` table:

- `queue_job_id: str | None` — Arq job ID returned by Redis enqueue.
- `attempt_count: int` — worker attempt count, default `0`.
- Existing fields retained:
  - `id`
  - `user_id`
  - `upload_id`
  - `status`
  - `progress`
  - `error_message`
  - `started_at`
  - `completed_at`
  - `created_at`
  - `updated_at`

Constraints / validation:

- `progress` must remain between `0` and `100`.
- Jobs belong to exactly one backend user.
- A job may reference one upload.
- Status values remain: `queued`, `running`, `succeeded`, `failed`, `cancelled`.

### Data Model: `AnalysisResult`

Create `analysis_results`:

- `id: UUID` — primary key.
- `user_id: UUID` — foreign key to `users.id`, required.
- `job_id: UUID` — foreign key to `analysis_jobs.id`, required and unique.
- `upload_id: UUID | None` — foreign key to `uploads.id`, nullable.
- `result_kind: str` — default `fake_analysis`.
- `schema_version: str` — default `fake-analysis-v1`.
- `title: str` — short display title.
- `summary: str` — short text summary.
- `payload: JSONB` — structured fake result.
- `created_at: datetime`.
- `updated_at: datetime`.

Indexes / constraints:

- Unique constraint on `job_id`.
- Index on `user_id`.
- Index on `(user_id, created_at)`.
- Optional index on `upload_id`.

Phase 2 fake payload shape:

```json
{
  "summary": "Mock coaching summary based on the submitted input.",
  "highlights": ["You created a replay analysis request."],
  "improvement_areas": ["Review laning deaths", "Track objective timing"],
  "recommended_focus": ["Last hitting", "Map awareness"],
  "next_steps": ["Upload a real replay once parser support lands"],
  "source": {
    "upload_id": "uuid",
    "upload_kind": "replay",
    "filename": "match.dem"
  }
}
```

### Endpoint: `POST /api/v1/analysis-jobs`

Create and enqueue an analysis job for an upload.

Input:

```json
{
  "upload_id": "uuid"
}
```

Output `201`:

```json
{
  "id": "uuid",
  "upload_id": "uuid",
  "status": "queued",
  "progress": 0,
  "queue_job_id": "arq-job-id-or-null",
  "error_message": null,
  "created_at": "2026-05-13T00:00:00Z",
  "started_at": null,
  "completed_at": null,
  "result": null
}
```

Error cases:

- `400` if `upload_id` is malformed.
- `401` if unauthenticated.
- `404` if the upload does not exist or does not belong to the current user.
- `409` if the upload already has a queued, running, or succeeded job.
- `503` if Redis enqueue fails; the job should be marked `failed` with a safe error message if it was already created.

### Endpoint: `GET /api/v1/analysis-jobs`

List recent jobs for the authenticated user.

Query params:

- `limit: int | None` — default `20`, max `50`.
- `offset: int | None` — default `0`.

Output `200`:

```json
{
  "jobs": [
    {
      "id": "uuid",
      "upload_id": "uuid",
      "status": "succeeded",
      "progress": 100,
      "queue_job_id": "arq-job-id",
      "error_message": null,
      "created_at": "2026-05-13T00:00:00Z",
      "started_at": "2026-05-13T00:00:01Z",
      "completed_at": "2026-05-13T00:00:05Z",
      "result": {
        "id": "uuid",
        "title": "Replay analysis ready",
        "summary": "Mock coaching summary...",
        "schema_version": "fake-analysis-v1"
      }
    }
  ],
  "total": 1
}
```

Error cases:

- `401` if unauthenticated.
- `400` if pagination params are invalid.

### Endpoint: `GET /api/v1/analysis-jobs/{job_id}`

Fetch status and optional result summary for one job.

Output `200`:

```json
{
  "id": "uuid",
  "upload_id": "uuid",
  "status": "running",
  "progress": 60,
  "queue_job_id": "arq-job-id",
  "error_message": null,
  "created_at": "2026-05-13T00:00:00Z",
  "started_at": "2026-05-13T00:00:01Z",
  "completed_at": null,
  "result": null
}
```

Error cases:

- `401` if unauthenticated.
- `404` if the job does not exist or does not belong to the current user.

### Endpoint: `GET /api/v1/analysis-jobs/{job_id}/result`

Fetch the completed structured result for one job.

Output `200`:

```json
{
  "id": "uuid",
  "job_id": "uuid",
  "upload_id": "uuid",
  "result_kind": "fake_analysis",
  "schema_version": "fake-analysis-v1",
  "title": "Replay analysis ready",
  "summary": "Mock coaching summary based on the submitted input.",
  "payload": {
    "summary": "Mock coaching summary based on the submitted input.",
    "highlights": [],
    "improvement_areas": [],
    "recommended_focus": [],
    "next_steps": [],
    "source": {
      "upload_id": "uuid",
      "upload_kind": "replay",
      "filename": "match.dem"
    }
  },
  "created_at": "2026-05-13T00:00:05Z"
}
```

Error cases:

- `401` if unauthenticated.
- `404` if the job/result does not exist or does not belong to the current user.
- `409` if the job exists but is not complete yet.

### Worker Function: `process_analysis_job(ctx, job_id: str)`

Input:

- `ctx` — Arq context.
- `job_id` — UUID string for `analysis_jobs.id`.

Behavior:

- Load the job and upload.
- Skip if the job is already `succeeded` and has a result.
- Mark `running`, increment `attempt_count`, set `started_at` if missing.
- Generate deterministic fake result payload.
- Insert `AnalysisResult`.
- Mark `succeeded`, `progress = 100`, set `completed_at`.
- On error, mark `failed`, store safe `error_message`, set `completed_at`, then re-raise only when useful for Arq retry logging.

## 7. File Changes

- Create:
  - `docs/phase-2-async-pipeline-plan.md` — this plan.
  - `apps/api/app/api/v1/analysis_jobs.py` — job creation/status/history API.
  - `apps/api/app/db/models/analysis_result.py` — persisted fake result model.
  - `apps/api/app/services/__init__.py` — service package marker.
  - `apps/api/app/services/analysis_jobs.py` — job orchestration and state transition helpers.
  - `apps/api/app/services/fake_analysis.py` — deterministic fake result builder.
  - `apps/api/app/queue/__init__.py` — queue package marker.
  - `apps/api/app/queue/client.py` — Arq Redis pool/enqueue helper.
  - `apps/api/app/workers/__init__.py` — worker package marker.
  - `apps/api/app/workers/analysis.py` — Arq task implementation.
  - `apps/api/app/workers/worker.py` — Arq worker settings/entrypoint.
  - `apps/api/tests/test_analysis_jobs.py` — API and worker tests for Phase 2 behavior.
  - `apps/web/src/app/analyses/[jobId]/page.tsx` — analysis status/result page.

- Modify:
  - `apps/api/app/api/v1/router.py` — include analysis job routes.
  - `apps/api/app/db/models/__init__.py` — export `AnalysisResult`.
  - `apps/api/app/db/models/analysis_job.py` — add queue fields and result relationship.
  - `apps/api/alembic/versions/*` — add migration for job fields and `analysis_results`.
  - `apps/api/app/core/config.py` — add queue settings only if needed beyond existing `redis_url`.
  - `apps/api/pyproject.toml` — add any test-only dependencies only if strictly required; Arq is already present.
  - `apps/web/src/lib/api.ts` — add analysis job/result request types and functions.
  - `apps/web/src/app/page.tsx` — enqueue analysis after upload creation and show recent jobs/history.
  - `README.md` — add Phase 2 local worker command and verification flow.
  - `.env.example` — add queue/worker env vars only if defaults are not enough.

- Delete:
  - None.

## 8. Implementation Phases

Use one branch for all Phase 2 async pipeline work:

- Branch: `feature/async-pipeline-phase-2`
- Each subphase below should be implemented as one or more focused commits on that branch.
- Do not create separate branches for Phase 2A/2B/2C unless explicitly requested.

### Phase 2A — Backend job API and result persistence

- Branch: `feature/async-pipeline-phase-2`
- Commits:
  - [ ] Add `AnalysisResult` model and Alembic migration.
  - [ ] Add `queue_job_id` and `attempt_count` fields to `AnalysisJob` with migration.
  - [ ] Add Pydantic response/request contracts for analysis jobs and results.
  - [ ] Add `POST /api/v1/analysis-jobs`, `GET /api/v1/analysis-jobs`, `GET /api/v1/analysis-jobs/{job_id}`, and `GET /api/v1/analysis-jobs/{job_id}/result` without worker execution yet.
  - [ ] Add API tests for auth, ownership, duplicate job prevention, and pagination basics.
- Done when:
  - Migrations apply cleanly.
  - Existing upload/me/health tests still pass.
  - Authenticated local dev user can create a queued job for their upload.
  - Unauthenticated and cross-user access is rejected.

### Phase 2B — Arq queue client and fake worker

- Branch: `feature/async-pipeline-phase-2`
- Commits:
  - [ ] Add Arq queue client wrapper using existing `redis_url`.
  - [ ] Wire job creation to enqueue `process_analysis_job` and store Arq queue job ID.
  - [ ] Add fake analysis payload builder.
  - [ ] Add Arq worker settings and `process_analysis_job` task.
  - [ ] Add worker tests that call the task directly against the test database.
  - [ ] Add Redis enqueue integration smoke test if local Redis is available.
- Done when:
  - Running the API and worker locally lets a created job progress from `queued` → `running` → `succeeded`.
  - Worker persists exactly one `AnalysisResult` per successful job.
  - Worker failure marks the job `failed` with a safe error message.
  - Re-running the worker task for a succeeded job is idempotent.

### Phase 2C — Frontend polling, result display, and history

- Branch: `feature/async-pipeline-phase-2`
- Commits:
  - [ ] Add frontend API helpers/types for analysis jobs and results.
  - [ ] Update the upload form flow to create an analysis job after upload creation.
  - [ ] Add recent analysis jobs/history list to the dashboard.
  - [ ] Add `/analyses/[jobId]` page that polls status while queued/running.
  - [ ] Render progress, failed state, and structured fake result payload.
- Done when:
  - User can submit input from the dashboard and land on or navigate to an analysis status page.
  - The page updates without refresh as the worker progresses.
  - Succeeded jobs show the persisted fake result.
  - Old jobs can be opened from the dashboard/history list.
  - `npm run type-check`, `npm run lint`, and `npm run build` pass.

### Phase 2D — Documentation, cleanup, and verification

- Branch: `feature/async-pipeline-phase-2`
- Commits:
  - [ ] Update README with local commands for API, worker, frontend, migrations, and tests.
  - [ ] Add troubleshooting notes for Redis/worker not running.
  - [ ] Run backend lint/tests and frontend lint/type/build checks.
  - [ ] Manually verify the full local flow with Docker Postgres/Redis, FastAPI, Arq worker, and Next.js.
- Done when:
  - Full backend test suite passes.
  - Backend ruff check passes.
  - Frontend lint/type/build checks pass.
  - Manual end-to-end flow works:
    - Create upload.
    - Create/enqueue job.
    - Worker processes fake analysis.
    - Frontend polling shows status progression.
    - Result page displays persisted output.

## 9. Testing Strategy

- Unit tests:
  - Fake analysis payload builder returns deterministic payloads for replay, screenshot, and match summary uploads.
  - Job transition helper clamps/validates progress and terminal statuses.
  - Safe error message helper does not expose stack traces or secrets.

- Backend API tests:
  - `POST /analysis-jobs` requires auth.
  - Job creation requires an upload owned by the current user.
  - Duplicate active/succeeded jobs for one upload return `409`.
  - Job list returns only the current user's jobs.
  - Job detail rejects cross-user access.
  - Result endpoint returns `409` before completion and `200` after result exists.
  - Redis enqueue failure returns `503` and leaves a safe failed job state if a job row was created.

- Worker tests:
  - Directly call `process_analysis_job` for a queued job.
  - Assert status transitions to `succeeded` and progress reaches `100`.
  - Assert `AnalysisResult` is created once.
  - Assert idempotent re-run does not create duplicate results.
  - Assert missing job or invalid upload failure is handled safely.

- Frontend checks:
  - `npm run lint`.
  - `npm run type-check`.
  - `npm run build`.
  - Manual browser test for upload → job → poll → result.

- Local integration verification:
  - Start infrastructure:

    ```bash
    docker compose -f infra/docker-compose.yml up -d
    ```

  - Apply migrations:

    ```bash
    cd apps/api
    uv run alembic upgrade head
    ```

  - Run API:

    ```bash
    uv run fastapi dev --port 8000
    ```

  - Run worker in another terminal:

    ```bash
    cd apps/api
    uv run arq app.workers.worker.WorkerSettings
    ```

  - Run frontend:

    ```bash
    cd apps/web
    npm run dev
    ```

## 10. Security Implications

- Data exposed or processed:
  - Upload metadata, optional match summary text, job statuses, and fake analysis results.
  - No binary file contents are processed in Phase 2.
  - No AI provider credentials or OAuth tokens are handled by the worker.

- Authentication/authorization:
  - All analysis job and result endpoints must use the existing FastAPI `resolve_current_user` dependency.
  - Jobs/results must be filtered by `current_user.id`.
  - `404` should be returned for cross-user job/result access to avoid disclosing object existence.

- User-controlled inputs:
  - `upload_id` in job creation.
  - Upload metadata and `summary_text` from existing upload endpoint.
  - Pagination query params.
  - All IDs must be validated as UUIDs.
  - Summary/result display in React must render as text, not raw HTML.

- Injection/path risks:
  - Worker must not read local paths from `filename` or `storage_key`.
  - Fake analysis must not execute shell commands.
  - SQL access should remain through SQLAlchemy/SQLModel query builders.

- Sensitive data:
  - Error messages persisted to `analysis_jobs.error_message` must be safe and short.
  - Do not store stack traces, Redis URLs, database URLs, secrets, provider tokens, or environment values in job errors/results.

- Queue security:
  - Redis should remain local/private in development.
  - Worker should accept only job IDs created by the authenticated API flow.
  - Worker must verify the job exists before processing.

## 11. Risks & Tradeoffs

- Risk: Database and Redis enqueue are not atomic, so a job row can exist even if enqueue fails.
  Mitigation: If enqueue fails, mark the job `failed`, store a safe error message, and return `503`. Keep the state visible to the user/developer.

- Risk: Polling is less efficient than SSE/WebSockets.
  Mitigation: Use short polling only while jobs are `queued`/`running`; stop polling on terminal states. Add SSE later if needed.

- Risk: JSONB fake payload could become a dumping ground for real AI output.
  Mitigation: Limit Phase 2 schema to `fake-analysis-v1`. Phase 3 must define real structured AI schemas explicitly before adding real AI results.

- Risk: Production auth validation remains unresolved.
  Mitigation: Treat Phase 2 as local/dev proof of async architecture using the established auth boundary. Do not deploy as production-authenticated functionality until Better Auth token validation is completed.

- Risk: Worker tests can become flaky if they rely on real Redis timing.
  Mitigation: Test the worker task directly for state transitions and keep Redis enqueue coverage as a small integration smoke test.

- Risk: Long-running worker tasks can hold stale DB sessions.
  Mitigation: Open short-lived sessions inside each worker phase/update. Do not keep sessions across sleeps or expensive work.

- Risk: Duplicate results if a task is retried after partial completion.
  Mitigation: Add a unique constraint on `analysis_results.job_id` and make the worker idempotent by checking for an existing successful result before insert.

## 12. Open Questions

- Should real Better Auth token validation be finished before Phase 2?
  - Decision: No, not for this Phase 2 async pipeline branch. The accepted risk is documented above. Phase 2 uses the existing FastAPI auth boundary and local dev user path.

- Should job creation be automatic inside `POST /uploads` or explicit via `POST /analysis-jobs`?
  - Decision: Use explicit `POST /analysis-jobs`. This keeps upload metadata creation separate from analysis execution and makes retries/re-runs easier to reason about later.

- Should duplicate analysis jobs be allowed for the same upload?
  - Decision: Not in Phase 2. Return `409` if an upload already has a queued, running, or succeeded job. Add explicit re-run support later if needed.

- Should Phase 2 add `analysis_events` for detailed status history?
  - Decision: No. The existing `AnalysisJob` lifecycle fields plus persisted `AnalysisResult` are enough to prove the pipeline. Add event history later only when richer observability or timelines require it.
