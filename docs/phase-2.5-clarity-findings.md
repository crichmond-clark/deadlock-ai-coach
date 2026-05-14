# Phase 2.5 Clarity Findings

Status: initial implementation.

## Current result

- Java CLI skeleton emits `deadlock-replay-parse-v1` placeholder JSON.
- Python/API/worker integration can call a configured parser through subprocess and persist artifacts.
- Real Clarity extraction has not been verified yet because no local Deadlock replay has been parsed in this session.

## Reliable fields so far

- Source filename, file size, SHA-256 from local file metadata.
- Parser/app metadata from the CLI boundary.
- Warning and stats fields in the normalized schema.

## Unverified/unavailable fields

- Match ID, duration, tick count, winning team.
- Player/account/hero/team extraction.
- Timeline/combat log events.
- Entity sampling and Clarity capability coverage for Deadlock.

## Recommendation

No go/no-go decision yet. Build the parser with `gradle installDist`, parse one real `.dem`, then update this file with the real Clarity coverage before Phase 3 structured AI analysis relies on replay artifacts.
