from __future__ import annotations

import inspect
import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Generic, TypeVar

from src.services.retry import RateLimitError


logger = logging.getLogger(__name__)

T = TypeVar("T")


RetryableProviderError = (
    ConnectionError,
    TimeoutError,
    RateLimitError,
)


@dataclass(frozen=True)
class ProviderCall(Generic[T]):
    """
    Represents one provider attempt.

    Example:
        ProviderCall(
            name="anthropic",
            call=lambda: describe_with_anthropic(image_path, user_text)
        )
    """

    name: str
    call: Callable[[], T | Awaitable[T]]


@dataclass(frozen=True)
class FailoverResult(Generic[T]):
    """
    Result returned after successful failover execution.

    Attributes:
        provider: Name of the provider that succeeded.
        value: Actual provider response.
        attempts: Number of providers attempted before success.
    """

    provider: str
    value: T
    attempts: int


class AllProvidersFailedError(RuntimeError):
    """
    Raised when every provider in the failover chain fails.
    """


async def _maybe_await(value: T | Awaitable[T]) -> T:
    """
    Await async results and directly return sync results.

    This lets failover work with both:
    - async provider calls
    - sync provider calls from the provided ai/ package
    """

    if inspect.isawaitable(value):
        return await value

    return value


async def call_with_failover(
    providers: list[ProviderCall[T]],
    operation_name: str,
) -> FailoverResult[T]:
    """
    Try providers in order until one succeeds.

    Only temporary provider failures trigger failover:
    - ConnectionError
    - TimeoutError
    - RateLimitError

    Non-temporary errors are raised immediately because they usually mean
    bad input, invalid schema, or a programming bug.

    Args:
        providers: Ordered list of provider calls.
        operation_name: Human-readable operation name, e.g. "vlm.describe_item".

    Returns:
        FailoverResult containing the successful provider name and result.

    Raises:
        ValueError: If no providers are supplied.
        AllProvidersFailedError: If all providers fail with retryable errors.
        Exception: Immediately raises non-retryable errors.
    """

    if not providers:
        raise ValueError("At least one provider must be supplied for failover.")

    errors: list[str] = []

    for index, provider in enumerate(providers, start=1):
        try:
            logger.info(
                "provider_attempt operation=%s provider=%s attempt=%s/%s",
                operation_name,
                provider.name,
                index,
                len(providers),
            )

            value = await _maybe_await(provider.call())

            logger.info(
                "provider_success operation=%s provider=%s attempts=%s",
                operation_name,
                provider.name,
                index,
            )

            return FailoverResult(
                provider=provider.name,
                value=value,
                attempts=index,
            )

        except RetryableProviderError as error:
            logger.warning(
                "provider_failed_retryable operation=%s provider=%s error=%s",
                operation_name,
                provider.name,
                error,
            )
            errors.append(f"{provider.name}: {error}")
            continue

        except Exception:
            logger.exception(
                "provider_failed_non_retryable operation=%s provider=%s",
                operation_name,
                provider.name,
            )
            raise

    raise AllProvidersFailedError(
        f"All providers failed for operation '{operation_name}'. "
        f"Errors: {' | '.join(errors)}"
    )