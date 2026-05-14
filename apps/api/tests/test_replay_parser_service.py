"""Tests for replay parser subprocess wrapper."""

from pathlib import Path

import pytest

from app.core.config import settings
from app.services.replay_parser import (
    ReplayParserExecutionError,
    ReplayParserNotConfiguredError,
    ReplayParserOutputError,
    ReplayParserTimeoutError,
    parse_replay_file,
)

FIXTURES = Path(__file__).parent / "fixtures" / "replay_parser"


@pytest.fixture
async def sample_replay(tmp_path):
    path = tmp_path / "match.dem"
    path.write_bytes(b"demo")
    return path


@pytest.mark.asyncio
async def test_parse_replay_file_success(monkeypatch, sample_replay):
    monkeypatch.setattr(settings, "replay_parser_command", str(FIXTURES / "success_parser.py"))

    result = await parse_replay_file(sample_replay)

    assert result.schema_version == "deadlock-replay-parse-v1"
    assert result.parser["name"] == "fake"
    assert result.warnings == ["test warning"]


@pytest.mark.asyncio
async def test_parse_replay_file_requires_command(monkeypatch, sample_replay):
    monkeypatch.setattr(settings, "replay_parser_command", None)

    with pytest.raises(ReplayParserNotConfiguredError):
        await parse_replay_file(sample_replay)


@pytest.mark.asyncio
async def test_parse_replay_file_nonzero_exit(monkeypatch, sample_replay):
    monkeypatch.setattr(settings, "replay_parser_command", str(FIXTURES / "failing_parser.py"))

    with pytest.raises(ReplayParserExecutionError, match="safe parser failure"):
        await parse_replay_file(sample_replay)


@pytest.mark.asyncio
async def test_parse_replay_file_invalid_json(monkeypatch, sample_replay):
    monkeypatch.setattr(settings, "replay_parser_command", str(FIXTURES / "invalid_json_parser.py"))

    with pytest.raises(ReplayParserOutputError):
        await parse_replay_file(sample_replay)


@pytest.mark.asyncio
async def test_parse_replay_file_timeout(monkeypatch, sample_replay):
    monkeypatch.setattr(settings, "replay_parser_command", str(FIXTURES / "slow_parser.py"))
    monkeypatch.setattr(settings, "replay_parser_timeout_seconds", 0.01)

    with pytest.raises(ReplayParserTimeoutError):
        await parse_replay_file(sample_replay)
