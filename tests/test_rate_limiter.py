from unittest.mock import AsyncMock, patch

import pytest

from src.services.rate_limiter import TokenRateLimiter, estimate_tokens


def test_estimate_tokens_empty_text():
    assert estimate_tokens("") == 1


def test_estimate_tokens_regular_text():
    text = "black wallet found near the university library"
    assert estimate_tokens(text) >= 1


@pytest.mark.asyncio
async def test_token_limiter_reserves_tokens():
    limiter = TokenRateLimiter(token_limit_per_minute=100)

    await limiter.reserve(20)

    snapshot = limiter.snapshot()

    assert snapshot.used_tokens == 20
    assert snapshot.limit == 100
    assert snapshot.remaining_tokens == 80


@pytest.mark.asyncio
async def test_token_limiter_rejects_single_request_above_limit():
    limiter = TokenRateLimiter(token_limit_per_minute=10)

    with pytest.raises(ValueError):
        await limiter.reserve(11)


@pytest.mark.asyncio
async def test_token_limiter_waits_when_limit_exceeded():
    limiter = TokenRateLimiter(token_limit_per_minute=10)

    await limiter.reserve(8)

    with patch("src.services.rate_limiter.asyncio.sleep", new=AsyncMock()) as mock_sleep:
        await limiter.reserve(5)

    assert mock_sleep.await_count == 1

    snapshot = limiter.snapshot()

    assert snapshot.used_tokens == 5
    assert snapshot.limit == 10
    assert snapshot.remaining_tokens == 5