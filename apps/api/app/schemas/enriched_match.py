"""Enriched match context schemas — combines replay + API data for AI analysis."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from app.schemas.match_metadata import MatchMetadataSummary


class SourceWarning(BaseModel):
    source: Literal["api", "replay", "enrichment"]
    code: str
    message: str


class ResolvedHero(BaseModel):
    id: int
    name: str | None = None
    class_name: str | None = None
    image_url: str | None = None
    raw_payload: dict | None = None
    resolved: bool = False


class ResolvedGameAsset(BaseModel):
    id: int
    name: str | None = None
    class_name: str | None = None
    asset_kind: str | None = None
    image_url: str | None = None
    raw_payload: dict | None = None
    resolved: bool = False


class ResolvedPlayer(BaseModel):
    account_id: int | None = None
    player_slot: int = 0
    hero: ResolvedHero | None = None
    team: int | None = None
    assigned_lane: int | None = None
    kills: int | None = None
    deaths: int | None = None
    assists: int | None = None
    net_worth: int | None = None
    last_hits: int | None = None
    denies: int | None = None
    level: int | None = None


class EnrichedMatchContext(BaseModel):
    match_id: int | None = None
    replay_artifact_id: str | None = None
    api_metadata_id: str | None = None
    metadata_summary: MatchMetadataSummary | None = None
    resolved_heroes: dict[int, ResolvedHero] = {}
    resolved_assets: dict[int, ResolvedGameAsset] = {}
    resolved_players: list[ResolvedPlayer] = []
    source_mode: Literal["replay_only", "api_only", "replay_plus_api"] = "replay_only"
    warnings: list[SourceWarning] = []
