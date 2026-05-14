"""Tests for enrichment service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.match_metadata import MatchMetadataSummary, MatchPlayerSummary
from app.services.deadlock_api.enrichment import (
    _build_source_warnings,
    _extract_asset_ids_from_replay,
    _extract_hero_ids_from_replay,
    enrich_match_context,
)
from app.services.deadlock_api.resolution import ResolvedHero

# ── ID extraction ─────────────────────────────────────────────────────


def test_extract_hero_ids_from_replay():
    artifact = {"players": [{"hero_id": 63}, {"hero_id": 1}, {"hero_id": None}]}
    assert _extract_hero_ids_from_replay(artifact) == {63, 1}


def test_extract_hero_ids_from_replay_empty():
    assert _extract_hero_ids_from_replay(None) == set()
    assert _extract_hero_ids_from_replay({}) == set()


def test_extract_asset_ids_from_replay():
    artifact = {
        "timeline": [
            {"ability_id": 1233782561},
            {"item_id": 24215179},
            {},
        ]
    }
    assert _extract_asset_ids_from_replay(artifact) == {1233782561, 24215179}


def test_extract_asset_ids_from_replay_empty():
    assert _extract_asset_ids_from_replay(None) == set()


# ── Warnings ──────────────────────────────────────────────────────────


def test_build_source_warnings_no_sources():
    warnings = _build_source_warnings(api_ok=False, replay_ok=False, unresolved_heroes=set(), unresolved_assets=set())
    assert any(w.code == "no_sources" for w in warnings)


def test_build_source_warnings_unresolved():
    warnings = _build_source_warnings(api_ok=True, replay_ok=True, unresolved_heroes={63}, unresolved_assets={999})
    codes = {w.code for w in warnings}
    assert "unresolved_hero" in codes
    assert "unresolved_asset" in codes
    assert "no_sources" not in codes


# ── Enrichment ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_enrich_replay_only():
    """Enrichment with a replay artifact but no match_id → replay_only mode."""
    db = AsyncMock()

    # Mock replay artifact
    ra = MagicMock()
    ra.id = "00000000-0000-0000-0000-000000000001"
    ra.artifact = {"match": {}, "players": [{"hero_id": 63}], "timeline": []}
    mock_select_result = MagicMock()
    mock_select_result.scalar_one_or_none.return_value = ra
    db.execute.return_value = mock_select_result

    # Mock resolution
    with patch("app.services.deadlock_api.enrichment.resolve_heroes_bulk") as mock_heroes:
        mock_heroes.return_value = {63: ResolvedHero(id=63, name="Mina", class_name="Hero", resolved=True)}
        with patch("app.services.deadlock_api.enrichment.resolve_game_assets_bulk") as mock_assets:
            mock_assets.return_value = {}

            context = await enrich_match_context(db, replay_artifact_id=ra.id)

    assert context.source_mode == "replay_only"
    assert context.metadata_summary is None
    assert 63 in context.resolved_heroes
    assert context.resolved_heroes[63].name == "Mina"


@pytest.mark.asyncio
async def test_enrich_api_only():
    """Enrichment with match_id but no replay → api_only mode."""
    db = AsyncMock()

    # Mock fetch_and_cache
    with patch("app.services.deadlock_api.enrichment.fetch_and_cache_match_metadata") as mock_fetch:
        mock_fetch.return_value = MatchMetadataSummary(
            match_id=44009651,
            duration_s=1800,
            players=[MatchPlayerSummary(player_slot=0, hero_id=63, kills=5, deaths=2, assists=10)],
        )
        with patch("app.services.deadlock_api.enrichment.resolve_heroes_bulk") as mock_heroes:
            mock_heroes.return_value = {63: ResolvedHero(id=63, name="Mina", class_name="Hero", resolved=True)}
            with patch("app.services.deadlock_api.enrichment.resolve_game_assets_bulk") as mock_assets:
                mock_assets.return_value = {}

                context = await enrich_match_context(db, match_id=44009651)

    assert context.source_mode == "api_only"
    assert context.metadata_summary is not None
    assert len(context.resolved_players) == 1
    assert context.resolved_players[0].hero.name == "Mina"


@pytest.mark.asyncio
async def test_enrich_api_failure_non_fatal():
    """API failure with replay data should still produce replay_only context."""
    db = AsyncMock()

    ra = MagicMock()
    ra.id = "00000000-0000-0000-0000-000000000001"
    ra.artifact = {"match": {"match_id": 123}, "players": [], "timeline": []}
    mock_select_result = MagicMock()
    mock_select_result.scalar_one_or_none.return_value = ra
    db.execute.return_value = mock_select_result

    with (
        patch("app.services.deadlock_api.enrichment.fetch_and_cache_match_metadata", side_effect=RuntimeError("api down")),
        patch("app.services.deadlock_api.enrichment.resolve_heroes_bulk", return_value={}),
        patch("app.services.deadlock_api.enrichment.resolve_game_assets_bulk", return_value={}),
    ):
        context = await enrich_match_context(db, replay_artifact_id=ra.id, match_id=123)

    assert context.source_mode == "replay_only"
    assert context.metadata_summary is None
