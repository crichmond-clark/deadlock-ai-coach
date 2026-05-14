"""Tests for asset catalog sync and resolution services."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.db.models.game_asset import GameAsset
from app.db.models.hero_asset import HeroAsset
from app.services.deadlock_api.assets import (
    sync_asset_catalog,
    sync_game_asset_catalog,
    sync_hero_catalog,
)
from app.services.deadlock_api.resolution import (
    resolve_game_asset,
    resolve_game_assets_bulk,
    resolve_hero,
    resolve_heroes_bulk,
)
from tests.fixtures.deadlock_api import HEROES_LIST, ITEMS_LIST


@pytest.fixture
def mock_assets_client():
    client = AsyncMock()
    client.list_heroes.return_value = HEROES_LIST
    client.list_items.return_value = ITEMS_LIST
    return client


def _make_hero_row(hero_id: int, name: str | None = None, class_name: str | None = None):
    row = MagicMock(spec=HeroAsset)
    row.id = hero_id
    row.name = name
    row.class_name = class_name
    row.image_url = None
    row.raw_payload = {}
    return row


def _make_asset_row(asset_id: int, name: str | None = None, asset_kind: str | None = None):
    row = MagicMock(spec=GameAsset)
    row.id = asset_id
    row.name = name
    row.class_name = None
    row.asset_kind = asset_kind
    row.image_url = None
    row.raw_payload = {}
    return row


# ── Catalog sync ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sync_hero_catalog(mock_assets_client):
    db = AsyncMock()
    count, errors = await sync_hero_catalog(db, client=mock_assets_client)
    assert count == 2
    assert errors == []
    assert db.execute.call_count == 2


@pytest.mark.asyncio
async def test_sync_hero_catalog_update_existing(mock_assets_client):
    mock_assets_client.list_heroes.return_value = [{"hero_id": 63, "name": "Mina (updated)"}]
    db = AsyncMock()
    count, errors = await sync_hero_catalog(db, client=mock_assets_client)
    assert count == 1
    assert errors == []


@pytest.mark.asyncio
async def test_sync_game_asset_catalog(mock_assets_client):
    db = AsyncMock()
    count, errors = await sync_game_asset_catalog(db, client=mock_assets_client)
    assert count == 3
    assert errors == []
    assert db.execute.call_count == 3


@pytest.mark.asyncio
async def test_sync_asset_catalog_full(mock_assets_client):
    db = AsyncMock()
    result = await sync_asset_catalog(db, client=mock_assets_client)
    assert result.heroes_upserted == 2
    assert result.game_assets_upserted == 3
    assert result.errors == []


@pytest.mark.asyncio
async def test_sync_hero_catalog_fetch_error(mock_assets_client):
    mock_assets_client.list_heroes.side_effect = RuntimeError("network down")
    db = AsyncMock()
    count, errors = await sync_hero_catalog(db, client=mock_assets_client)
    assert count == 0
    assert len(errors) == 1
    assert "network down" in errors[0]


# ── Resolution ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_resolve_hero_cached():
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = _make_hero_row(63, "Mina", "CitadelHero_Mina")
    db.execute.return_value = mock_result

    hero = await resolve_hero(db, 63)
    assert hero.resolved is True
    assert hero.name == "Mina"
    assert hero.class_name == "CitadelHero_Mina"


@pytest.mark.asyncio
async def test_resolve_hero_missing_returns_unresolved():
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_result

    hero = await resolve_hero(db, 99999)
    assert hero.resolved is False
    assert hero.id == 99999
    assert hero.name is None


@pytest.mark.asyncio
async def test_resolve_game_asset_cached():
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = _make_asset_row(1233782561, "Love Bites", "ability")
    db.execute.return_value = mock_result

    asset = await resolve_game_asset(db, 1233782561)
    assert asset.resolved is True
    assert asset.name == "Love Bites"
    assert asset.asset_kind == "ability"


@pytest.mark.asyncio
async def test_resolve_game_asset_missing_returns_unresolved():
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_result

    asset = await resolve_game_asset(db, 88888)
    assert asset.resolved is False
    assert asset.id == 88888


@pytest.mark.asyncio
async def test_resolve_heroes_bulk():
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [
        _make_hero_row(63, "Mina"),
        _make_hero_row(1, "Abrams"),
    ]
    db.execute.return_value = mock_result

    resolved = await resolve_heroes_bulk(db, {63, 1, 99999})
    assert resolved[63].resolved is True
    assert resolved[63].name == "Mina"
    assert resolved[1].resolved is True
    assert resolved[1].name == "Abrams"
    assert resolved[99999].resolved is False


@pytest.mark.asyncio
async def test_resolve_game_assets_bulk():
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [
        _make_asset_row(1233782561, "Love Bites", "ability"),
    ]
    db.execute.return_value = mock_result

    resolved = await resolve_game_assets_bulk(db, {1233782561, 88888})
    assert resolved[1233782561].resolved is True
    assert resolved[1233782561].asset_kind == "ability"
    assert resolved[88888].resolved is False


@pytest.mark.asyncio
async def test_resolve_heroes_bulk_empty():
    db = AsyncMock()
    resolved = await resolve_heroes_bulk(db, set())
    assert resolved == {}
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_resolve_game_assets_bulk_empty():
    db = AsyncMock()
    resolved = await resolve_game_assets_bulk(db, set())
    assert resolved == {}
    db.execute.assert_not_called()
