"""Tests for match metadata fetch, cache, and normalization."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.db.models.external_match_metadata import ExternalMatchMetadata
from app.schemas.match_metadata import MatchMetadataSummary
from app.services.deadlock_api.match_metadata import (
    _is_cache_fresh,
    fetch_and_cache_match_metadata,
    normalize_match_metadata,
)
from tests.fixtures.deadlock_api import MATCH_METADATA

# ── Normalization ─────────────────────────────────────────────────────


def test_normalize_match_metadata():
    summary = normalize_match_metadata(MATCH_METADATA)
    assert summary.match_id == 44009651
    assert summary.duration_s == 1800
    assert summary.winning_team == 2
    assert len(summary.players) == 2
    assert summary.source == "api"

    p0 = summary.players[0]
    assert p0.hero_id == 63
    assert p0.kills == 8

    p1 = summary.players[1]
    assert p1.account_id is None
    assert p1.hero_id == 1


def test_normalize_match_metadata_empty_players():
    summary = normalize_match_metadata({"match_id": 1})
    assert summary.players == []


# ── Cache freshness ───────────────────────────────────────────────────


def test_cache_fresh():
    now = datetime.now(UTC)
    assert _is_cache_fresh(now) is True


def test_cache_stale():
    with patch("app.services.deadlock_api.match_metadata.settings") as mock_settings:
        mock_settings.deadlock_api_cache_ttl_minutes = 1
        stale = datetime.now(UTC) - timedelta(minutes=2)
        assert _is_cache_fresh(stale) is False


# ── Fetch and cache ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_fetch_and_cache_hit():
    db = AsyncMock()
    mock_client = AsyncMock()
    mock_client.get_match_metadata.return_value = MATCH_METADATA

    # Simulate cache miss
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_result

    summary = await fetch_and_cache_match_metadata(db, 44009651, client=mock_client)
    assert summary.match_id == 44009651
    assert summary.duration_s == 1800
    # Should have called insert and flush
    assert db.execute.call_count >= 2


@pytest.mark.asyncio
async def test_fetch_and_cache_cached():
    db = AsyncMock()
    mock_client = AsyncMock()

    cached = MagicMock(spec=ExternalMatchMetadata)
    cached.fetched_at = datetime.now(UTC)
    cached.summary = MatchMetadataSummary(
        match_id=44009651, duration_s=1800, players=[]
    ).model_dump()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = cached
    db.execute.return_value = mock_result

    summary = await fetch_and_cache_match_metadata(db, 44009651, client=mock_client)
    assert summary.match_id == 44009651
    mock_client.get_match_metadata.assert_not_called()


@pytest.mark.asyncio
async def test_fetch_and_cache_force():
    db = AsyncMock()
    mock_client = AsyncMock()
    mock_client.get_match_metadata.return_value = MATCH_METADATA

    cached = MagicMock(spec=ExternalMatchMetadata)
    cached.fetched_at = datetime.now(UTC)
    cached.summary = {}

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = cached
    db.execute.return_value = mock_result

    summary = await fetch_and_cache_match_metadata(db, 44009651, client=mock_client, force=True)
    assert summary.match_id == 44009651
    mock_client.get_match_metadata.assert_called_once()
