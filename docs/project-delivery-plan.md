# Project Delivery Plan

This plan takes the current merged prototype through a usable match-ID/summary product, then through replay validation and product delivery. The existing API, web app, worker, database, AI, RAG, and parser code provide a starting point; they do not yet constitute a validated production service. See [the testing guide](testing-guide.md) and [Phase 6 readiness findings](phase-6-replay-intelligence-readiness-findings.md) for the current verification and replay gates.

## Sequence

1. Establish a reproducible baseline.
2. Make jobs reliable.
3. Deliver a real, authenticated match-ID/summary analysis path.
4. Validate replay parsing, then connect real file transport **only if the validation gate passes**.
5. Polish, evaluate, and deploy the proven flows.

Replay discovery (milestone 4A) can run alongside milestones 2–3. Do not make the match-ID product depend on replay extraction. Milestone 5's replay-specific work depends on milestone 4B; its match-ID work does not.

## 1. Reproducible baseline

**Goal:** Establish what actually works from a clean checkout before changing behavior.

- Fix the local configuration instructions: the README currently copies `.env.local` to the repository root, but API settings load `.env.local` relative to the API process's working directory. Specify the configuration files and launch directory for both apps.
- Install the prerequisites, start PostgreSQL/pgvector and Redis with `infra/docker-compose.yml`, and apply Alembic migrations.
- Run the backend suite and lint, frontend type-check and build, Java parser tests, and deterministic workflow evaluations using `docs/testing-guide.md`. Record failures rather than interpreting unrun checks as passes.
- Smoke-test two full paths with the API, worker, and web app running: **summary → job → persisted result → detail page** and **knowledge note → strategy search result**.
- Once reproducible locally, add CI checks for migrations, backend behavior, web build, and parser. Focus tests on user-visible behavior and state transitions, not mere presence of functions.

**Done when:** a fresh checkout follows one documented setup procedure; migrations and checks pass; both smoke paths complete through the browser. Primary files: `README.md`, `.env.example`, `apps/web/.env.example`, `apps/api/app/core/config.py`, `docs/testing-guide.md`.

## 2. Reliable job processing

**Goal:** Every submitted job reaches a durable, explainable state.

- Ensure failed `AnalysisJob`, `WorkflowRun`, and `WorkflowStep` updates commit even when workflow execution raises. Currently the runner flushes failure state and re-raises inside a database context that rolls back on an exception; verify this failure mode in an integration test before changing the transaction boundary.
- Eliminate the enqueue-before-commit race: do not expose a task to Arq until its job row is visible. Provide a recoverable state and reconciliation path when a committed job cannot be enqueued or a worker is interrupted.
- Define duplicate-delivery/idempotency behavior, retryable versus terminal errors, attempt counts, and cancellation handling. Ensure retries cannot create multiple results for one job.
- Reconcile the worker's 60-second task timeout with parser and AI operation timeouts, including cancellation and subprocess cleanup.
- Exercise success, worker failure, enqueue failure, duplicate delivery, and interrupted execution against PostgreSQL and Redis. Check both stored state and the API response.

**Done when:** no job stays silently queued or loses its failure record; retries and duplicate deliveries are safe; the API reports a durable terminal outcome. Primary files: `apps/api/app/services/analysis_jobs.py`, `app/db/session.py`, `app/queue/`, `app/workers/`, `app/workflows/analysis/`, related models and tests.

## 3. Usable match-ID and summary analysis

**Goal:** Deliver value without claiming unsupported replay evidence. Prefer match-ID analysis as the primary path; keep manually entered summaries available when no match ID is known.

- Verify a known match ID against the external Deadlock API. Persist normalized metadata and show source availability, cache freshness, and clear warnings when data is unavailable.
- Change the dashboard from a generic “fake analysis” metadata form to explicit match-ID and summary inputs. Render the actual source, job status, structured result, and failure/warning information; let users revisit prior analyses.
- Use the mock AI provider to test the structured-result contract, then test a configured real provider against available match/summary data. Keep deterministic fake output explicitly labelled as fake; do not present model assertions as verified replay facts.
- Connect Better Auth browser identity to FastAPI: select one credential-validation contract, validate credentials server-side, map provider identity to backend users, and remove the fixed `X-Dev-User-Id` header from normal frontend requests. Preserve a bypass only for explicitly local development.
- Test valid, invalid, and expired credentials and isolation between two users for uploads, jobs, results, and knowledge. Smoke-test signed-in submission → completed analysis → revisit in the browser.

**Done when:** a signed-in user submits a match ID or summary and sees a source-labelled, persisted structured result; another user cannot access it; no default fake result is represented as real coaching. Primary files: `apps/web/src/app/page.tsx`, `apps/web/src/lib/api.ts`, `apps/web/src/auth/`, `apps/api/app/auth/dependencies.py`, and the Deadlock API/AI services.

## 4. Replay validation, then real file transport

**Goal:** Build replay features only from observed `.dem` data. Follow the [Phase 6 validation gate](phase-6-replay-intelligence-validation-gate-plan.md).

### Gate 4A — local extraction proof

- Obtain one or more real local Deadlock `.dem` samples; never commit the samples or sensitive parser output.
- Wire actual Clarity processors/listeners in `apps/replay-parser/`. Discover and document accessible match fields, messages, properties, and events. Verify emitted values against a real replay, rather than accepting schema-valid placeholder output.
- Keep the normalized artifact contract and Python subprocess wrapper working; add extraction tests for meaningful fields and missing-data boundaries.
- Replace `Files.readAllBytes` in file sampling/hashing with bounded or streaming reads so large replays do not require whole-file memory.
- Record the commands, observed categories, limits, and decision in `docs/phase-6-replay-intelligence-readiness-findings.md`: proceed with Clarity, change parser strategy, or postpone replay intelligence.

**Gate 4A passes when:** at least one real replay yields a verified replay-derived match field or meaningful event category beyond file metadata. If it fails, stop planning Clarity-dependent timelines and investigate an alternative parser.

### Gate 4B — user-owned replay path, conditional on Gate 4A

- Implement actual replay upload to private object storage, ownership and size checks, worker retrieval/staging, and cleanup. Do not treat a caller-supplied `storage_key` or shared local sample path as proof of file upload.
- Persist genuinely extracted artifacts and expose parser errors and unsupported replay data clearly. Use confirmed replay events to enrich context and build a timeline/coaching slice one event category at a time.
- Smoke-test **user uploads replay → worker retrieves that user's bytes → parser extracts verified data → artifact/result appears only for that user**, plus missing/corrupt replay and parser failure.

**Done when:** an uploaded replay produces a user-owned artifact with verified replay-derived match/event data, or the readiness findings explicitly explain why the replay path is postponed. Primary files: `apps/replay-parser/`, `apps/api/app/services/replay_parser.py`, `apps/api/app/workflows/analysis/nodes/parse_replay.py`, upload/storage and artifact code.

## 5. Product polish, quality, and deployment

**Goal:** Improve and operate flows proven in milestones 1–4; do not polish placeholders.

- Make the dashboard, history, and detail pages coherent: clear source provenance, progress, retries/failures, and warnings. Build replay charts or timelines only after Gate 4B supplies real events.
- Seed and evaluate a useful strategy-knowledge corpus. Check retrieval relevance and citation correctness; keep embeddings from incompatible provider/model spaces separate. Move ranking into PostgreSQL/pgvector when data volume warrants it instead of loading all candidate vectors into Python.
- Add selected matchup/build analytics only for demonstrated coaching use cases, with patch awareness and graceful handling of missing or stale external data.
- Prepare deployment configuration, migrations, secrets, health checks, structured logs, and monitoring. Validate a production-like sign-in → analysis → revisit flow and recovery from external API/provider outages.

**Done when:** supported flows work for real users in a deployed environment, output quality has evidence-based checks, and failures are observable and recoverable. Match-ID polish can proceed independently of replay-specific polish.

## Release gates

- **Usable match-ID/summary release:** milestones 1–3 complete, plus the relevant match-ID/UI/deployment portions of milestone 5.
- **Replay-capable release:** Gate 4A passes, Gate 4B completes, and replay-specific milestone 5 work is verified. A schema-valid placeholder replay artifact does not satisfy this gate.
