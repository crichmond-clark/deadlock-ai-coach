# Phase 2.6 Deadlock API Integration Plan

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

Phase 2.6 is the Deadlock API integration phase. It is not another Clarity/replay parser phase.

The app needs a thin, app-owned integration layer around [deadlock-api.com](https://deadlock-api.com) and the Assets API so it can fetch structured match metadata and resolve game asset IDs. Clarity/replay parsing from Phase 2.5 remains the local replay-derived source, while this phase adds external context that replays either cannot provide or may expose only as raw IDs:

1. **Asset Resolution**: Turn raw IDs into user-facing names, images, descriptions, and metadata.
   - Example: `hero_id: 63` resolves to `Mina`.
   - Example: `ability_id: 1233782561` resolves to `Love Bites`.
2. **Match Metadata**: Given a `match_id`, fetch structured post-match data such as players, item/ability timeline entries, deaths, stats, positions, objectives, and damage summaries.
3. **Global Analytics**: Later, compare a player's choices against aggregate hero, matchup, item, and build statistics.
4. **Data Freshness**: Keep hero/item/ability catalog data current as the game changes.

The immediate objective is API-backed match metadata and asset resolution. Replay artifact enrichment is one consumer of this layer; broad analytics can come after the core client, cache, and normalization pieces are stable.

## 2. Goals & Non-Goals

- Goals:
  - Add separate Python clients for:
    - Game/stat endpoints at `https://api.deadlock-api.com`.
    - Asset/catalog endpoints at `https://assets.deadlock-api.com`.
  - Build an asset resolution service for heroes, purchasable items, abilities, and upgrades where available.
  - Store raw external API responses in JSONB where useful, then normalize incrementally.
  - Fetch and cache match metadata by `match_id`.
  - Enrich existing replay parse artifacts with resolved names/images without changing the replay parser contract.
  - Reuse the existing upload/job model rather than creating a parallel analysis flow.
  - Add tests for clients, fixtures, normalization, caching, and error handling.
  - Handle rate limits, API errors, and external downtime gracefully.

- Non-Goals:
  - Replacing Clarity/replay parsing.
  - Depending on API metadata as the single source of truth when a replay artifact exists.
  - Full analytics ingestion in the first implementation slice.
  - Full database dump ingestion; Phase 4 RAG can revisit this.
  - GraphQL endpoint usage; REST is sufficient for now.
  - Protobuf format handling; JSON endpoints are sufficient for now.
  - Custom match creation or live event API usage.
  - Frontend polish for rich API data browsing.

## 3. Proposed Architecture

Use the API as a supplementary data provider behind app-owned services. Keep external API response shapes out of the rest of the app.

```txt
                    ┌──────────────────────────────┐
                    │  api.deadlock-api.com         │
                    │  match metadata, analytics    │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │  DeadlockGameAPIClient        │
                    └──────────────┬───────────────┘
                                   │
Replay upload / match_id           │
        │                          │
        ▼                          ▼
┌────────────────┐        ┌────────────────────────┐
│ Clarity Parser │        │ Match Metadata Service  │
│ replay artifact│        │ raw JSONB + normalized  │
└───────┬────────┘        └───────────┬────────────┘
        │                             │
        │          ┌──────────────────▼──────────────────┐
        │          │  assets.deadlock-api.com             │
        │          │  heroes, items, abilities, images    │
        │          └──────────────────┬──────────────────┘
        │                             │
        │          ┌──────────────────▼──────────────────┐
        └─────────►│  Asset Resolution Service             │
                   │  heroes/items/abilities/upgrades      │
                   └──────────────────┬──────────────────┘
                                      │
                                      ▼
                   ┌──────────────────────────────────────┐
                   │ Enriched Match Context                │
                   │ replay + API metadata + resolved IDs  │
                   └──────────────────┬──────────────────┘
                                      │
                                      ▼
                   ┌──────────────────────────────────────┐
                   │ Phase 3 AI Coaching Pipeline          │
                   └──────────────────────────────────────┘
```

Key decisions:

- Keep two base URLs because game/stat endpoints and asset endpoints live on different hosts.
- Store raw match metadata and catalog payloads first; normalize only the subset needed for coaching.
- Do not force API metadata and Clarity artifacts into the exact same shape yet. Instead, normalize both into a later `EnrichedMatchContext` boundary.
- Keep Phase 2.6 implementation slices small. Analytics comes after client + assets + metadata are stable.

## 4. Component Breakdown

### 4.1 Deadlock API Clients

Create two thin `httpx` clients:

- `DeadlockGameAPIClient`
  - Base URL: `https://api.deadlock-api.com`
  - Uses endpoints such as `/v1/matches/{match_id}/metadata`, `/v1/players/{account_id}/match-history`, and later `/v1/analytics/*`.
- `DeadlockAssetsAPIClient`
  - Base URL: `https://assets.deadlock-api.com`
  - Uses endpoints such as `/v2/heroes`, `/v2/heroes/{id}`, `/v2/items`, `/v2/items/{id}`.

Responsibilities:

- Apply optional API key headers if configured.
- Enforce request timeouts.
- Normalize external errors into app exceptions.
- Respect `429` responses and `Retry-After` headers.
- Provide testable methods for known endpoints.

Files:

- `apps/api/app/services/deadlock_api/client.py`
- `apps/api/app/services/deadlock_api/errors.py`

### 4.2 Asset Catalog and Resolution Service

The API's `items`/timeline data can include abilities and upgrades, not only shop items. Avoid assuming every ID is a purchasable item.

Catalog concepts:

- `HeroAsset`
- `GameAsset`
  - may represent a purchasable item, ability, upgrade, weapon, or unknown external asset
- `ResolvedGameAsset`
  - app-facing resolution object used by replay/API enrichment

Initial DB approach:

- `heroes` table for hero catalog rows.
- `game_assets` table for item/ability/upgrade-like assets.
- Include `asset_kind` as nullable/string because upstream categories may not map perfectly at first.
- Store `raw_payload JSONB` for source fidelity.

Resolution behavior:

- Resolve from local DB first.
- If missing, optionally fetch single asset by ID from the Assets API and cache it.
- If still missing, return an explicit unresolved placeholder instead of failing analysis.

Files:

- `apps/api/app/models/hero.py`
- `apps/api/app/models/game_asset.py`
- `apps/api/app/services/deadlock_api/assets.py`
- `apps/api/app/services/deadlock_api/resolution.py`

### 4.3 Match Metadata Service

Fetches `GET /v1/matches/{match_id}/metadata` and stores the raw response.

Initial scope:

- Fetch by `match_id`.
- Cache/store raw JSONB keyed by `match_id`.
- Extract a small normalized summary:
  - match id, duration, start time, winning team, game mode
  - players: account id, player slot, hero id, team, lane, KDA, net worth, last hits, denies, level
  - player timeline references: item/ability entries, death details
  - objective and mid-boss timing where present
- Leave large/complex fields such as full path arrays and damage matrices in raw JSONB for later normalization.

Files:

- `apps/api/app/models/match_metadata.py`
- `apps/api/app/schemas/match_metadata.py`
- `apps/api/app/services/deadlock_api/match_metadata.py`

### 4.4 Enrichment Layer

Combines available sources into an app-owned context object.

Inputs:

- Replay parse artifact, if available.
- API match metadata, if `match_id` is available.
- Asset catalog resolution.

Outputs:

- `EnrichedMatchContext` for Phase 3 AI analysis.

Rules:

- Replay artifact remains the source for replay-derived events.
- API metadata supplements replay output and fills gaps.
- If replay and API disagree, keep both values and add a warning rather than silently overwriting.
- Missing external API data should degrade analysis quality, not crash the whole job when replay data exists.

Files:

- `apps/api/app/schemas/enriched_match.py`
- `apps/api/app/services/deadlock_api/enrichment.py`

### 4.5 Analytics Service (Deferred Slice)

Analytics are valuable, but they should not block the core integration.

Later scope:

- Hero stats.
- Hero counters.
- Hero synergies.
- Item stats.
- Hero build stats.
- Ability order stats.

Initial Phase 2.6 should define where this service will live but only implement it after client/assets/metadata/enrichment are working.

Files later:

- `apps/api/app/models/hero_analytics.py`
- `apps/api/app/schemas/analytics.py`
- `apps/api/app/services/deadlock_api/analytics.py`

## 5. Data Flow

### Flow A: Replay Upload with Optional Match ID

```txt
User uploads .dem and optionally supplies match_id
↓
Existing upload + analysis job flow runs
↓
Worker invokes Clarity parser
↓
Parser produces replay parse artifact
↓
If match_id is available, fetch/cache API match metadata
↓
Resolution service resolves hero/item/ability IDs from replay + metadata
↓
Enrichment layer builds EnrichedMatchContext with source warnings
↓
Future Phase 3 AI pipeline consumes enriched context
```

### Flow B: Match ID Input without Replay

```txt
User submits match_id as an analysis input type
↓
Existing upload/input + analysis job flow runs
↓
Worker fetches/caches API match metadata
↓
Resolution service resolves hero/item/ability IDs
↓
Enrichment layer builds EnrichedMatchContext with source = api_only
↓
Future Phase 3 AI pipeline consumes enriched context
```

Important: this should reuse the existing analysis job model. Prefer adding an input/upload type for `match_id` over adding a separate `POST /api/v1/matches/{match_id}/analyze` flow.

### Flow C: Catalog Sync

```txt
Scheduled or manually-triggered Arq job
↓
Fetch /v2/heroes and /v2/items from assets API
↓
Upsert heroes and game_assets tables
↓
Resolution service uses local DB cache during analysis
```

## 6. Interface Contracts

### 6.1 Configuration

```python
class Settings(BaseSettings):
    deadlock_api_base_url: str = "https://api.deadlock-api.com"
    deadlock_assets_api_base_url: str = "https://assets.deadlock-api.com"
    deadlock_api_key: str | None = None
    deadlock_api_timeout_seconds: float = 10.0
    deadlock_api_cache_ttl_minutes: int = 60
```

API key note: an API key increases allowed request volume; it does not remove all rate limits.

### 6.2 Client Functions

```python
class DeadlockGameAPIClient:
    async def get_match_metadata(self, match_id: int, *, disable_steam: bool = True) -> dict: ...
    async def get_player_match_history(self, account_id: int) -> dict: ...

class DeadlockAssetsAPIClient:
    async def list_heroes(self) -> list[dict]: ...
    async def get_hero(self, hero_id: int) -> dict: ...
    async def list_items(self) -> list[dict]: ...
    async def get_item(self, item_id: int) -> dict: ...
```

### 6.3 App-Owned Schemas

```python
class Position(BaseModel):
    x: float
    y: float
    z: float | None = None

class ResolvedHero(BaseModel):
    id: int
    name: str | None
    class_name: str | None
    image_url: str | None
    raw_payload: dict | None = None
    resolved: bool

class ResolvedGameAsset(BaseModel):
    id: int
    name: str | None
    class_name: str | None
    asset_kind: str | None  # item, ability, upgrade, weapon, unknown
    image_url: str | None
    raw_payload: dict | None = None
    resolved: bool

class MatchMetadataSummary(BaseModel):
    match_id: int
    duration_s: int | None = None
    start_time: int | None = None
    game_mode: int | None = None
    winning_team: int | None = None
    average_badge_team0: int | None = None
    average_badge_team1: int | None = None
    players: list[MatchPlayerSummary]
    source: Literal["api"] = "api"

class MatchPlayerSummary(BaseModel):
    account_id: int | None = None
    player_slot: int
    hero_id: int | None = None
    team: int | None = None
    assigned_lane: int | None = None
    kills: int | None = None
    deaths: int | None = None
    assists: int | None = None
    net_worth: int | None = None
    last_hits: int | None = None
    denies: int | None = None
    level: int | None = None

class SourceWarning(BaseModel):
    source: Literal["api", "replay", "enrichment"]
    code: str
    message: str

class EnrichedMatchContext(BaseModel):
    match_id: int | None = None
    replay_artifact_id: str | None = None
    api_metadata_id: str | None = None
    metadata_summary: MatchMetadataSummary | None = None
    resolved_heroes: dict[int, ResolvedHero]
    resolved_assets: dict[int, ResolvedGameAsset]
    source_mode: Literal["replay_only", "api_only", "replay_plus_api"]
    warnings: list[SourceWarning]
```

### 6.4 Service Functions

```python
async def sync_asset_catalog(session: AsyncSession) -> CatalogSyncResult: ...
async def resolve_hero(session: AsyncSession, hero_id: int) -> ResolvedHero: ...
async def resolve_game_asset(session: AsyncSession, asset_id: int) -> ResolvedGameAsset: ...
async def fetch_and_cache_match_metadata(session: AsyncSession, match_id: int) -> MatchMetadataSummary: ...
async def enrich_match_context(
    session: AsyncSession,
    *,
    match_id: int | None,
    replay_artifact_id: UUID | None,
) -> EnrichedMatchContext: ...
```

### 6.5 Data Models

New tables:

- `heroes`
  - `id INTEGER PRIMARY KEY`
  - `name TEXT NULL`
  - `class_name TEXT NULL`
  - `image_url TEXT NULL`
  - `raw_payload JSONB NOT NULL`
  - `fetched_at TIMESTAMPTZ NOT NULL`

- `game_assets`
  - `id INTEGER PRIMARY KEY`
  - `name TEXT NULL`
  - `class_name TEXT NULL`
  - `asset_kind TEXT NULL`
  - `image_url TEXT NULL`
  - `raw_payload JSONB NOT NULL`
  - `fetched_at TIMESTAMPTZ NOT NULL`

- `external_match_metadata`
  - `id UUID PRIMARY KEY`
  - `match_id BIGINT NOT NULL UNIQUE`
  - `raw_payload JSONB NOT NULL`
  - `summary JSONB NOT NULL`
  - `fetched_at TIMESTAMPTZ NOT NULL`

- `enriched_match_contexts`
  - optional in this phase; can be stored as JSONB on/near `analysis_results` first if simpler

## 7. File Changes

Create:

- `apps/api/app/services/deadlock_api/__init__.py` — package marker and public exports
- `apps/api/app/services/deadlock_api/client.py` — game/assets API clients
- `apps/api/app/services/deadlock_api/errors.py` — normalized external API exceptions
- `apps/api/app/services/deadlock_api/assets.py` — asset catalog sync helpers
- `apps/api/app/services/deadlock_api/resolution.py` — hero/asset resolution service
- `apps/api/app/services/deadlock_api/match_metadata.py` — metadata fetch/cache/summary service
- `apps/api/app/services/deadlock_api/enrichment.py` — combined context builder
- `apps/api/app/schemas/match_metadata.py` — metadata summary schemas
- `apps/api/app/schemas/enriched_match.py` — enriched context schemas
- `apps/api/app/models/game_asset.py` — game asset SQLModel
- `apps/api/app/models/match_metadata.py` — external metadata SQLModel

Modify:

- `apps/api/app/core/config.py` — add Deadlock API settings
- `apps/api/app/models/__init__.py` — export new models
- `apps/api/app/workers/analysis.py` or equivalent worker module — call enrichment service after replay parsing when data is available
- `apps/api/alembic/versions/*` — add migration for new tables
- `.env.example` — document optional API key and base URLs

Do not create a separate match analysis endpoint until the existing upload/input model is reviewed. Prefer extending the existing job creation flow with a match-id input type.

## 8. Implementation Phases

Use one branch for this feature: `feature/deadlock-api-integration`.

### Phase 2.6A — API Client Foundation

Commits:

- [ ] Add config for game API and assets API base URLs, optional API key, timeout, cache TTL.
- [ ] Add `DeadlockGameAPIClient` and `DeadlockAssetsAPIClient`.
- [ ] Add normalized exception types.
- [ ] Add unit tests using mocked HTTP responses.
- [ ] Add a small manually runnable script or test marker for live smoke checks.

Done when:

- Clients can fetch a known match metadata payload and known asset payload in a live smoke check.
- Mocked tests cover success, 404, 429, timeout, and invalid JSON.

### Phase 2.6B — Asset Catalog and Resolution

Commits:

- [ ] Add `heroes` and `game_assets` models + migration.
- [ ] Add catalog sync service for `/v2/heroes` and `/v2/items`.
- [ ] Add resolution service with unresolved placeholders.
- [ ] Add tests with fixture data.

Done when:

- `hero_id=63` resolves to `Mina` from cached data.
- `asset_id=1233782561` resolves to `Love Bites` as an ability-like asset, not assumed to be a shop item.
- Missing IDs return unresolved placeholders instead of crashing.

### Phase 2.6C — Match Metadata Fetch and Cache

Commits:

- [ ] Add `external_match_metadata` model + migration.
- [ ] Add `fetch_and_cache_match_metadata()` service.
- [ ] Add summary normalization for match and player basics.
- [ ] Add tests using the `44009651` fixture.

Done when:

- A known match ID can be fetched, stored as raw JSONB, and summarized.
- Re-fetching the same match uses cached data unless stale/forced.
- `disable_steam=True` is used by default to avoid accidentally triggering expensive Steam fallback requests during normal app usage.

### Phase 2.6D — Enrichment for Existing Analysis Jobs

Commits:

- [ ] Add `EnrichedMatchContext` schema.
- [ ] Extract IDs from replay artifacts and/or API metadata.
- [ ] Resolve heroes/assets and attach warnings for missing/conflicting data.
- [ ] Integrate enrichment into the existing worker after replay parsing.
- [ ] Persist enriched context as JSONB on an existing artifact/result path if no dedicated table is needed yet.

Done when:

- Existing replay analysis jobs can produce an enriched context when IDs are present.
- Jobs still succeed when API enrichment fails but replay parsing succeeded.
- Source warnings are visible in stored artifact/result data.

### Phase 2.6E — Match ID Input Path

Commits:

- [ ] Extend the existing upload/input model to support `match_id` input.
- [ ] Reuse existing analysis job creation and polling flow.
- [ ] Worker fetches metadata and builds `api_only` enriched context.
- [ ] Add authorization tests around job ownership.

Done when:

- A user can submit a match ID without uploading a replay.
- The job produces cached metadata and an enriched context.
- No separate, parallel analysis endpoint exists unless explicitly approved later.

## Deferred Enhancement: Analytics Context

Do not include broad hero/item/matchup analytics in Phase 2.6. Keep this phase focused on API clients, asset resolution, match metadata caching, enrichment, and match-id input.

Global analytics belongs in the later analytics enhancement phase in the overarching plan, after the core analysis flow is stable enough to prove which stats are actually useful for coaching.

## 9. Testing Strategy

- Unit tests:
  - Client success/error cases with mocked `httpx` responses.
  - Resolution behavior for cached, fetched, and unresolved IDs.
  - Metadata summary normalization from fixture JSON.
  - Enrichment source-mode and warning behavior.

- Integration tests:
  - DB upsert/caching behavior for heroes, game assets, and match metadata.
  - Worker enrichment path with API success and API failure.
  - Match ID input path reusing existing analysis job ownership checks.

- Live smoke checks:
  - `GET https://api.deadlock-api.com/v1/matches/44009651/metadata?disable_steam=true`
  - `GET https://assets.deadlock-api.com/v2/heroes/63` → `Mina`
  - `GET https://assets.deadlock-api.com/v2/items/1233782561` → `Love Bites`

Live smoke checks should not be mandatory in normal CI unless explicitly marked and gated by environment variables.

## 10. Security Implications

- Users control `match_id` input. Validate that it is a positive integer and apply normal authenticated job ownership checks.
- Do not expose the Deadlock API key to the browser. It belongs only in backend/worker environment variables.
- External API calls can be abused indirectly. Mitigate with:
  - per-user job limits,
  - cached match metadata,
  - dedupe by `match_id`,
  - request timeouts,
  - rate-limit/backoff handling.
- Store external API raw payloads as JSONB; treat them as untrusted external data when rendering in the frontend.
- Do not render raw HTML descriptions from asset payloads without sanitization. Asset descriptions may contain HTML/SVG strings.
- No command execution or path traversal risk is introduced by API fetches directly, but worker integration must preserve existing replay parser subprocess safety.

## 11. Risks & Tradeoffs

| Risk | Mitigation |
|---|---|
| API downtime | Cache catalog and match metadata locally; allow replay-only analysis to continue when possible |
| Rate limits | Cache by match ID; sync catalogs on schedule; respect 429 and Retry-After; use optional API key for higher limits |
| Schema changes | Keep raw JSONB; normalize only a small subset; ignore unknown fields; fixture tests catch breaking changes |
| Misclassified IDs | Use generic `game_assets` with nullable `asset_kind`; do not assume every ID is a shop item |
| Clarity/API disagreement | Preserve both values and add source warnings; do not silently overwrite replay data |
| Scope creep | Defer broad analytics to the overarching plan's Phase 8 Analytics Enhancements; keep Phase 2.6 limited to clients, assets, match metadata, enrichment, and match-id input |
| Unsafe frontend rendering | Sanitize or avoid rendering raw description HTML/SVG from API payloads |

## 12. Open Questions

1. Where should `match_id` live in the existing domain model: as an `Upload` input type, as metadata on `AnalysisJob`, or as a separate `Match` record linked to jobs?
2. Should enriched contexts be persisted in a dedicated table, or stored as JSONB on existing analysis artifacts/results until the shape stabilizes?
3. Should catalog sync run automatically on worker startup in development, or only via explicit command/job?
4. How should the app detect stale match metadata, if at all? Match metadata is mostly immutable, but API parse/enrichment may improve over time.
5. Should live API smoke tests run in CI behind an opt-in environment flag, or remain manual/local only?
