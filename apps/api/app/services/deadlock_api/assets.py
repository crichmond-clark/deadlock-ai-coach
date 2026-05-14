"""Asset catalog sync helpers — fetch and cache heroes/items from Deadlock Assets API."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.game_asset import GameAsset
from app.db.models.hero_asset import HeroAsset
from app.services.deadlock_api.client import DeadlockAssetsAPIClient


@dataclass
class CatalogSyncResult:
    heroes_upserted: int = 0
    game_assets_upserted: int = 0
    errors: list[str] = None

    def __post_init__(self) -> None:
        if self.errors is None:
            self.errors = []


def _now() -> datetime:
    return datetime.now(UTC)


def _clean_text(value: str | None, max_length: int = 500) -> str | None:
    if value is None:
        return None
    if len(value) > max_length:
        return value[: max_length - 1] + "…"
    return value


async def sync_hero_catalog(
    db: AsyncSession,
    *,
    client: DeadlockAssetsAPIClient | None = None,
) -> tuple[int, list[str]]:
    """Fetch /v2/heroes and upsert into the heroes table.  Returns (upserted, errors)."""
    _client = client or DeadlockAssetsAPIClient()
    errors: list[str] = []
    try:
        heroes = await _client.list_heroes()
    except Exception as exc:
        return 0, [f"failed to fetch hero catalog: {exc}"]

    count = 0
    now = _now()
    for entry in heroes:
        hero_id = entry.get("hero_id")
        if not isinstance(hero_id, int):
            errors.append(f"hero entry missing integer hero_id: {entry}")
            continue
        stmt = (
            pg_insert(HeroAsset)
            .values(
                id=hero_id,
                name=_clean_text(entry.get("name")),
                class_name=_clean_text(entry.get("class_name")),
                image_url=_clean_text(entry.get("image_url")),
                raw_payload=entry,
                fetched_at=now,
            )
            .on_conflict_do_update(
                index_elements=["id"],
                set_={
                    "name": _clean_text(entry.get("name")),
                    "class_name": _clean_text(entry.get("class_name")),
                    "image_url": _clean_text(entry.get("image_url")),
                    "raw_payload": entry,
                    "fetched_at": now,
                },
            )
        )
        await db.execute(stmt)
        count += 1
    return count, errors


async def sync_game_asset_catalog(
    db: AsyncSession,
    *,
    client: DeadlockAssetsAPIClient | None = None,
) -> tuple[int, list[str]]:
    """Fetch /v2/items and upsert into game_assets.  Returns (upserted, errors)."""
    _client = client or DeadlockAssetsAPIClient()
    errors: list[str] = []
    try:
        items = await _client.list_items()
    except Exception as exc:
        return 0, [f"failed to fetch item catalog: {exc}"]

    count = 0
    now = _now()
    for entry in items:
        item_id = entry.get("id")
        if not isinstance(item_id, int):
            errors.append(f"item entry missing integer id: {entry}")
            continue
        kind = entry.get("item_type") or entry.get("type") or "unknown"
        stmt = (
            pg_insert(GameAsset)
            .values(
                id=item_id,
                name=_clean_text(entry.get("name")),
                class_name=_clean_text(entry.get("class_name")),
                asset_kind=_clean_text(kind, max_length=50),
                image_url=_clean_text(entry.get("image_url")),
                raw_payload=entry,
                fetched_at=now,
            )
            .on_conflict_do_update(
                index_elements=["id"],
                set_={
                    "name": _clean_text(entry.get("name")),
                    "class_name": _clean_text(entry.get("class_name")),
                    "asset_kind": _clean_text(kind, max_length=50),
                    "image_url": _clean_text(entry.get("image_url")),
                    "raw_payload": entry,
                    "fetched_at": now,
                },
            )
        )
        await db.execute(stmt)
        count += 1
    return count, errors


async def sync_asset_catalog(
    db: AsyncSession,
    *,
    client: DeadlockAssetsAPIClient | None = None,
) -> CatalogSyncResult:
    """Convenience wrapper: sync both heroes and game_assets."""
    result = CatalogSyncResult()
    _client = client or DeadlockAssetsAPIClient()

    count, errs = await sync_hero_catalog(db, client=_client)
    result.heroes_upserted = count
    result.errors.extend(errs)

    count, errs = await sync_game_asset_catalog(db, client=_client)
    result.game_assets_upserted = count
    result.errors.extend(errs)

    return result
