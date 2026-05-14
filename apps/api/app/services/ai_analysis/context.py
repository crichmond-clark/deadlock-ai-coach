"""Build bounded prompt context for structured AI analysis."""

from __future__ import annotations

from typing import Any

from app.db.models import Upload
from app.schemas.ai_analysis import AnalysisInputContext
from app.schemas.enriched_match import EnrichedMatchContext

_MAX_SUMMARY_CHARS = 4000
_MAX_REPLAY_ITEMS = 20


def build_analysis_input_context(
    *,
    upload: Upload,
    replay_parse_summary: dict[str, Any] | None = None,
    enriched_context: EnrichedMatchContext | None = None,
) -> AnalysisInputContext:
    """Create compact model input context from persisted app data."""
    warnings: list[str] = []
    summary_text = upload.summary_text
    if summary_text and len(summary_text) > _MAX_SUMMARY_CHARS:
        summary_text = summary_text[:_MAX_SUMMARY_CHARS]
        warnings.append("match summary text was truncated for AI context")

    compact_replay = _compact_replay_summary(replay_parse_summary)
    if replay_parse_summary and compact_replay != replay_parse_summary:
        warnings.append("replay parse summary was compacted for AI context")

    if enriched_context is not None:
        warnings.extend(warning.message for warning in enriched_context.warnings)

    return AnalysisInputContext(
        upload_kind=str(upload.kind),
        match_summary_text=summary_text,
        replay_parse_summary=compact_replay,
        enriched_context=enriched_context,
        source_warnings=warnings,
    )


def _compact_replay_summary(summary: dict[str, Any] | None) -> dict[str, Any] | None:
    if summary is None:
        return None
    compact: dict[str, Any] = {}
    for key in ("parser", "match", "stats", "warnings"):
        value = summary.get(key)
        if value is not None:
            compact[key] = value
    players = summary.get("players")
    if isinstance(players, list):
        compact["players"] = players[:_MAX_REPLAY_ITEMS]
    timeline = summary.get("timeline")
    if isinstance(timeline, list):
        compact["timeline"] = timeline[:_MAX_REPLAY_ITEMS]
    return compact
