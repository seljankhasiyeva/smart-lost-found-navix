import asyncio
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import AsyncMock, MagicMock, patch

ITEMS = [
    ("data/lost/umbrella_black.png",    "black umbrella",  "lost"),
    ("data/lost/backpack_navy.png",     "navy backpack",   "lost"),
    ("data/lost/phone_apple_black.png", "black iphone",    "lost"),
    ("data/found/umbrella_black_2.png", "umbrella",        "found"),
    ("data/found/backpack_navy_2.png",  "backpack",        "found"),
]


async def run_sequential(repo):
    from src.concurrency.pipeline import register_item
    t0 = time.monotonic()
    for img, desc, st in ITEMS:
        await register_item(repo, img, desc, st)
    return time.monotonic() - t0


async def run_concurrent(repo):
    from src.concurrency.pipeline import register_batch
    t0 = time.monotonic()
    await register_batch(repo, ITEMS)
    return time.monotonic() - t0


async def main():
    mock_repo = MagicMock()
    mock_repo.create = AsyncMock(return_value=None)
    mock_repo.update_ai_fields = AsyncMock()

    with patch(
        "src.services.ai_service.vlm_module.describe_item",
        return_value={"confidence": 0.9, "object_class": "item"},
    ), patch(
        "src.services.ai_service.embed_module.embed",
        return_value=[0.1] * 1536,
    ), patch(
        "src.storage.repository.save_image",
        return_value="/tmp/x.jpg",
    ):
        print(f"Benchmark: {len(ITEMS)} items")
        print("-" * 40)

        t_seq = await run_sequential(mock_repo)
        print(f"Sequential:  {t_seq:.2f}s")

        from src.services.ai_service import clear_cache
        clear_cache()

        t_con = await run_concurrent(mock_repo)
        print(f"Concurrent:  {t_con:.2f}s")
        print(f"Speedup:     {t_seq / t_con:.1f}x")
        print("-" * 40)
        print("Paste these numbers into README.md")


if __name__ == "__main__":
    asyncio.run(main())