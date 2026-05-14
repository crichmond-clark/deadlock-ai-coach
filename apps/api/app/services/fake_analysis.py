"""Deterministic fake analysis generation for Phase 2."""

from typing import Any

from app.db.models import Upload, UploadKind


def build_fake_analysis_payload(upload: Upload, replay_parse_summary: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a deterministic fake coaching payload from upload metadata."""
    kind_label = upload.kind.value.replace("_", " ")
    filename = upload.filename or "submitted input"

    if upload.kind == UploadKind.MATCH_SUMMARY:
        title = "Match summary analysis ready"
        summary = "Mock coaching summary based on your submitted match summary."
    elif upload.kind == UploadKind.SCREENSHOT:
        title = "Screenshot analysis ready"
        summary = f"Mock coaching summary based on screenshot metadata for {filename}."
    else:
        title = "Replay analysis ready"
        summary = f"Mock coaching summary based on replay metadata for {filename}."

    payload = {
        "title": title,
        "summary": summary,
        "highlights": [
            f"Your {kind_label} request entered the async analysis pipeline.",
            "The worker processed this job without calling external AI services.",
        ],
        "improvement_areas": [
            "Review laning deaths",
            "Track objective timing",
            "Compare item timing against match pressure",
        ],
        "recommended_focus": [
            "Last hitting",
            "Map awareness",
            "Objective setup",
        ],
        "next_steps": [
            "Upload a real replay once parser support lands",
            "Use the completed result page to review future AI-generated coaching",
        ],
        "source": {
            "upload_id": str(upload.id),
            "upload_kind": upload.kind.value,
            "filename": upload.filename,
        },
    }
    if replay_parse_summary is not None:
        payload["replay_parse_summary"] = replay_parse_summary
    return payload
