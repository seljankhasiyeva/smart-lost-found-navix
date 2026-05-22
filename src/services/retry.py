# src/services/retry.py
from __future__ import annotations

import asyncio
import functools
import logging
from typing import Any, Callable

from tenacity import (
    retry as tenacity_retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

logger = logging.getLogger(__name__)


class RateLimitError(ConnectionError):
    """
    Raised when an AI provider returns HTTP 429 rate limit response.
    Inherits from ConnectionError so ai_retry can catch and retry it.
    """


def ai_retry(func: Callable) -> Callable:
    """
    Async retry decorator for AI provider calls.
    Retries on: ConnectionError, TimeoutError, RateLimitError
    Attempts: 3 — Wait: 2s -> 4s -> 8s
    """
    @tenacity_retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, RateLimitError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        return await func(*args, **kwargs)
    return wrapper


def setup_logging(level: str = "INFO") -> None:
    """Configure root logger. Called once at startup."""
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        level=getattr(logging, level.upper(), logging.INFO),
        force=True,
    )