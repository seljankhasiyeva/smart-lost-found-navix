# tests/test_retry.py

import logging

import pytest

from src.services.retry import RateLimitError, ai_retry, setup_logging


@pytest.mark.asyncio
async def test_ai_retry_retries_connection_error_then_succeeds():
    """
    ai_retry should retry temporary ConnectionError failures.

    Expected flow:
    1st attempt -> ConnectionError
    2nd attempt -> ConnectionError
    3rd attempt -> success
    """

    call_count = 0

    @ai_retry
    async def flaky_provider_call():
        nonlocal call_count
        call_count += 1

        if call_count < 3:
            raise ConnectionError("temporary provider failure")

        return [0.1] * 1536

    result = await flaky_provider_call()

    assert result == [0.1] * 1536
    assert call_count == 3


@pytest.mark.asyncio
async def test_ai_retry_stops_after_three_attempts():
    """
    ai_retry should stop after 3 failed attempts and re-raise
    the last temporary exception.
    """

    call_count = 0

    @ai_retry
    async def always_fails():
        nonlocal call_count
        call_count += 1
        raise ConnectionError("provider still unavailable")

    with pytest.raises(ConnectionError):
        await always_fails()

    assert call_count == 3


@pytest.mark.asyncio
async def test_ai_retry_retries_timeout_error_then_succeeds():
    """
    TimeoutError is a temporary error and should be retried.
    """

    call_count = 0

    @ai_retry
    async def timeout_then_success():
        nonlocal call_count
        call_count += 1

        if call_count == 1:
            raise TimeoutError("request timed out")

        return {"status": "ok"}

    result = await timeout_then_success()

    assert result == {"status": "ok"}
    assert call_count == 2


@pytest.mark.asyncio
async def test_ai_retry_retries_rate_limit_error_then_succeeds():
    """
    RateLimitError should be retried because it represents HTTP 429
    or similar temporary provider throttling.
    """

    call_count = 0

    @ai_retry
    async def rate_limited_then_success():
        nonlocal call_count
        call_count += 1

        if call_count < 3:
            raise RateLimitError("rate limit exceeded")

        return "success"

    result = await rate_limited_then_success()

    assert result == "success"
    assert call_count == 3


@pytest.mark.asyncio
async def test_ai_retry_does_not_retry_value_error():
    """
    Non-temporary errors such as ValueError should not be retried.
    """

    call_count = 0

    @ai_retry
    async def invalid_request():
        nonlocal call_count
        call_count += 1
        raise ValueError("invalid input")

    with pytest.raises(ValueError):
        await invalid_request()

    assert call_count == 1


def test_rate_limit_error_is_connection_error():
    """
    RateLimitError must inherit from ConnectionError so it can be
    handled as a temporary provider failure.
    """

    error = RateLimitError("too many requests")

    assert isinstance(error, ConnectionError)


def test_setup_logging_sets_log_level():
    """
    setup_logging should configure the root logger with the requested level.
    """

    setup_logging("DEBUG")

    root_logger = logging.getLogger()

    assert root_logger.level == logging.DEBUG