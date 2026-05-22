# tests/test_failover.py

import pytest

from src.services.failover import (
    AllProvidersFailedError,
    ProviderCall,
    call_with_failover,
)
from src.services.retry import RateLimitError


@pytest.mark.asyncio
async def test_failover_uses_second_provider_when_first_fails():
    """
    If the first provider fails with a retryable error,
    failover should call the second provider.
    """

    async def provider_a():
        raise ConnectionError("anthropic unavailable")

    async def provider_b():
        return {"provider": "openai", "result": "success"}

    result = await call_with_failover(
        providers=[
            ProviderCall(name="anthropic", call=provider_a),
            ProviderCall(name="openai", call=provider_b),
        ],
        operation_name="vlm.describe_item",
    )

    assert result.provider == "openai"
    assert result.value == {"provider": "openai", "result": "success"}
    assert result.attempts == 2


@pytest.mark.asyncio
async def test_failover_first_provider_success_no_second_call():
    """
    If the first provider succeeds, the second provider should not be called.
    """

    second_provider_called = False

    async def provider_a():
        return "success from first provider"

    async def provider_b():
        nonlocal second_provider_called
        second_provider_called = True
        return "success from second provider"

    result = await call_with_failover(
        providers=[
            ProviderCall(name="anthropic", call=provider_a),
            ProviderCall(name="openai", call=provider_b),
        ],
        operation_name="embedding.embed",
    )

    assert result.provider == "anthropic"
    assert result.value == "success from first provider"
    assert result.attempts == 1
    assert second_provider_called is False


@pytest.mark.asyncio
async def test_failover_all_providers_fail():
    """
    If all providers fail with retryable errors,
    AllProvidersFailedError should be raised.
    """

    async def provider_a():
        raise ConnectionError("provider A down")

    async def provider_b():
        raise TimeoutError("provider B timeout")

    async def provider_c():
        raise RateLimitError("provider C rate limited")

    with pytest.raises(AllProvidersFailedError):
        await call_with_failover(
            providers=[
                ProviderCall(name="anthropic", call=provider_a),
                ProviderCall(name="openai", call=provider_b),
                ProviderCall(name="offline", call=provider_c),
            ],
            operation_name="vlm.describe_item",
        )


@pytest.mark.asyncio
async def test_failover_non_retryable_error_is_not_hidden():
    """
    Non-retryable errors should not trigger failover.
    They should be raised immediately.
    """

    second_provider_called = False

    async def provider_a():
        raise ValueError("invalid schema")

    async def provider_b():
        nonlocal second_provider_called
        second_provider_called = True
        return "should not run"

    with pytest.raises(ValueError):
        await call_with_failover(
            providers=[
                ProviderCall(name="anthropic", call=provider_a),
                ProviderCall(name="openai", call=provider_b),
            ],
            operation_name="vlm.describe_item",
        )

    assert second_provider_called is False


@pytest.mark.asyncio
async def test_failover_empty_provider_list_rejected():
    """
    Failover requires at least one provider.
    """

    with pytest.raises(ValueError):
        await call_with_failover(
            providers=[],
            operation_name="vlm.describe_item",
        )