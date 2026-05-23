from __future__ import annotations

import asyncio
from typing import AsyncIterator


async def stream_text_chunks(text: str, chunk_size: int = 20) -> AsyncIterator[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")
    for start in range(0, len(text), chunk_size):
        await asyncio.sleep(0)
        yield text[start : start + chunk_size]


async def stream_match_reason(reason: str) -> AsyncIterator[str]:
    async for chunk in stream_text_chunks(reason, chunk_size=30):
        yield chunk
