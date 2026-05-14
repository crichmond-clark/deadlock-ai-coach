# Phase 6 Replay Intelligence Validation Gate Plan

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

Phase 6 depends on real replay-derived evidence from Clarity. The current Phase 2.5 parser skeleton produces schema-valid placeholder output, but real Deadlock `.dem` parsing has not been validated. Building death timelines, ability casts, item progression, teamfight detection, and semantic replay coaching before validation would risk building product features around imaginary data.

This plan defines the gate that must be passed before Phase 6 implementation planning begins.

## 2. Goals & Non-Goals

- Goals:
  - Validate that Clarity can parse at least one real Deadlock replay file.
  - Identify which event classes/properties are actually accessible.
  - Produce one real normalized artifact with match overview and at least one category of meaningful replay-derived event.
  - Update findings with evidence-backed recommendations for Phase 6 scope.
  - Decide whether Phase 6 should proceed with Clarity, a different parser strategy, or replay-intelligence postponement.

- Non-Goals:
  - Implement Phase 6 replay intelligence.
  - Build teamfight detection.
  - Build hero-specific replay coaching.
  - Build frontend timeline UI.
  - Commit `.dem` files or large parser outputs.

## 3. Proposed Architecture

Treat this as a validation spike, not a product feature. Work stays on its own branch and ends with documentation plus a small parser proof if successful.

```txt
Real local .dem file (not committed)
↓
Java parser CLI with Clarity instrumentation
↓
Discover accessible event/message/property types
↓
Emit limited real normalized artifact
↓
Python wrapper smoke check
↓
Findings doc decides Phase 6 readiness
```

## 4. Component Breakdown

- Parser instrumentation:
  - Log or sample Clarity message/property types safely.
  - Keep output bounded and redacted.

- Normalized artifact proof:
  - Replace placeholder-only output with real fields only where verified.
  - Preserve app-owned JSON schema.

- Findings:
  - Document replay file characteristics, commands, event categories found, blockers, and next recommendations.

## 5. Data Flow

```txt
Developer provides LOCAL_REPLAY_SAMPLE_PATH
↓
Parser CLI reads file locally
↓
Clarity handlers inspect accessible messages/properties
↓
CLI emits normalized JSON to stdout
↓
Python subprocess wrapper validates JSON
↓
Findings doc records evidence and readiness decision
```

## 6. Interface Contracts

No public API interfaces should change.

Optional parser CLI debug flags:

```bash
replay-parser --input /path/to/match.dem --pretty --max-events 500 --debug-discovery
```

Output must remain compatible with Phase 2.5 normalized artifact shape:

- `schema_version`
- `parser`
- `match`
- `players`
- `timeline`
- `raw_metadata`
- `warnings`

## 7. File Changes

- Create:
  - `docs/phase-6-replay-intelligence-readiness-findings.md` — validation results.

- Modify only if needed:
  - `apps/replay-parser/src/main/java/.../ClarityReplayParser.java` — discovery instrumentation and verified real extraction.
  - `apps/replay-parser/src/main/java/.../ReplayParserCli.java` — optional debug flag.
  - `apps/replay-parser/src/test/...` — CLI/debug flag tests.
  - `docs/phase-2.5-clarity-findings.md` — link to readiness findings.

- Delete:
  - None.

## 8. Implementation Phases

Branching rule:

- Branch: `spike/phase-6-replay-intelligence-validation`
- This is not the Phase 6 implementation branch.

### Gate 6A — Real Replay Discovery

- Branch: `spike/phase-6-replay-intelligence-validation`
- Commits:
  - [ ] Add bounded debug discovery flag if needed.
  - [ ] Run parser against one real local Deadlock `.dem` file.
  - [ ] Record accessible event/message/property categories.
- Done when:
  - There is written evidence of what Clarity can/cannot expose for Deadlock.

### Gate 6B — Minimal Real Extraction Proof

- Commits:
  - [ ] Extract at least one verified real event category or match/player field.
  - [ ] Preserve normalized schema and warnings.
  - [ ] Add parser tests for the extraction code using fixtures/mocks where possible.
- Done when:
  - Parser output is not placeholder-only for the validated replay.

### Gate 6C — Readiness Decision

- Commits:
  - [ ] Add Phase 6 readiness findings doc.
  - [ ] Recommend one of: proceed with Clarity, change parser strategy, or postpone Phase 6.
- Done when:
  - Phase 6 implementation can be scoped from verified replay data, not assumptions.

## 9. Testing Strategy

- Unit tests:
  - CLI debug flag parsing.
  - Normalized artifact shape remains valid.
  - Extraction helpers handle missing fields.

- Manual smoke tests:
  - Run parser against a local `.dem` file.
  - Run Python wrapper against the built CLI.

- Validation before any Phase 6 implementation:
  - `cd apps/replay-parser && gradle test`
  - `cd apps/replay-parser && gradle installDist`
  - `build/install/replay-parser/bin/replay-parser --input "$LOCAL_REPLAY_SAMPLE_PATH" --pretty --max-events 500`
  - `cd apps/api && uv run pytest tests/test_replay_parser_service.py -v`

## 10. Security Implications

- Replay files are local developer artifacts and must not be committed.
- Debug discovery output may contain account IDs or match metadata; keep logs local and summarized in docs.
- Preserve existing subprocess/path safety from Phase 2.5.

## 11. Risks & Tradeoffs

| Risk | Mitigation |
|---|---|
| Clarity cannot parse Deadlock replay structure well enough | Stop Phase 6 and investigate alternatives before product implementation. |
| Debug output is huge/noisy | Add max-event caps and summarize findings manually. |
| Real replay fixture cannot be committed | Use local smoke instructions and mocked/unit fixtures for committed tests. |
| We overfit to one replay | Treat one replay as minimum gate; use more samples before broad Phase 6 implementation. |

## 12. Open Questions

All questions must be resolved or accepted as risks before Phase 6 implementation begins.

1. Do you have one or more local Deadlock `.dem` files available for validation?
2. What minimum real data is enough to green-light Phase 6: players only, item progression, deaths, ability casts, damage events, or objectives?
3. Should validation happen before or after Phases 3-5? Recommended: can happen in parallel as a spike, but do not implement Phase 6 until validated.
