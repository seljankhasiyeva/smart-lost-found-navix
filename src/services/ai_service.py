import asyncio
import logging
import time

from src.config import settings
from src.core.exceptions import ProviderError
from src.services.retry import ai_retry, RateLimitError

import ai.vlm as vlm_module
import ai.embedding as embed_module
import ai.similarity as sim_module

logger = logging.getLogger(__name__)

# In-session embedding cache
# Same text → same vector, no repeat API calls
_embed_cache: dict[str, list[float]] = {}

# Semaphore — limits concurrent AI calls
# Prevents provider rate limit errors
_semaphore: asyncio.Semaphore | None = None


def get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(settings.ai_concurrency_limit)
        logger.info("semaphore_init limit=%d", settings.ai_concurrency_limit)
    return _semaphore


@ai_retry
async def describe_item(image_path: str, user_text: str) -> dict:
    """
    Call ai.vlm.describe_item with semaphore + retry + logging.
    Returns a plain dict (stored as JSONB in DB).
    HTTP 429 / rate limit responses are raised as RateLimitError
    so ai_retry can catch and retry them.
    """
    async with get_semaphore():
        logger.info("vlm_start image=%s", image_path)
        t0 = time.monotonic()
        try:
            result = vlm_module.describe_item(image_path, user_text)
        except Exception as e:
            logger.error("vlm_failed image=%s error=%s", image_path, e)
            if "429" in str(e) or "rate limit" in str(e).lower():
                raise RateLimitError(str(e)) from e
            raise ProviderError(str(e)) from e

        elapsed = time.monotonic() - t0
        logger.info("vlm_done elapsed=%.2fs", elapsed)

        # Convert pydantic model to dict if needed
        if not isinstance(result, dict):
            result = result.model_dump()

        # Validate required field
        if "confidence" not in result:
            raise ProviderError("VLM response missing confidence field")

        return result


@ai_retry
async def get_embedding(text: str) -> list[float]:
    """
    Embed text. Returns cached vector if same text was seen before.
    Cache key is the raw text string.
    HTTP 429 / rate limit responses are raised as RateLimitError
    so ai_retry can catch and retry them.
    """
    if text in _embed_cache:
        logger.debug("embed_cache_hit text=%.40s", text)
        return _embed_cache[text]

    async with get_semaphore():
        logger.info("embed_start text=%.40s", text)
        t0 = time.monotonic()
        try:
            vec = embed_module.embed(text)
        except Exception as e:
            logger.error("embed_failed error=%s", e)
            if "429" in str(e) or "rate limit" in str(e).lower():
                raise RateLimitError(str(e)) from e
            raise ProviderError(str(e)) from e

        elapsed = time.monotonic() - t0
        logger.info("embed_done elapsed=%.2fs", elapsed)

        # Convert numpy array to list if needed
        if hasattr(vec, "tolist"):
            vec = vec.tolist()

        _embed_cache[text] = vec
        return vec


def top_matches(
    query_vec: list[float],
    candidates: list[list[float]],
    k: int = 3,
) -> list:
    """Wrapper around ai.similarity.top_k."""
    import numpy as np
    q = np.array(query_vec, dtype=np.float32)
    cands = [np.array(c, dtype=np.float32) for c in candidates]
    return sim_module.top_k(q, cands, k)


def clear_cache() -> None:
    """Clear embedding cache. Used in tests."""
    global _embed_cache
    