"""Subprocess wrapper for the Phase 2.5 replay parser CLI."""

import asyncio
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ValidationError

from app.core.config import settings

SCHEMA_VERSION = "deadlock-replay-parse-v1"
MAX_ERROR_LENGTH = 500


class ReplayParseResult(BaseModel):
    schema_version: Literal["deadlock-replay-parse-v1"]
    parser: dict[str, Any]
    source: dict[str, Any]
    match: dict[str, Any]
    players: list[dict[str, Any]]
    timeline: list[dict[str, Any]]
    capabilities: dict[str, Any]
    warnings: list[str]
    stats: dict[str, Any]


class ReplayParserError(Exception):
    """Base safe parser error."""


class ReplayParserNotConfiguredError(ReplayParserError):
    """Parser command is not configured."""


class ReplayParserInputError(ReplayParserError):
    """Replay input path is missing or unreadable."""


class ReplayParserTimeoutError(ReplayParserError):
    """Parser exceeded its timeout."""


class ReplayParserExecutionError(ReplayParserError):
    """Parser exited unsuccessfully."""


class ReplayParserOutputError(ReplayParserError):
    """Parser output was invalid."""


def safe_error(message: str) -> str:
    return " ".join(message.split())[:MAX_ERROR_LENGTH]


async def parse_replay_file(path: Path, *, max_events: int = 500) -> ReplayParseResult:
    """Run the configured replay parser and validate normalized JSON output."""
    command = settings.replay_parser_command
    if not command:
        raise ReplayParserNotConfiguredError("replay parser command is not configured")
    if not path.is_file():
        raise ReplayParserInputError("replay input file does not exist")

    argv = [command, "--input", str(path), "--max-events", str(max_events)]
    try:
        process = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except OSError as exc:
        raise ReplayParserNotConfiguredError(safe_error(str(exc))) from exc

    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=settings.replay_parser_timeout_seconds,
        )
    except TimeoutError as exc:
        process.kill()
        await process.communicate()
        raise ReplayParserTimeoutError("replay parser timed out") from exc

    if process.returncode != 0:
        message = stderr.decode(errors="replace") or f"parser exited with code {process.returncode}"
        raise ReplayParserExecutionError(safe_error(message))

    try:
        parsed = json.loads(stdout.decode())
        return ReplayParseResult.model_validate(parsed)
    except (UnicodeDecodeError, json.JSONDecodeError, ValidationError) as exc:
        raise ReplayParserOutputError("replay parser returned invalid normalized JSON") from exc


def resolve_local_replay_path(storage_key: str | None = None) -> Path | None:
    """Resolve local-dev replay path without accepting arbitrary user paths."""
    if not settings.allow_local_replay_paths:
        return None
    if settings.local_replay_sample_path:
        return Path(settings.local_replay_sample_path)
    if storage_key and storage_key.startswith("local://"):
        return Path(storage_key.removeprefix("local://"))
    return None
