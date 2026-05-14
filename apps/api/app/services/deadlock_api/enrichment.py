"""Enrichment service — combines replay artifacts and API metadata into EnrichedMatchContext."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.replay_parse_artifact import ReplayParseArtifact
from app.schemas.enriched_match import EnrichedMatchContext, ResolvedPlayer, SourceWarning
from app.schemas.match_metadata import MatchMetadataSummary
from app.services.deadlock_api.match_metadata import fetch_and_cache_match_metadata
from app.services.deadlock_api.resolution import (
    ResolvedGameAsset as ServiceResolvedAsset,
)
from app.services.deadlock_api.resolution import (
    ResolvedHero as ServiceResolvedHero,
)
from app.services.deadlock_api.resolution import (
    resolve_game_assets_bulk,
    resolve_heroes_bulk,
)


def _convert_hero(sh: ServiceResolvedHero) -> dict[str, Any]:
    return {
        "id": sh.id,
        "name": sh.name,
        "class_name": sh.class_name,
        "image_url": sh.image_url,
        "raw_payload": sh.raw_payload,
        "resolved": sh.resolved,
    }


def _convert_asset(sa: ServiceResolvedAsset) -> dict[str, Any]:
    return {
        "id": sa.id,
        "name": sa.name,
        "class_name": sa.class_name,
        "asset_kind": sa.asset_kind,
        "image_url": sa.image_url,
        "raw_payload": sa.raw_payload,
        "resolved": sa.resolved,
    }


def _hero_from_api_player(player: MatchMetadataSummary, hero_map: dict[int, ServiceResolvedHero]) -> dict | None:
    hid = player.hero_id
    if hid is not None and hid in hero_map:
        return _convert_hero(hero_map[hid])
    return None


def _build_source_warnings(
    api_ok: bool,
    replay_ok: bool,
    unresolved_heroes: set[int],
    unresolved_assets: set[int],
) -> list[SourceWarning]:
    warnings: list[SourceWarning] = []
    if not api_ok and not replay_ok:
        warnings.append(SourceWarning(source="enrichment", code="no_sources", message="neither replay nor API data available"))
    elif not api_ok and replay_ok:
        pass  # replay-only is fine
    elif api_ok and not replay_ok:
        pass  # api-only is fine
    for hid in unresolved_heroes:
        warnings.append(SourceWarning(source="enrichment", code="unresolved_hero", message=f"hero_id {hid} not found in catalog"))
    for aid in unresolved_assets:
        warnings.append(SourceWarning(source="enrichment", code="unresolved_asset", message=f"asset_id {aid} not found in catalog"))
    return warnings


def _extract_hero_ids_from_replay(artifact: dict[str, Any] | None) -> set[int]:
    ids: set[int] = set()
    if not artifact:
        return ids
    players = artifact.get("players") or []
    for p in players:
        hid = p.get("hero_id")
        if isinstance(hid, int):
            ids.add(hid)
    return ids


def _extract_asset_ids_from_replay(artifact: dict[str, Any] | None) -> set[int]:
    ids: set[int] = set()
    if not artifact:
        return ids
    timeline = artifact.get("timeline") or []
    for event in timeline:
        aid = event.get("asset_id") or event.get("item_id") or event.get("ability_id")
        if isinstance(aid, int):
            ids.add(aid)
    return ids


async def enrich_match_context(
    db: AsyncSession,
    *,
    match_id: int | None = None,
    replay_artifact_id: uuid.UUID | None = None,
) -> EnrichedMatchContext:
    """Build an EnrichedMatchContext from available replay and/or API data."""
    replay_ok = False
    api_ok = False
    metadata_summary: MatchMetadataSummary | None = None
    api_metadata_id: str | None = None
    hero_ids: set[int] = set()
    asset_ids: set[int] = set()

    # 1. Load replay artifact if available
    if replay_artifact_id is not None:
        result = await db.execute(select(ReplayParseArtifact).where(ReplayParseArtifact.id == replay_artifact_id))
        ra = result.scalar_one_or_none()
        if ra is not None and ra.artifact:
            replay_ok = True
            artifact = ra.artifact
            hero_ids |= _extract_hero_ids_from_replay(artifact)
            asset_ids |= _extract_asset_ids_from_replay(artifact)
            # Use replay's match_id if available and none was provided
            if match_id is None:
                mid = artifact.get("match", {}).get("match_id")
                if isinstance(mid, int):
                    match_id = mid

    # 2. Fetch API metadata if match_id is available
    try:
        if match_id is not None:
            metadata_summary = await fetch_and_cache_match_metadata(db, match_id)
            api_ok = True
            # Extract hero IDs from API metadata
            for p in metadata_summary.players:
                if p.hero_id is not None:
                    hero_ids.add(p.hero_id)
    except Exception:
        pass  # API failure is non-fatal when replay data exists

    # Safety: if the fetch call didn't set api_metadata_id, we leave it None
    # (the caller can set it later)

    # 3. Resolve heroes
    heroes_map = await resolve_heroes_bulk(db, hero_ids)
    resolved_heroes = {hid: _convert_hero(h) for hid, h in heroes_map.items()}
    unresolved_heroes = {hid for hid, h in heroes_map.items() if not h.resolved}

    # 4. Resolve game assets
    assets_map = await resolve_game_assets_bulk(db, asset_ids)
    resolved_assets = {aid: _convert_asset(a) for aid, a in assets_map.items()}
    unresolved_assets = {aid for aid, a in assets_map.items() if not a.resolved}

    # 5. Build resolved players from API metadata
    resolved_players: list[ResolvedPlayer] = []
    if metadata_summary is not None:
        for p in metadata_summary.players:
            hero_data = _hero_from_api_player(p, heroes_map)
            resolved_players.append(
                ResolvedPlayer(
                    account_id=p.account_id,
                    player_slot=p.player_slot,
                    hero=hero_data,
                    team=p.team,
                    assigned_lane=p.assigned_lane,
                    kills=p.kills,
                    deaths=p.deaths,
                    assists=p.assists,
                    net_worth=p.net_worth,
                    last_hits=p.last_hits,
                    denies=p.denies,
                    level=p.level,
                )
            )

    # 6. Determine source mode
    if replay_ok and api_ok:
        source_mode = "replay_plus_api"
    elif api_ok:
        source_mode = "api_only"
    else:
        source_mode = "replay_only"

    # 7. Build warnings
    warnings = _build_source_warnings(api_ok, replay_ok, unresolved_heroes, unresolved_assets)

    return EnrichedMatchContext(
        match_id=match_id,
        replay_artifact_id=str(replay_artifact_id) if replay_artifact_id else None,
        api_metadata_id=api_metadata_id,
        metadata_summary=metadata_summary,
        resolved_heroes=resolved_heroes,
        resolved_assets=resolved_assets,
        resolved_players=resolved_players,
        source_mode=source_mode,
        warnings=warnings,
    )
