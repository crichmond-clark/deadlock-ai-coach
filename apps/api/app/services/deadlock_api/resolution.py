"""Asset resolution service — resolves hero/item/ability IDs from local DB cache."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.game_asset import GameAsset
from app.db.models.hero_asset import HeroAsset


@dataclass
class ResolvedHero:
    id: int
    name: str | None = None
    class_name: str | None = None
    image_url: str | None = None
    raw_payload: dict[str, Any] | None = None
    resolved: bool = False


@dataclass
class ResolvedGameAsset:
    id: int
    name: str | None = None
    class_name: str | None = None
    asset_kind: str | None = None
    image_url: str | None = None
    raw_payload: dict[str, Any] | None = None
    resolved: bool = False


def _unresolved_hero(hero_id: int) -> ResolvedHero:
    return ResolvedHero(id=hero_id)


def _unresolved_asset(asset_id: int) -> ResolvedGameAsset:
    return ResolvedGameAsset(id=asset_id)


async def resolve_hero(db: AsyncSession, hero_id: int) -> ResolvedHero:
    """Resolve a hero ID from the local catalog.  Returns unresolved placeholder on miss."""
    result = await db.execute(select(HeroAsset).where(HeroAsset.id == hero_id))
    row = result.scalar_one_or_none()
    if row is None:
        return _unresolved_hero(hero_id)
    return ResolvedHero(
        id=row.id,
        name=row.name,
        class_name=row.class_name,
        image_url=row.image_url,
        raw_payload=row.raw_payload,
        resolved=True,
    )


async def resolve_game_asset(db: AsyncSession, asset_id: int) -> ResolvedGameAsset:
    """Resolve a game asset ID (item/ability/upgrade) from the local catalog."""
    result = await db.execute(select(GameAsset).where(GameAsset.id == asset_id))
    row = result.scalar_one_or_none()
    if row is None:
        return _unresolved_asset(asset_id)
    return ResolvedGameAsset(
        id=row.id,
        name=row.name,
        class_name=row.class_name,
        asset_kind=row.asset_kind,
        image_url=row.image_url,
        raw_payload=row.raw_payload,
        resolved=True,
    )


async def resolve_heroes_bulk(db: AsyncSession, hero_ids: set[int]) -> dict[int, ResolvedHero]:
    """Resolve multiple hero IDs in one query."""
    if not hero_ids:
        return {}
    result = await db.execute(select(HeroAsset).where(HeroAsset.id.in_(hero_ids)))
    rows = {row.id: row for row in result.scalars().all()}
    resolved: dict[int, ResolvedHero] = {}
    for hid in hero_ids:
        row = rows.get(hid)
        if row is None:
            resolved[hid] = _unresolved_hero(hid)
        else:
            resolved[hid] = ResolvedHero(
                id=row.id,
                name=row.name,
                class_name=row.class_name,
                image_url=row.image_url,
                raw_payload=row.raw_payload,
                resolved=True,
            )
    return resolved


async def resolve_game_assets_bulk(db: AsyncSession, asset_ids: set[int]) -> dict[int, ResolvedGameAsset]:
    """Resolve multiple game asset IDs in one query."""
    if not asset_ids:
        return {}
    result = await db.execute(select(GameAsset).where(GameAsset.id.in_(asset_ids)))
    rows = {row.id: row for row in result.scalars().all()}
    resolved: dict[int, ResolvedGameAsset] = {}
    for aid in asset_ids:
        row = rows.get(aid)
        if row is None:
            resolved[aid] = _unresolved_asset(aid)
        else:
            resolved[aid] = ResolvedGameAsset(
                id=row.id,
                name=row.name,
                class_name=row.class_name,
                asset_kind=row.asset_kind,
                image_url=row.image_url,
                raw_payload=row.raw_payload,
                resolved=True,
            )
    return resolved
