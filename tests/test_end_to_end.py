# tests/test_end_to_end.py
import pytest
import uuid
from unittest.mock import AsyncMock, patch
from src.concurrency.pipeline import register_item
from src.core.exceptions import ProviderError


@pytest.mark.asyncio
async def test_register_item_happy_path(mock_pool):
    """Full happy-path: register one lost item end-to-end."""
    pool, conn = mock_pool
    item_id = uuid.uuid4()

    with patch("src.concurrency.pipeline.describe_item",
               AsyncMock(return_value={"confidence": 0.85, "object_class": "wallet"})), \
         patch("src.concurrency.pipeline.get_embedding",
               AsyncMock(return_value=[0.1] * 8)), \
         patch("src.concurrency.pipeline.save_image",
               return_value="/tmp/x.jpg"):

        from src.storage.repository import ItemRepository
        repo = ItemRepository(pool)
        repo.create = AsyncMock(return_value=item_id)
        repo.update_ai_fields = AsyncMock()

        result = await register_item(repo, "/tmp/wallet.jpg", "black wallet", "lost")
        assert result is not None
        repo.create.assert_called_once()
        repo.update_ai_fields.assert_called_once()


@pytest.mark.asyncio
async def test_register_item_vlm_fails(mock_pool):
    """If VLM fails, ProviderError propagates."""
    pool, conn = mock_pool

    with patch("src.concurrency.pipeline.describe_item",
               AsyncMock(side_effect=ProviderError("VLM down"))), \
         patch("src.concurrency.pipeline.get_embedding",
               AsyncMock(return_value=[0.1] * 8)), \
         patch("src.concurrency.pipeline.save_image",
               return_value="/tmp/x.jpg"):

        from src.storage.repository import ItemRepository
        repo = ItemRepository(pool)
        repo.create = AsyncMock(return_value=uuid.uuid4())
        repo.update_ai_fields = AsyncMock()

        with pytest.raises(ProviderError):
            await register_item(repo, "/tmp/wallet.jpg", "wallet", "lost")