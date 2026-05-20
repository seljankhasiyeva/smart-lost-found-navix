import asyncio
import uuid
import pytest
from unittest.mock import AsyncMock, patch
from src.concurrency.pipeline import register_batch, find_matches
from src.models import ItemRecord
from datetime import datetime, timezone


@pytest.mark.asyncio
async def test_register_batch_all_succeed(mock_pool):
    pool, conn = mock_pool

    with patch("src.concurrency.pipeline.describe_item",
               AsyncMock(return_value={"confidence": 0.9, "object_class": "wallet"})), \
         patch("src.concurrency.pipeline.get_embedding",
               AsyncMock(return_value=[0.1] * 8)), \
         patch("src.concurrency.pipeline.save_image",
               return_value="/tmp/x.jpg"):

        from src.storage.repository import ItemRepository
        repo = ItemRepository(pool)
        repo.create = AsyncMock(return_value=uuid.uuid4())
        repo.update_ai_fields = AsyncMock()

        results = await register_batch(repo, [
            ("/tmp/a.jpg", "wallet", "lost"),
            ("/tmp/b.jpg", "backpack", "found"),
        ])
        assert len(results) == 2


@pytest.mark.asyncio
async def test_gather_one_task_raises_propagates():
    call_count = 0

    async def flaky():
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise ConnectionError("provider down")
        return "ok"

    with pytest.raises(ConnectionError):
        await asyncio.gather(flaky(), flaky())


@pytest.mark.asyncio
async def test_find_matches_empty_candidates(mock_pool):
    pool, conn = mock_pool
    from src.storage.repository import ItemRepository

    repo = ItemRepository(pool)
    fake_item = ItemRecord(
        id=uuid.uuid4(),
        status="lost",
        user_text="wallet",
        image_path=None,
        vlm_description=None,
        embedding=None,
        confidence=None,
        created_at=datetime.now(timezone.utc),
    )
    repo.get_by_id = AsyncMock(return_value=fake_item)
    repo.get_by_status = AsyncMock(return_value=[])

    with patch("src.concurrency.pipeline.get_embedding",
               AsyncMock(return_value=[0.1] * 8)):
        matches = await find_matches(repo, fake_item.id, k=3)
        assert matches == []