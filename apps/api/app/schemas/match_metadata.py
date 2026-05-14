"""App-owned schemas for Deadlock API match metadata."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class MatchPlayerSummary(BaseModel):
    account_id: int | None = None
    player_slot: int
    hero_id: int | None = None
    team: int | None = None
    assigned_lane: int | None = None
    kills: int | None = None
    deaths: int | None = None
    assists: int | None = None
    net_worth: int | None = None
    last_hits: int | None = None
    denies: int | None = None
    level: int | None = None


class MatchMetadataSummary(BaseModel):
    match_id: int
    duration_s: int | None = None
    start_time: int | None = None
    game_mode: int | None = None
    winning_team: int | None = None
    average_badge_team0: int | None = None
    average_badge_team1: int | None = None
    players: list[MatchPlayerSummary] = []
    source: Literal["api"] = "api"
