# Phase 2.5 Clarity Replay Parser Spike Plan

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

Phase 2 proved the app can create uploads, enqueue asynchronous analysis jobs, process them with an Arq worker, persist a structured fake result, and show that result in the frontend. The next product risk is replay parsing: before building AI workflows or rich replay intelligence, we need to know whether `skadistats/clarity` can parse current Deadlock replay files well enough for our coaching pipeline.

This phase is a spike, not a polished replay intelligence product. It should answer:

1. Can a small Java CLI using Clarity parse one real Deadlock replay locally?
2. What useful fields/events can we reliably extract today?
3. Can the Python worker call the parser through a stable app-owned JSON boundary?
4. Can parser failures be captured cleanly without breaking the existing async job flow?
5. What normalized artifact shape should later AI/replay phases consume?

The important architectural principle is isolation: the FastAPI/Python app must never depend on Clarity-specific Java objects, protobuf internals, or raw parser implementation details. The parser boundary should be a CLI that reads a replay path and writes normalized JSON.

## 2. Goals & Non-Goals

- Goals:
  - Add a small Java/Gradle replay parser CLI under the repo.
  - Use Clarity as the first parser candidate.
  - Parse a local Deadlock replay file from a CLI command.
  - Emit deterministic normalized JSON owned by this project.
  - Include parser metadata, parser version, parse duration, and extraction warnings.
  - Extract a minimal useful subset:
    - match/replay metadata where available;
    - duration/tick information where available;
    - players/heroes/entities where available;
    - basic timeline events where available;
    - raw capability summary showing what Clarity exposed.
  - Add Python service code that invokes the parser CLI via subprocess with timeout and safe error handling.
  - Persist parse artifacts in PostgreSQL as JSONB.
  - Update the existing Phase 2 worker so replay uploads can attempt parser execution before falling back to fake analysis.
  - Add an API endpoint to retrieve a parse artifact for an authorized user's analysis job.
  - Add minimal frontend display of parser status/artifact summary on the analysis detail page.
  - Add tests around normalization, subprocess handling, API authorization, and worker behavior.
  - Document local Java/Gradle setup and how to run the parser spike against a real replay file.

- Non-Goals:
  - Real coaching from replay data.
  - Rich match timeline UX.
  - Full hero/item/economy/objective modeling.
  - Full binary replay upload streaming.
  - Cloudflare R2 implementation.
  - Production containerization of the Java parser.
  - Multi-parser abstraction beyond keeping the JSON boundary clean.
  - Parsing every Clarity data stream.
  - Persisting every entity/event as relational rows.
  - AI analysis, Instructor schemas, prompt engineering, or model calls.
  - SSE/WebSocket streaming.
  - Production Better Auth token validation.

## 3. Proposed Architecture

Add a separate Java CLI package for replay parsing and keep Python integration at the process boundary.

```txt
Local replay file
  ↓
apps/replay-parser CLI
  ↓
Clarity reads replay
  ↓
Project-owned normalized JSON printed to stdout or written to --output
  ↓
Python worker subprocess wrapper validates JSON
  ↓
ReplayParseArtifact persisted in Postgres JSONB
  ↓
AnalysisResult payload includes parse summary/source metadata
  ↓
Frontend analysis page displays parser summary and warnings
```

Key decisions:

- Create `apps/replay-parser/` rather than mixing Java into `apps/api/`.
  - The parser has different tooling and runtime requirements.
  - It can later become its own Docker build stage/container without changing app contracts.

- Use a CLI boundary first.
  - Subprocess invocation is simple, observable, and enough for the spike.
  - Avoids JVM embedding in Python.
  - Keeps parser failures containable.

- Store the normalized artifact as JSONB.
  - We do not yet know the stable relational model for replay data.
  - JSONB lets us inspect real outputs and evolve the schema during later replay intelligence phases.

- Add one lightweight persistence table: `replay_parse_artifacts`.
  - Do not add matches, match events, heroes, builds, or full timeline relational tables yet.
  - This table stores spike output and metadata linked to the existing upload/job/user.

- Keep Phase 2 fake analysis working.
  - Match summary and screenshot uploads should continue using fake analysis.
  - Replay uploads should parse when a local replay path is available, then create a fake/parse-aware result summary.
  - Parser failure should mark the job failed for real replay jobs, with safe error text and persisted failure metadata when possible.

- Local replay path is a developer-only spike input.
  - Because binary upload/R2 is not implemented, Phase 2.5 needs a local way to point the worker at a replay file.
  - Use an environment variable such as `LOCAL_REPLAY_SAMPLE_PATH` for manual verification and/or allow `Upload.storage_key` values prefixed with `local://` in local dev only.
  - Do not allow arbitrary API users to submit server filesystem paths.

## 4. Component Breakdown

- `apps/replay-parser/`
  - Java/Gradle CLI package that owns Clarity dependency and parsing logic.
  - Reads replay file path from `--input`.
  - Writes normalized JSON to stdout or `--output`.
  - Exits non-zero with safe stderr on parse failures.

- `apps/replay-parser/src/main/java/.../ReplayParserCli.java`
  - CLI argument parsing and process exit behavior.
  - Validates input file exists and is readable.
  - Delegates parsing to a parser service.

- `apps/replay-parser/src/main/java/.../ClarityReplayParser.java`
  - Clarity integration.
  - Collects available metadata/events.
  - Does not decide the app's final persistence model.

- `apps/replay-parser/src/main/java/.../NormalizedReplayArtifact.java`
  - Jackson-serializable DTOs for normalized output.
  - Defines a schema version such as `deadlock-replay-parse-v1`.

- `apps/api/app/db/models/replay_parse_artifact.py`
  - SQLModel table storing parser output and metadata.
  - Linked to `users`, `uploads`, and optionally `analysis_jobs`.

- `apps/api/app/services/replay_parser.py`
  - Python subprocess wrapper.
  - Builds command from settings.
  - Enforces timeout.
  - Captures stdout/stderr.
  - Parses and validates JSON.
  - Converts failures to safe app exceptions.

- `apps/api/app/services/replay_artifacts.py`
  - Persistence helpers for creating/fetching parser artifacts.
  - User ownership checks.

- `apps/api/app/workers/analysis.py`
  - If upload kind is replay and a replay file path can be resolved, call parser before generating the result.
  - Persist artifact.
  - Include parse summary in `AnalysisResult.payload.source`.

- `apps/api/app/api/v1/replay_artifacts.py`
  - Read-only endpoint for retrieving the parse artifact attached to a job.
  - Enforces current user ownership.

- `apps/web/src/lib/api.ts`
  - Adds type and fetch helper for job replay artifact.

- `apps/web/src/app/analyses/[jobId]/page.tsx`
  - Shows whether a replay parse artifact exists.
  - Displays schema version, parser status, warnings, and summary counts.

## 5. Data Flow

### Manual parser CLI flow

1. Developer obtains a Deadlock replay file locally.
2. Developer runs:

   ```bash
   cd apps/replay-parser
   ./gradlew run --args="--input /path/to/match.dem --output /tmp/deadlock-parse.json"
   ```

3. CLI validates the input path.
4. CLI invokes Clarity.
5. CLI maps Clarity data into the normalized artifact schema.
6. CLI writes JSON.
7. Developer inspects the output and records findings in `docs/phase-2.5-clarity-findings.md`.

### Worker-integrated flow

1. User/dev creates a replay upload record.
2. Upload has either:
   - a local dev replay reference resolvable by the worker, or
   - no file reference, in which case Phase 2.5 parser execution is skipped and the job fails with clear instructions or falls back only when explicitly configured.
3. User creates an analysis job.
4. Arq worker loads the job and upload.
5. Worker resolves replay file path using local-only settings.
6. Worker calls `parse_replay_file(path)`.
7. Python wrapper runs the Java CLI with timeout.
8. Python validates returned JSON has required fields.
9. Worker persists `ReplayParseArtifact`.
10. Worker creates an `AnalysisResult` with a parse-aware fake summary.
11. Frontend polls existing job endpoint until success/failure.
12. Frontend fetches `/api/v1/analysis-jobs/{job_id}/replay-artifact` and renders summary.

### Parser failure flow

1. Worker calls parser.
2. Parser exits non-zero, times out, emits invalid JSON, or returns a validation error.
3. Python wrapper produces a safe `ReplayParserError`.
4. Worker records job failure and safe `error_message`.
5. Optional partial failure metadata is persisted if a row was created before failure.
6. Frontend displays the failed job state and safe message.

## 6. Interface Contracts

### Java CLI: `replay-parser`

Command:

```bash
./gradlew run --args="--input <path> [--output <path>] [--pretty]"
```

Input flags:

- `--input <path>` — required local replay file path.
- `--output <path>` — optional output JSON file. If omitted, write JSON to stdout.
- `--pretty` — optional pretty-print JSON.
- `--max-events <int>` — optional cap for emitted timeline events, default `500`.

Exit codes:

- `0` — success.
- `2` — invalid CLI arguments.
- `3` — input file missing/unreadable.
- `10` — Clarity parser failed.
- `11` — normalization failed.

Stderr:

- Safe short diagnostic only.
- No stack trace unless `--debug` is explicitly added later.

### Normalized replay artifact JSON: `deadlock-replay-parse-v1`

Minimum output shape:

```json
{
  "schema_version": "deadlock-replay-parse-v1",
  "parser": {
    "name": "clarity",
    "version": "4.0.1",
    "app_parser_version": "0.1.0"
  },
  "source": {
    "filename": "match.dem",
    "size_bytes": 123456,
    "sha256": "hex-or-null"
  },
  "match": {
    "match_id": "optional-string-or-null",
    "duration_seconds": 1800,
    "tick_count": 123456,
    "winning_team": "optional-string-or-null"
  },
  "players": [
    {
      "slot": 0,
      "account_id": "optional-string-or-null",
      "display_name": "optional-string-or-null",
      "hero": "optional-string-or-null",
      "team": "optional-string-or-null"
    }
  ],
  "timeline": [
    {
      "time_seconds": 123.4,
      "tick": 12345,
      "type": "event_type",
      "description": "human-readable summary",
      "data": {}
    }
  ],
  "capabilities": {
    "overview_available": true,
    "players_available": true,
    "combat_log_available": false,
    "entities_sampled": true
  },
  "warnings": ["Some expected fields were unavailable"],
  "stats": {
    "parse_duration_ms": 850,
    "timeline_events_emitted": 42,
    "timeline_events_dropped": 0
  }
}
```

Validation rules:

- `schema_version` must equal `deadlock-replay-parse-v1`.
- `parser.name` must be non-empty.
- `match`, `players`, `timeline`, `capabilities`, `warnings`, and `stats` must exist even if sparse.
- Timeline length must respect `--max-events`.
- Warnings must be strings safe for user/developer display.

### Database model: `ReplayParseArtifact`

Table: `replay_parse_artifacts`

Fields:

- `id: UUID` — primary key.
- `user_id: UUID` — FK to `users.id`, indexed, required.
- `upload_id: UUID` — FK to `uploads.id`, indexed, required.
- `job_id: UUID | None` — FK to `analysis_jobs.id`, unique when present.
- `parser_name: str` — default `clarity`.
- `parser_version: str | None`.
- `schema_version: str` — default `deadlock-replay-parse-v1`.
- `status: str` — `succeeded` or `failed`.
- `artifact: JSONB` — normalized artifact for successful parse.
- `warnings: JSONB` — list of warnings.
- `error_message: str | None` — safe error on failure.
- `parse_duration_ms: int | None`.
- `created_at: datetime`.
- `updated_at: datetime`.

Indexes/constraints:

- Index on `user_id`.
- Index on `upload_id`.
- Unique index on `job_id` where job ID exists.
- Index on `(user_id, created_at)`.

### Python function: `parse_replay_file`

Location: `apps/api/app/services/replay_parser.py`

Signature:

```python
async def parse_replay_file(path: Path, *, max_events: int = 500) -> ReplayParseResult: ...
```

Output model:

```python
class ReplayParseResult(BaseModel):
    schema_version: Literal["deadlock-replay-parse-v1"]
    parser: dict[str, Any]
    source: dict[str, Any]
    match: dict[str, Any]
    players: list[dict[str, Any]]
    timeline: list[dict[str, Any]]
    capabilities: dict[str, Any]
    warnings: list[str]
    stats: dict[str, Any]
```

Error cases:

- `ReplayParserNotConfiguredError` — parser command is missing.
- `ReplayParserInputError` — file does not exist or is not readable.
- `ReplayParserTimeoutError` — subprocess exceeds timeout.
- `ReplayParserExecutionError` — subprocess exits non-zero.
- `ReplayParserOutputError` — stdout/output file is invalid JSON or fails validation.

### Settings

Add to `apps/api/app/core/config.py`:

- `replay_parser_command: str | None`
  - Example: `../replay-parser/gradlew --project-dir ../replay-parser run --args=` may be awkward; prefer a small wrapper script path.
- `replay_parser_timeout_seconds: int = 60`
- `replay_parser_max_events: int = 500`
- `local_replay_sample_path: str | None = None`
- `allow_local_replay_paths: bool = False`

Recommended local command shape:

```env
REPLAY_PARSER_COMMAND=/absolute/path/to/apps/replay-parser/build/install/replay-parser/bin/replay-parser
REPLAY_PARSER_TIMEOUT_SECONDS=60
REPLAY_PARSER_MAX_EVENTS=500
LOCAL_REPLAY_SAMPLE_PATH=/absolute/path/to/sample.dem
ALLOW_LOCAL_REPLAY_PATHS=true
```

### API endpoint: `GET /api/v1/analysis-jobs/{job_id}/replay-artifact`

Fetch parse artifact for one job.

Output `200`:

```json
{
  "id": "uuid",
  "job_id": "uuid",
  "upload_id": "uuid",
  "parser_name": "clarity",
  "parser_version": "4.0.1",
  "schema_version": "deadlock-replay-parse-v1",
  "status": "succeeded",
  "artifact": {},
  "warnings": [],
  "error_message": null,
  "parse_duration_ms": 850,
  "created_at": "2026-05-14T00:00:00Z"
}
```

Error cases:

- `401` if unauthenticated.
- `404` if the job does not exist, does not belong to the user, or has no parse artifact.
- `409` if the job is a replay parse job but is not complete yet.

### AnalysisResult payload extension

For replay jobs with parsed artifacts, include parse summary in the existing `AnalysisResult.payload.source`:

```json
{
  "source": {
    "upload_id": "uuid",
    "upload_kind": "replay",
    "filename": "match.dem",
    "replay_artifact_id": "uuid",
    "replay_schema_version": "deadlock-replay-parse-v1",
    "parser_name": "clarity"
  },
  "replay_parse_summary": {
    "duration_seconds": 1800,
    "players_count": 12,
    "timeline_events_count": 42,
    "warnings_count": 1
  }
}
```

## 7. File Changes

- Create:
  - `docs/phase-2.5-clarity-replay-parser-plan.md` — this plan.
  - `docs/phase-2.5-clarity-findings.md` — running notes from parsing real replay files; include what fields are reliable and what is missing.
  - `apps/replay-parser/settings.gradle.kts` — Gradle project settings.
  - `apps/replay-parser/build.gradle.kts` — Java application plugin, Clarity dependency, Jackson dependency, test dependencies.
  - `apps/replay-parser/gradle.properties` — Java/Gradle properties.
  - `apps/replay-parser/src/main/java/com/deadlockcoach/replayparser/ReplayParserCli.java` — command entrypoint and argument validation.
  - `apps/replay-parser/src/main/java/com/deadlockcoach/replayparser/ClarityReplayParser.java` — Clarity integration.
  - `apps/replay-parser/src/main/java/com/deadlockcoach/replayparser/NormalizedReplayArtifact.java` — DTOs for normalized output.
  - `apps/replay-parser/src/main/java/com/deadlockcoach/replayparser/ReplayParserException.java` — safe parser exception type with exit code mapping.
  - `apps/replay-parser/src/test/java/com/deadlockcoach/replayparser/ReplayParserCliTest.java` — CLI tests for invalid args/missing file/output shape with fixtures or mocks.
  - `apps/api/app/db/models/replay_parse_artifact.py` — SQLModel table for persisted parse output.
  - `apps/api/alembic/versions/0003_replay_parse_artifacts.py` — migration for parse artifact table.
  - `apps/api/app/services/replay_parser.py` — subprocess wrapper and Pydantic validation.
  - `apps/api/app/services/replay_artifacts.py` — persistence/authorization helpers.
  - `apps/api/app/api/v1/replay_artifacts.py` — read-only artifact endpoint.
  - `apps/api/tests/test_replay_parser_service.py` — subprocess wrapper tests with fake parser scripts.
  - `apps/api/tests/test_replay_artifacts.py` — API and worker persistence tests.
  - `apps/api/tests/fixtures/replay_parser/success_parser.py` — fake parser executable for tests.
  - `apps/api/tests/fixtures/replay_parser/failing_parser.py` — fake parser executable for tests.
  - `apps/api/tests/fixtures/replay_parser/invalid_json_parser.py` — fake parser executable for tests.

- Modify:
  - `.env.example` — add local replay parser configuration variables.
  - `README.md` — add Java 17 requirement, parser build command, parser CLI usage, and Phase 2.5 verification steps.
  - `.gitignore` — ensure replay files, parser build outputs, and local artifacts are ignored; e.g. `*.dem`, `*.dem.bz2`, `apps/replay-parser/build/`, `tmp/replay-parser/`.
  - `apps/api/app/core/config.py` — add parser settings.
  - `apps/api/app/db/models/__init__.py` — export `ReplayParseArtifact`.
  - `apps/api/app/db/models/user.py` — add relationship to replay parse artifacts.
  - `apps/api/app/db/models/upload.py` — add relationship to replay parse artifacts.
  - `apps/api/app/db/models/analysis_job.py` — add optional relationship to replay parse artifact.
  - `apps/api/app/api/v1/router.py` — include replay artifact route.
  - `apps/api/app/services/fake_analysis.py` — allow fake result builder to include replay parse summary when provided.
  - `apps/api/app/workers/analysis.py` — call replay parser for replay uploads when configured and persist artifact.
  - `apps/web/src/lib/api.ts` — add `ReplayParseArtifactResponse` type and `fetchReplayArtifact(jobId)` helper.
  - `apps/web/src/app/analyses/[jobId]/page.tsx` — render parser artifact summary/warnings when available.
  - `apps/web/src/app/page.tsx` — optionally clarify replay upload currently requires local parser setup for Phase 2.5 spike.

- Delete:
  - None.

## 8. Implementation Phases

Use one branch for all Phase 2.5 replay parser spike work:

- Branch: `feature/replay-parser-phase-2.5`
- Each subphase below should be implemented as one or more focused commits on that branch.
- Do not create separate branches for 2.5A/2.5B/2.5C unless explicitly requested.

### Phase 2.5A — Java parser CLI skeleton

- Branch: `feature/replay-parser-phase-2.5`
- Commits:
  - [ ] Add `apps/replay-parser` Gradle Java application with Clarity and Jackson dependencies.
  - [ ] Add CLI argument parsing for `--input`, `--output`, `--pretty`, and `--max-events`.
  - [ ] Add safe exit codes for invalid args and missing files.
  - [ ] Add a placeholder normalized artifact writer that emits schema-valid JSON without deep Clarity extraction.
  - [ ] Add Java tests for CLI validation and JSON serialization.
- Done when:
  - `cd apps/replay-parser && ./gradlew test` passes.
  - `./gradlew run --args="--input <missing>"` exits with the expected code.
  - A known local file can produce schema-valid placeholder JSON.

### Phase 2.5B — Clarity integration and normalized extraction

- Branch: `feature/replay-parser-phase-2.5`
- Commits:
  - [ ] Wire Clarity parser into `ClarityReplayParser`.
  - [ ] Extract available replay overview/match metadata.
  - [ ] Extract player/entity summary where available.
  - [ ] Extract a capped basic timeline or capability summary from available Clarity streams.
  - [ ] Add warnings for unavailable/unknown fields instead of failing the whole parse.
  - [ ] Document first real replay findings in `docs/phase-2.5-clarity-findings.md`.
- Done when:
  - One real local Deadlock replay can be parsed into `deadlock-replay-parse-v1` JSON.
  - The output includes enough information to decide whether Clarity is viable for later phases.
  - The findings doc states which fields are reliable, unreliable, and unavailable.

### Phase 2.5C — Python subprocess wrapper and persistence

- Branch: `feature/replay-parser-phase-2.5`
- Commits:
  - [ ] Add replay parser settings to FastAPI config and `.env.example`.
  - [ ] Add `ReplayParseArtifact` model and Alembic migration.
  - [ ] Add Python `parse_replay_file` subprocess wrapper with timeout, JSON validation, and safe errors.
  - [ ] Add artifact persistence helpers.
  - [ ] Add tests with fake parser scripts for success, non-zero exit, timeout, and invalid JSON.
- Done when:
  - `uv run alembic upgrade head` applies cleanly.
  - Python tests pass without requiring Java or a real replay file.
  - Wrapper failure modes produce safe, short errors.

### Phase 2.5D — Worker integration and API access

- Branch: `feature/replay-parser-phase-2.5`
- Commits:
  - [ ] Update worker to parse replay uploads when parser is configured and a local replay path is resolvable.
  - [ ] Persist replay artifact linked to job/upload/user.
  - [ ] Extend fake analysis result payload with parse summary.
  - [ ] Add `GET /api/v1/analysis-jobs/{job_id}/replay-artifact`.
  - [ ] Add tests for worker success, parser failure, missing artifact, and cross-user authorization.
- Done when:
  - Existing Phase 2 match summary flow still works.
  - Replay jobs with a configured sample replay create both `AnalysisResult` and `ReplayParseArtifact`.
  - Parser failures mark the job failed with a safe error.
  - Artifact endpoint enforces ownership.

### Phase 2.5E — Frontend artifact summary and documentation

- Branch: `feature/replay-parser-phase-2.5`
- Commits:
  - [ ] Add frontend API helper/type for replay parse artifacts.
  - [ ] Update analysis detail page to show parser summary and warnings.
  - [ ] Add local replay parser setup docs to README.
  - [ ] Add findings doc entries from manual replay verification.
  - [ ] Add troubleshooting notes for Java, Gradle, parser timeout, and missing sample replay.
- Done when:
  - `npm run type-check`, `npm run lint`, and `npm run build` pass.
  - The analysis page gracefully handles no artifact, pending jobs, failed parser jobs, and successful parser jobs.
  - README has clear commands to build parser, run parser directly, run API/worker, and verify the full flow.

### Phase 2.5F — Final verification and decision gate

- Branch: `feature/replay-parser-phase-2.5`
- Commits:
  - [ ] Run all backend, frontend, and parser checks.
  - [ ] Manually verify a real replay parse through CLI.
  - [ ] Manually verify worker-integrated parse using Docker Postgres/Redis.
  - [ ] Update `docs/phase-2.5-clarity-findings.md` with a clear go/no-go recommendation for Clarity.
- Done when:
  - `cd apps/replay-parser && ./gradlew test` passes.
  - `cd apps/api && uv run pytest tests/ -q && uv run ruff check .` passes.
  - `cd apps/web && npm run type-check && npm run lint && npm run build` passes.
  - Manual CLI parse succeeds against one real replay.
  - Manual worker flow succeeds or documents exactly why Clarity is blocked.
  - Findings doc answers whether Phase 3 AI work can rely on parsed replay artifacts.

## 9. Testing Strategy

- Java unit/CLI tests:
  - CLI rejects missing `--input`.
  - CLI rejects unreadable file.
  - CLI writes valid JSON to stdout.
  - CLI writes valid JSON to `--output`.
  - DTO serialization includes required fields even when sparse.
  - `--max-events` caps timeline length.

- Java integration/manual tests:
  - Parse one real Deadlock replay locally.
  - Capture output artifact and summarize fields in findings doc.
  - Do not commit real replay files or large parser outputs.

- Python unit tests:
  - `parse_replay_file` handles successful fake parser output.
  - Non-zero subprocess exit raises `ReplayParserExecutionError`.
  - Timeout raises `ReplayParserTimeoutError`.
  - Invalid JSON raises `ReplayParserOutputError`.
  - Missing parser command raises `ReplayParserNotConfiguredError`.
  - Missing input file raises `ReplayParserInputError`.

- Backend API/worker tests:
  - Artifact endpoint requires auth.
  - Artifact endpoint rejects cross-user access.
  - Artifact endpoint returns 404 when no artifact exists.
  - Worker persists artifact for replay upload when parser returns valid output.
  - Worker marks job failed on parser failure.
  - Existing Phase 2 tests continue passing.

- Frontend checks:
  - `npm run type-check`.
  - `npm run lint`.
  - `npm run build`.
  - Manual browser test for replay job with artifact.
  - Manual browser test for job without artifact.

- Local integration verification:
  - Start infrastructure:

    ```bash
    docker compose -f infra/docker-compose.yml up -d
    ```

  - Build parser:

    ```bash
    cd apps/replay-parser
    ./gradlew installDist
    ```

  - Parse directly:

    ```bash
    apps/replay-parser/build/install/replay-parser/bin/replay-parser \
      --input /path/to/deadlock.dem \
      --output /tmp/deadlock-parse.json \
      --pretty
    ```

  - Configure `.env.local`:

    ```env
    REPLAY_PARSER_COMMAND=/absolute/path/to/apps/replay-parser/build/install/replay-parser/bin/replay-parser
    LOCAL_REPLAY_SAMPLE_PATH=/absolute/path/to/deadlock.dem
    ALLOW_LOCAL_REPLAY_PATHS=true
    ```

  - Apply migrations and run API/worker:

    ```bash
    cd apps/api
    uv run alembic upgrade head
    uv run fastapi dev --port 8000
    uv run arq app.workers.worker.WorkerSettings
    ```

  - Create a replay upload/job and verify:
    - job succeeds;
    - replay artifact row exists;
    - artifact endpoint returns JSON;
    - analysis page shows parser summary.

## 10. Security Implications

- User-controlled inputs:
  - Upload metadata already comes from API requests.
  - Replay file paths must not become arbitrary user-controlled filesystem access.
  - `local://` paths or `LOCAL_REPLAY_SAMPLE_PATH` must be local-dev-only and gated by `ALLOW_LOCAL_REPLAY_PATHS=true`.

- Filesystem access:
  - Parser reads replay files from disk in Phase 2.5.
  - Do not expose an API field allowing users to request arbitrary server paths.
  - In production, parser should read from controlled object storage/download paths, not raw user paths.

- Subprocess execution:
  - Use `asyncio.create_subprocess_exec` with argv list, not shell strings.
  - Do not interpolate user input into a shell command.
  - Enforce timeout.
  - Capture stderr and truncate safe errors.

- Large/untrusted files:
  - Replay files may be large or malformed.
  - Enforce parser timeout.
  - Later phases should add file size limits before real upload streaming.

- Data exposure:
  - Parse artifacts may include player names/account IDs if Clarity exposes them.
  - Artifact endpoint must enforce user ownership through job/upload relationships.
  - Avoid logging full artifacts by default.

- XSS:
  - Frontend must render artifact strings as text, not HTML.

- Secrets:
  - No secrets should be passed to parser.
  - `.env.example` should not include real local paths or credentials.

## 11. Risks & Tradeoffs

- Risk: Clarity's Deadlock support may not expose enough useful fields yet.
  - Mitigation: Treat this as a spike with a findings doc and go/no-go recommendation. Persist capability flags and warnings rather than pretending data is complete.

- Risk: Clarity examples may be Dota-focused and require Deadlock-specific exploration.
  - Mitigation: Keep extraction minimal first: overview, entities, capability summary, capped events. Avoid committing to a detailed schema until real outputs are inspected.

- Risk: Java/Gradle adds tooling complexity to a Python/Next repo.
  - Mitigation: Isolate under `apps/replay-parser`, document Java 17 requirement, and keep Python interaction as a CLI call.

- Risk: Subprocess parser calls may be slow.
  - Mitigation: Set configurable timeout and collect parse duration metrics. Optimization is out of scope for the spike.

- Risk: Real replay files are large and should not be committed.
  - Mitigation: Add `.gitignore` entries and use local-only sample paths.

- Risk: Local path handling could become unsafe if exposed through API.
  - Mitigation: Gate local path resolution behind environment settings and never accept arbitrary request-provided paths.

- Risk: JSONB artifact schema may need changes.
  - Mitigation: Include `schema_version` and keep downstream code tolerant of missing fields.

- Risk: This phase may overlap with structured AI analysis naming from the overarching plan.
  - Mitigation: This document now follows the overarching plan's numbering: Phase 2.5 is the Clarity Replay Parser Spike, and Phase 3 is reserved for Structured AI Analysis.

## 12. Open Questions

- Do we have a real Deadlock replay file available locally for manual verification?
  - Must be resolved before implementation reaches Phase 2.5B/2.5F. If not, implementation can build the CLI and wrapper but the spike cannot answer Clarity viability.

- Should local replay path resolution use only `LOCAL_REPLAY_SAMPLE_PATH`, or should `Upload.storage_key=local://...` be supported in local dev?
  - Recommendation: start with only `LOCAL_REPLAY_SAMPLE_PATH` for safety and simplicity. Add `local://` only if manual testing needs multiple files.

- Should parser failure fail the whole analysis job or fall back to fake analysis?
  - Recommendation: for replay uploads in Phase 2.5, parser failure should fail the job so we can see real viability issues. Match summaries and screenshots continue through the Phase 2 fake flow.

- Should the Java parser emit partial artifacts on failure?
  - Recommendation: not initially. Keep failure simple. Add partial artifacts only if Clarity often exposes useful partial data before failing.

- Do we want to commit Gradle wrapper files?
  - Recommendation: yes, if generated intentionally, so setup is reproducible. Review generated files before committing.
