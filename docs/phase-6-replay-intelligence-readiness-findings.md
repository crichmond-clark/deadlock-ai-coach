# Phase 6 Replay Intelligence Readiness Findings

Status: validation gate tooling added; real replay validation still required.

## What changed in this spike

- Added `--debug-discovery` to the Java replay parser CLI.
- Debug mode preserves the `deadlock-replay-parse-v1` artifact shape.
- Debug mode emits bounded file-level discovery metadata:
  - `capabilities.debug_discovery=true`
  - `capabilities.sample_bytes`
  - `capabilities.first_bytes_hex`
  - `capabilities.validated_real_events=[]`
- Added parser tests covering the debug flag and schema-compatible output.

## Current evidence

The committed parser still does **not** prove Clarity can extract Deadlock replay events. The debug flag is intentionally conservative: it verifies local file access, bounded sampling, hashing, JSON shape, and Python-wrapper compatibility, but it does not claim match/player/timeline extraction.

## Local validation command

With a real local `.dem` file that is not committed:

```bash
cd apps/replay-parser
gradle test
gradle installDist
build/install/replay-parser/bin/replay-parser \
  --input "$LOCAL_REPLAY_SAMPLE_PATH" \
  --pretty \
  --max-events 500 \
  --debug-discovery
```

Then run the Python subprocess wrapper tests:

```bash
cd apps/api
uv run pytest tests/test_replay_parser_service.py -v
```

## Readiness decision

**Decision: do not start Phase 6 implementation yet.**

Proceed only after at least one real Deadlock replay produces verified replay-derived data beyond file metadata. Minimum acceptable proof should include one or more of:

- match ID / duration / tick count from replay data,
- player slot or hero identity from replay data,
- death/combat/objective/timeline event category,
- item/build progression event category.

## Recommended next step

Wire real Clarity processors/listeners in `ClarityReplayParser`, run debug discovery on one or more local replays, and update this findings file with exact event/message/property categories observed.
