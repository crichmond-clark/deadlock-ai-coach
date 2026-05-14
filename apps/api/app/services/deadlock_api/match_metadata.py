"""Match metadata service — fetch, cache, and summarize Deadlock match data."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.external_match_metadata import ExternalMatchMetadata
from app.schemas.match_metadata import MatchMetadataSummary, MatchPlayerSummary
from app.services.deadlock_api.client import DeadlockGameAPIClient


def _now() -> datetime:
    return datetime.now(UTC)


def _normalize_players(raw_players: list[dict]) -> list[MatchPlayerSummary]:
    summaries: list[MatchPlayerSummary] = []
    for p in raw_players:
        summaries.append(
            MatchPlayerSummary(
                account_id=p.get("account_id"),
                player_slot=p.get("player_slot", 0),
                hero_id=p.get("hero_id"),
                team=p.get("team"),
                assigned_lane=p.get("assigned_lane"),
                kills=p.get("kills"),
                deaths=p.get("deaths"),
                assists=p.get("assists"),
                net_worth=p.get("net_worth"),
                last_hits=p.get("last_hits"),
                denies=p.get("denies"),
                level=p.get("level"),
            )
        )
    return summaries


def normalize_match_metadata(raw: dict) -> MatchMetadataSummary:
    """Extract a small normalized summary from raw API match metadata."""
    players_raw = raw.get("players") if isinstance(raw.get("players"), list) else []
    return MatchMetadataSummary(
        match_id=raw.get("match_id", 0),
        duration_s=raw.get("duration_s"),
        start_time=raw.get("start_time"),
        game_mode=raw.get("game_mode"),
        winning_team=raw.get("winning_team"),
        average_badge_team0=raw.get("average_badge_team0"),
        average_badge_team1=raw.get("average_badge_team1"),
        players=_normalize_players(players_raw),
    )


async def fetch_and_cache_match_metadata(
    db: AsyncSession,
    match_id: int,
    *,
    client: DeadlockGameAPIClient | None = None,
    force: bool = False,
) -> MatchMetadataSummary:
    """Fetch match metadata from the Deadlock API, cache it, and return the summary.

    Returns cached data if already present unless *force* is True.
    """
    if not force:
        result = await db.execute(
            select(ExternalMatchMetadata).where(ExternalMatchMetadata.match_id == match_id)
        )
        cached = result.scalar_one_or_none()
        if cached is not None and _is_cache_fresh(cached.fetched_at):
            return MatchMetadataSummary.model_validate(cached.summary)

    _client = client or DeadlockGameAPIClient()
    raw = await _client.get_match_metadata(match_id)
    summary = normalize_match_metadata(raw)

    now = _now()
    stmt = (
        pg_insert(ExternalMatchMetadata)
        .values(
            match_id=match_id,
            raw_payload=raw,
            summary=summary.model_dump(),
            fetched_at=now,
        )
        .on_conflict_do_update(
            index_elements=["match_id"],
            set_={
                "raw_payload": raw,
                "summary": summary.model_dump(),
                "fetched_at": now,
            },
        )
    )
    await db.execute(stmt)
    await db.flush()

    return summary


def _is_cache_fresh(fetched_at: datetime) -> bool:
    ttl = settings.deadlock_api_cache_ttl_minutes * 60
    age = (_now() - fetched_at).total_seconds()
    return age < ttl
