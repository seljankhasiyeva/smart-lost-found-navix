from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

from src.config import settings


logger = logging.getLogger(__name__)


def estimate_tokens(text: str) -> int:
    """
    Estimate token count from text.

    This is a lightweight approximation. A common rough estimate is:
    1 token ≈ 4 characters in English-like text.

    Minimum token count is 1.
    """

    if not text:
        return 1

    return max(1, len(text) // 4)


@dataclass
class TokenUsageSnapshot:
    """
    Represents current token usage state.
    """

    used_tokens: int
    limit: int
    remaining_tokens: int
    window_started_at: float


class TokenRateLimiter:
    """
    Token-aware rate limiter.

    Tracks estimated token usage per 60-second window.
    This protects AI provider calls from exceeding token-per-minute limits.
    """

    def __init__(self, token_limit_per_minute: int | None = None) -> None:
        self.token_limit_per_minute = (
            token_limit_per_minute or settings.ai_token_per_minute_limit
        )
        self.window_seconds = 60
        self.window_started_at = time.monotonic()
        self.used_tokens = 0
        self._lock = asyncio.Lock()

    def _reset_window_if_needed(self) -> None:
        now = time.monotonic()

        if now - self.window_started_at >= self.window_seconds:
            logger.info(
                "token_window_reset used_tokens=%s limit=%s",
                self.used_tokens,
                self.token_limit_per_minute,
            )
            self.window_started_at = now
            self.used_tokens = 0

    async def reserve(self, estimated_tokens: int) -> None:
        """
        Reserve tokens before an AI request.

        If the request would exceed the current minute limit, this waits until
        the next token window starts.
        """

        if estimated_tokens <= 0:
            estimated_tokens = 1

        async with self._lock:
            self._reset_window_if_needed()

            if estimated_tokens > self.token_limit_per_minute:
                raise ValueError(
                    "Single request token estimate exceeds per-minute token limit."
                )

            if self.used_tokens + estimated_tokens > self.token_limit_per_minute:
                elapsed = time.monotonic() - self.window_started_at
                wait_seconds = max(0.0, self.window_seconds - elapsed)

                logger.warning(
                    "token_limit_reached used=%s requested=%s limit=%s wait=%.2fs",
                    self.used_tokens,
                    estimated_tokens,
                    self.token_limit_per_minute,
                    wait_seconds,
                )

                await asyncio.sleep(wait_seconds)

                self.window_started_at = time.monotonic()
                self.used_tokens = 0

            self.used_tokens += estimated_tokens

            logger.info(
                "tokens_reserved requested=%s used=%s limit=%s",
                estimated_tokens,
                self.used_tokens,
                self.token_limit_per_minute,
            )

    def snapshot(self) -> TokenUsageSnapshot:
        """
        Return current usage state.
        """

        self._reset_window_if_needed()

        remaining = max(0, self.token_limit_per_minute - self.used_tokens)

        return TokenUsageSnapshot(
            used_tokens=self.used_tokens,
            limit=self.token_limit_per_minute,
            remaining_tokens=remaining,
            window_started_at=self.window_started_at,
        )


global_token_limiter = TokenRateLimiter()