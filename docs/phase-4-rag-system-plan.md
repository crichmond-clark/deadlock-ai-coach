# Phase 4 RAG System Plan

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

The platform can analyze a single submitted match, but it cannot ground coaching in reusable strategy knowledge. Users need searchable strategy knowledge and AI coaching needs cited context from guides, patch notes, matchup notes, and other curated sources.

Phase 4 adds an app-owned retrieval-augmented generation foundation: ingest knowledge sources, chunk them, embed chunks in Postgres/pgvector, search by semantic similarity, display citations, and expose retrieval context for Phase 3 coaching.

## 2. Goals & Non-Goals

- Goals:
  - Enable `pgvector` in the PostgreSQL database.
  - Add knowledge source, chunk, and embedding tables.
  - Add a provider-flexible embedding abstraction with OpenAI as default.
  - Support OpenAI-compatible embedding endpoints for open-source/provider-compatible models where possible.
  - Ingest pasted text/markdown strategy sources in the first slice.
  - Chunk, hash, embed, and persist knowledge with source metadata and patch/version tags.
  - Add a strategy search API endpoint returning ranked chunks with citations.
  - Add a simple frontend strategy search UI.
  - Provide a retrieval service that Phase 3/5 coaching can call to inject citations.
  - Keep ingestion and search authenticated and user-scoped/global-source aware.

- Non-Goals:
  - Web crawling or arbitrary server-side URL fetching in the first slice.
  - Full admin/role system.
  - Automatically ingesting every Deadlock API database dump.
  - RAG evaluation with Ragas/DeepEval. That belongs in Phase 5.
  - Streaming answer generation.
  - Multi-vector/hybrid search beyond simple vector similarity plus metadata filtering.

## 3. Proposed Architecture

Use PostgreSQL + pgvector as the retrieval store to avoid adding a separate vector database. Store source text and metadata in relational tables, split source content into deterministic chunks, generate embeddings via an embedding provider, and search chunks by vector distance.

```txt
Knowledge Source text/markdown
↓
Ingestion service validates + normalizes
↓
Chunking service creates stable chunks + content hashes
↓
Embedding provider generates vectors
↓
Postgres stores source, chunks, embeddings
↓
Strategy search endpoint embeds query + vector-searches chunks
↓
Frontend displays ranked snippets + citations
↓
Phase 3/5 coaching retrieves top-k context for prompts
```

Provider strategy:

- `EMBEDDING_PROVIDER=openai` defaults to OpenAI `text-embedding-3-small`.
- `EMBEDDING_PROVIDER=openai_compatible` uses `EMBEDDING_BASE_URL`, `EMBEDDING_API_KEY`, and `EMBEDDING_MODEL` for Ollama Cloud, vLLM, or other compatible endpoints if they support embeddings.
- `EMBEDDING_PROVIDER=mock` returns deterministic vectors for tests.
- Provider-specific Minimax support is deferred unless OpenAI-compatible embedding endpoints are not sufficient.

The RAG system will expose retrieval context as app-owned Pydantic models. AI analysis code consumes those models, not database rows or provider responses.

## 4. Component Breakdown

- Database extension and models:
  - Enable `vector` extension.
  - Store sources, chunks, and embeddings.
  - Keep global and user-owned source support.

- Embedding provider abstraction:
  - Provider protocol for embedding text batches.
  - OpenAI adapter.
  - OpenAI-compatible adapter.
  - Mock adapter.

- Chunking service:
  - Deterministic character/token-ish splitter with overlap.
  - Stable content hashes to avoid duplicate chunks.
  - Metadata propagation from source to chunks.

- Ingestion service:
  - Validates source content.
  - Creates/updates source rows.
  - Chunks and embeds content.
  - Handles re-ingestion idempotently.

- Search service:
  - Embeds query.
  - Performs vector similarity search.
  - Applies filters: owner/global, source type, hero, patch, tags.
  - Returns citation-ready snippets.

- API layer:
  - Create/list/retrieve knowledge sources.
  - Search strategy knowledge.

- Frontend:
  - Minimal strategy search page.
  - Search input, filters, ranked results, citations.

- Coaching integration:
  - Retrieval service returns compact `RetrievalContext` for Phase 3/5 prompts.
  - If Phase 3 branch is not merged yet, this integration is implemented as a follow-up commit after both branches are merged.

## 5. Data Flow

### Flow A: Ingest Pasted Strategy Text

```txt
Authenticated user submits title + text/markdown + optional tags/hero/patch
↓
API creates KnowledgeSource(status="processing")
↓
Ingestion service normalizes text and calculates content_hash
↓
Chunking service creates chunks
↓
Embedding provider embeds chunk texts in batches
↓
DB stores chunks and vector embeddings
↓
Source marked ready
```

### Flow B: Strategy Search

```txt
User enters query + optional filters
↓
API validates query
↓
Search service embeds query
↓
pgvector query returns nearest chunks user can access
↓
API returns snippets with source citation metadata
↓
Frontend renders ranked results
```

### Flow C: Coaching Retrieval Context

```txt
Analysis workflow builds query from hero/match context
↓
Retrieval service searches top-k chunks
↓
Compact citations injected into AI prompt context
↓
Structured AI result can reference retrieved source IDs
```

## 6. Interface Contracts

### Environment Settings

- `EMBEDDING_PROVIDER`: `openai | openai_compatible | mock`, default `openai`.
- `EMBEDDING_MODEL`: default `text-embedding-3-small`.
- `EMBEDDING_API_KEY`: generic key for compatible providers.
- `EMBEDDING_BASE_URL`: required for `openai_compatible`.
- `EMBEDDING_DIMENSIONS`: default `1536` for `text-embedding-3-small` unless configured.
- `EMBEDDING_BATCH_SIZE`: default `64`.
- `RAG_CHUNK_SIZE_CHARS`: default `1200`.
- `RAG_CHUNK_OVERLAP_CHARS`: default `200`.
- `RAG_TOP_K`: default `5`.

### Database Models

`KnowledgeSource`

- `id UUID primary key`
- `owner_user_id UUID nullable` — null means global/shared source.
- `source_type str` — `text | markdown | note | patch_notes | guide`.
- `title str`
- `url str nullable` — metadata only in first slice, not fetched server-side.
- `content_hash str`
- `raw_content text`
- `status str` — `processing | ready | failed`.
- `patch_version str nullable`
- `hero_ids list[int] JSONB nullable`
- `tags list[str] JSONB`
- `metadata JSONB`
- `error_message text nullable`
- timestamps.

`KnowledgeChunk`

- `id UUID primary key`
- `source_id UUID not null`
- `chunk_index int`
- `content text`
- `content_hash str`
- `token_count_estimate int nullable`
- `metadata JSONB`
- timestamps.

`KnowledgeEmbedding`

- `id UUID primary key`
- `chunk_id UUID not null`
- `provider str`
- `model_name str`
- `dimensions int`
- `embedding vector(dimensions)`
- `metadata JSONB`
- timestamps.

Unique constraints:

- `(source_id, chunk_index)` for chunks.
- `(chunk_id, provider, model_name)` for embeddings.

### Pydantic Schemas

`KnowledgeSourceCreateRequest`

```python
class KnowledgeSourceCreateRequest(BaseModel):
    title: str
    source_type: Literal["text", "markdown", "note", "patch_notes", "guide"] = "text"
    content: str
    url: str | None = None
    patch_version: str | None = None
    hero_ids: list[int] = []
    tags: list[str] = []
```

`StrategySearchRequest`

```python
class StrategySearchRequest(BaseModel):
    query: str
    top_k: int = 5
    hero_ids: list[int] = []
    tags: list[str] = []
    include_global: bool = True
```

`StrategySearchResult`

```python
class StrategySearchResult(BaseModel):
    chunk_id: UUID
    source_id: UUID
    title: str
    snippet: str
    score: float
    citation_label: str
    url: str | None = None
    patch_version: str | None = None
    tags: list[str]
    metadata: dict[str, Any]
```

`RetrievalContext`

```python
class RetrievalContext(BaseModel):
    query: str
    results: list[StrategySearchResult]
    warnings: list[str] = []
```

### Embedding Provider Protocol

```python
class EmbeddingProvider(Protocol):
    async def embed_texts(
        self,
        texts: list[str],
        *,
        model: str,
    ) -> EmbeddingProviderResponse: ...
```

### API Endpoints

`POST /api/v1/knowledge-sources`

- Auth: current authenticated user.
- Input: `KnowledgeSourceCreateRequest`.
- Output: `KnowledgeSourceResponse` including id/status/chunk count.
- Error cases:
  - `400` empty/too-large content.
  - `401` unauthenticated.
  - `422` invalid hero IDs/tags.
  - `503` embedding provider unavailable.

`GET /api/v1/knowledge-sources`

- Auth: current authenticated user.
- Output: paginated list of user's sources plus global sources.

`POST /api/v1/strategy-search`

- Auth: current authenticated user.
- Input: `StrategySearchRequest`.
- Output: `StrategySearchResponse` with ranked results.
- Error cases:
  - `400` empty query.
  - `401` unauthenticated.
  - `503` embedding provider unavailable.

### Retrieval Service

```python
async def retrieve_strategy_context(
    db: AsyncSession,
    *,
    user_id: UUID,
    query: str,
    top_k: int = 5,
    hero_ids: list[int] | None = None,
    tags: list[str] | None = None,
    include_global: bool = True,
) -> RetrievalContext: ...
```

## 7. File Changes

- Create:
  - `apps/api/app/db/models/knowledge_source.py` — source metadata and raw content.
  - `apps/api/app/db/models/knowledge_chunk.py` — chunk rows.
  - `apps/api/app/db/models/knowledge_embedding.py` — vector embeddings.
  - `apps/api/alembic/versions/0008_rag_knowledge_tables.py` — pgvector extension and tables.
  - `apps/api/app/embeddings/__init__.py` — embedding package exports.
  - `apps/api/app/embeddings/providers/base.py` — provider protocol.
  - `apps/api/app/embeddings/providers/openai.py` — OpenAI embeddings adapter.
  - `apps/api/app/embeddings/providers/openai_compatible.py` — compatible embeddings adapter.
  - `apps/api/app/embeddings/providers/mock.py` — deterministic embeddings for tests.
  - `apps/api/app/embeddings/providers/registry.py` — provider factory.
  - `apps/api/app/schemas/knowledge.py` — API/request/response schemas.
  - `apps/api/app/schemas/retrieval.py` — retrieval context schemas.
  - `apps/api/app/services/rag/chunking.py` — deterministic chunking.
  - `apps/api/app/services/rag/ingestion.py` — source ingestion pipeline.
  - `apps/api/app/services/rag/search.py` — vector search.
  - `apps/api/app/services/rag/context.py` — coaching retrieval context builder.
  - `apps/api/app/api/v1/knowledge.py` — knowledge source endpoints.
  - `apps/api/app/api/v1/strategy_search.py` — strategy search endpoint.
  - `apps/api/tests/test_rag_chunking.py`
  - `apps/api/tests/test_embedding_providers.py`
  - `apps/api/tests/test_rag_ingestion.py`
  - `apps/api/tests/test_rag_search.py`
  - `apps/web/src/app/strategy-search/page.tsx` — simple search UI.
  - `apps/web/src/components/strategy-search-results.tsx`

- Modify:
  - `apps/api/pyproject.toml` — add `pgvector` and OpenAI/embedding deps as needed.
  - `apps/api/app/core/config.py` — add embedding/RAG settings.
  - `apps/api/app/db/models/__init__.py` — export knowledge models.
  - `apps/api/app/api/v1/router.py` — include knowledge/search routers.
  - `apps/api/app/workers/worker.py` — optionally add ingestion job entrypoint if ingestion becomes async.
  - `apps/web/src/lib/api.ts` — knowledge/search API helpers and types.
  - `README.md`, `.env.example`, `docs/testing-guide.md` — RAG setup/testing docs.
  - Phase 3 AI analysis service — optional follow-up commit to inject retrieval context once both branches are merged.

- Delete:
  - None.

## 8. Implementation Phases

Branching rule:

- Branch: `feature/phase-4-rag-system`
- This can be developed in parallel with Phase 3 after Phase 2.6 is stable because it mainly adds independent knowledge/search APIs.
- If Phase 3 is already merged, include coaching-context injection in this branch. If Phase 3 is not merged, implement search/ingestion first and add the coaching integration after merge.

### Phase 4A — pgvector and Knowledge Models

- Branch: `feature/phase-4-rag-system`
- Commits:
  - [ ] Add `pgvector` dependency.
  - [ ] Add `KnowledgeSource`, `KnowledgeChunk`, and `KnowledgeEmbedding` models.
  - [ ] Add migration enabling `vector` extension and creating tables/indexes.
  - [ ] Add model exports and relationship wiring.
- Done when:
  - Alembic migration applies cleanly on local Postgres.
  - Model import tests pass.

### Phase 4B — Embedding Provider Foundation

- Commits:
  - [ ] Add embedding settings and `.env.example` entries.
  - [ ] Add embedding provider protocol and response models.
  - [ ] Add mock provider.
  - [ ] Add OpenAI and OpenAI-compatible providers.
  - [ ] Add provider tests using deterministic fixtures.
- Done when:
  - Tests can generate deterministic embeddings without API keys.
  - Provider errors normalize into controlled app exceptions.

### Phase 4C — Chunking and Ingestion

- Commits:
  - [ ] Add chunking service with stable hashes and overlap.
  - [ ] Add source ingestion service.
  - [ ] Add API endpoint for `POST /knowledge-sources`.
  - [ ] Add ingestion tests for idempotency, duplicate content, and validation.
- Done when:
  - A pasted strategy note creates a source, chunks, and embeddings using the mock provider.
  - Re-ingesting unchanged content does not duplicate chunks.

### Phase 4D — Strategy Search API

- Commits:
  - [ ] Add vector search service.
  - [ ] Add `POST /strategy-search` endpoint.
  - [ ] Add filters for owner/global, hero IDs, and tags.
  - [ ] Add search tests with mock embeddings.
- Done when:
  - A query returns ranked chunks with citation metadata.
  - Unauthorized users cannot see another user's private sources.

### Phase 4E — Frontend Search UI

- Commits:
  - [ ] Add strategy search API helpers.
  - [ ] Add `/strategy-search` page.
  - [ ] Render search results with source title, snippet, score, patch/tags, and citation label.
- Done when:
  - Typecheck/build pass.
  - User can search ingested local notes from the UI.

### Phase 4F — Coaching Retrieval Integration

- Commits:
  - [ ] Add `retrieve_strategy_context` service.
  - [ ] Add prompt-context conversion for top-k retrieved snippets.
  - [ ] Wire into Phase 3 AI analysis only if Phase 3 is merged; otherwise leave service ready and document follow-up.
  - [ ] Add tests proving retrieved citations appear in the AI prompt context and final `SourceEvidence` when mock AI references them.
- Done when:
  - AI coaching can receive compact retrieval context and produce citation-aware output.
  - Missing/empty RAG results degrade with a warning, not a failed job.

### Subagent Orchestration Strategy

Phase 4 can use parallel subagents after Phase 4A defines database contracts:

- Backend RAG subagent: models, migrations, ingestion/search services.
- Provider subagent: embedding adapters and provider tests.
- Frontend subagent: strategy search UI from agreed API fixtures.
- Docs/testing subagent: testing guide, fixtures, live smoke docs.

Do not parallelize search implementation before the embedding vector dimensions and table schema are finalized.

## 9. Testing Strategy

- Unit tests:
  - Chunking produces deterministic chunks and content hashes.
  - Empty/short/long content handling.
  - Mock embedding provider returns stable vectors.
  - OpenAI-compatible provider handles success/failure/timeout with mocked HTTP.
  - Search request validation and filter construction.

- Integration tests:
  - Migration enables pgvector and creates indexes.
  - Ingestion creates sources/chunks/embeddings.
  - Re-ingestion is idempotent.
  - Search returns expected ranked chunks with mock embeddings.
  - Authorization prevents cross-user private source access.

- Edge cases:
  - Content too large.
  - Duplicate source content.
  - Embedding dimension mismatch.
  - Provider failure mid-batch.
  - No search results.
  - Tags/hero filters with no matches.

- Validation before merge:
  - `cd apps/api && uv run pytest -v`
  - `cd apps/api && uv run ruff check .`
  - `cd apps/api && uv run alembic upgrade head`
  - `cd apps/web && npm run type-check`
  - `cd apps/web && npm run build`
  - Optional live smoke with a real embedding provider, not required in CI.

## 10. Security Implications

- User-controlled content:
  - Knowledge source text is fully user-controlled. Store as text and render snippets escaped by React.
  - Do not render raw HTML from knowledge sources.

- SSRF:
  - First slice must not fetch arbitrary URLs server-side. `url` is citation metadata only.

- Authorization:
  - Private sources are visible only to their owner.
  - Global sources have `owner_user_id = null`; without roles, creating global sources should be internal/CLI-only or disabled in public endpoints.

- Secrets:
  - Embedding provider API keys stay server-side only.

- Prompt injection:
  - Retrieved knowledge is untrusted context. AI prompts must label it as retrieved source material, not system instructions.

- Data retention:
  - User-uploaded notes may contain private information. Do not log full content by default.

## 11. Risks & Tradeoffs

| Risk | Mitigation |
|---|---|
| pgvector extension unavailable in local/hosted DB | Verify extension in migration; document Neon/local Postgres requirements. |
| Embedding provider dimension mismatch | Store dimensions per embedding row and validate against configured dimension before insert/search. |
| Chunking quality is basic | Start deterministic and simple; improve later with semantic chunking only if needed. |
| RAG returns irrelevant chunks | Add filters and keep top-k small; Phase 5 evaluations can measure usefulness. |
| User source ingestion creates unbounded storage/cost | Enforce content size limits, chunk limits, and batch limits. |
| Branch conflicts with Phase 3 | Keep RAG services independent; only add coaching integration after Phase 3 contracts are stable. |

## 12. Open Questions

All questions must be resolved or accepted as risks before implementation starts.

1. Should public endpoints allow users to create only private sources, with global sources seeded by CLI/internal jobs? Recommended: yes.
2. Do you want URL fetching in this phase? Recommended: no, store URL only as citation metadata.
3. Which open-source embedding endpoint do you want to prioritize after OpenAI-compatible support? Recommended: Ollama Cloud/OpenAI-compatible first.
4. Should source ingestion be synchronous for MVP or queued with Arq? Recommended: synchronous for small text, queued once file/large sources are added.
5. What initial seed knowledge should be included for demos? Recommended: add manual seed notes later, not in this infrastructure PR.
