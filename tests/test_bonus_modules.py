"""Tests for streaming, cost_telemetry, and cli modules."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from click.testing import CliRunner


# ── Streaming tests ───────────────────────────────────────────────────────────

from src.services.streaming import stream_text_chunks, stream_match_reason


@pytest.mark.asyncio
async def test_stream_text_chunks_basic():
    text = "Hello World This Is A Test"
    chunks = []
    async for chunk in stream_text_chunks(text, chunk_size=5):
        chunks.append(chunk)
    assert "".join(chunks) == text


@pytest.mark.asyncio
async def test_stream_text_chunks_invalid_chunk_size():
    with pytest.raises(ValueError):
        async for _ in stream_text_chunks("hello", chunk_size=0):
            pass


@pytest.mark.asyncio
async def test_stream_text_chunks_empty_string():
    chunks = []
    async for chunk in stream_text_chunks("", chunk_size=5):
        chunks.append(chunk)
    assert chunks == []


@pytest.mark.asyncio
async def test_stream_match_reason():
    reason = "Both items are brown wallets found near a library."
    chunks = []
    async for chunk in stream_match_reason(reason):
        chunks.append(chunk)
    assert "".join(chunks) == reason


# ── Cost telemetry tests ──────────────────────────────────────────────────────

from src.services.cost_telemetry import (
    estimate_tokens,
    estimate_cost,
    CostTelemetry,
    CostEvent,
    MODEL_PRICING_PER_1K_TOKENS,
)


def test_estimate_tokens_basic():
    assert estimate_tokens("hello") == max(1, len("hello") // 4)


def test_estimate_tokens_empty():
    assert estimate_tokens("") == 1


def test_estimate_tokens_long_text():
    text = "a" * 400
    assert estimate_tokens(text) == 100


def test_estimate_cost_known_model():
    cost = estimate_cost("gpt-4o-mini", 1000)
    assert cost == pytest.approx(0.00015)


def test_estimate_cost_unknown_model():
    cost = estimate_cost("unknown-model", 1000)
    assert cost == 0.0


def test_cost_telemetry_record():
    telemetry = CostTelemetry()
    event = telemetry.record("embed", "openai", "text-embedding-3-small", "hello world")
    assert isinstance(event, CostEvent)
    assert event.operation == "embed"
    assert event.provider == "openai"
    assert event.tokens >= 1


def test_cost_telemetry_total_tokens():
    telemetry = CostTelemetry()
    telemetry.record("embed", "openai", "text-embedding-3-small", "hello world")
    telemetry.record("embed", "openai", "text-embedding-3-small", "another text")
    assert telemetry.total_tokens() > 0


def test_cost_telemetry_total_cost():
    telemetry = CostTelemetry()
    telemetry.record("embed", "openai", "gpt-4o-mini", "hello world")
    assert telemetry.total_cost() >= 0.0


def test_cost_telemetry_summary_by_provider():
    telemetry = CostTelemetry()
    telemetry.record("embed", "openai", "gpt-4o-mini", "hello world")
    telemetry.record("vlm", "openai", "gpt-4o-mini", "another text")
    summary = telemetry.summary_by_provider()
    assert "openai" in summary
    assert summary["openai"]["calls"] == 2


def test_cost_telemetry_empty():
    telemetry = CostTelemetry()
    assert telemetry.total_tokens() == 0
    assert telemetry.total_cost() == 0.0
    assert telemetry.summary_by_provider() == {}


def test_model_pricing_has_known_models():
    assert "gpt-4o-mini" in MODEL_PRICING_PER_1K_TOKENS
    assert "text-embedding-3-small" in MODEL_PRICING_PER_1K_TOKENS


# ── CLI tests ─────────────────────────────────────────────────────────────────

from src.cli import cli


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0


def test_cli_register_lost_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["register-lost", "--help"])
    assert result.exit_code == 0


def test_cli_register_found_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["register-found", "--help"])
    assert result.exit_code == 0


def test_cli_list_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["list", "--help"])
    assert result.exit_code == 0


def test_cli_search_matches_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["search-matches", "--help"])
    assert result.exit_code == 0
from src.services.telemetry import setup_tracing

def test_telemetry_setup():
    tracer = setup_tracing()
    assert tracer is not None
