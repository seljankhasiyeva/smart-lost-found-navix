import pytest
import uuid
import os
from unittest.mock import AsyncMock, patch
from src.storage.repository import ItemRepository, save_image
from src.models import ItemCreate
from src.core.exceptions import StorageError, ItemNotFound


@pytest.mark.asyncio
async def test_create_item_happy_path(mock_pool):
    pool, conn = mock_pool
    item_id = uuid.uuid4()
    conn.execute = AsyncMock()
    repo = ItemRepository(pool)
    result = await repo.create(
        item_id,
        ItemCreate(
            status="lost",
            user_text="black wallet",
            image_path="/tmp/x.jpg",
        ),
    )
    assert result == item_id


@pytest.mark.asyncio
async def test_get_by_id_not_found(mock_pool):
    pool, conn = mock_pool
    conn.fetchrow = AsyncMock(return_value=None)
    repo = ItemRepository(pool)
    with pytest.raises(ItemNotFound):
        await repo.get_by_id(uuid.uuid4())


@pytest.mark.asyncio
async def test_get_by_status_returns_list(mock_pool):
    pool, conn = mock_pool
    from datetime import datetime, timezone
    fake_row = {
        "id": uuid.uuid4(),
        "status": "lost",
        "user_text": "wallet",
        "image_path": "/tmp/x.jpg",
        "vlm_description": None,
        "embedding": None,
        "confidence": None,
        "created_at": datetime.now(timezone.utc),
    }
    conn.fetch = AsyncMock(return_value=[fake_row])
    repo = ItemRepository(pool)
    result = await repo.get_by_status("lost")
    assert len(result) == 1
    assert result[0].status == "lost"


@pytest.mark.asyncio
async def test_update_ai_fields(mock_pool):
    pool, conn = mock_pool
    conn.execute = AsyncMock()
    repo = ItemRepository(pool)
    await repo.update_ai_fields(
        uuid.uuid4(),
        {"object_class": "wallet", "confidence": 0.9},
        b"fake_embedding",
        0.9,
    )
    conn.execute.assert_called_once()


def test_save_image_creates_file(tmp_path):
    src = tmp_path / "test.png"
    src.write_bytes(b"fake-image-data")
    item_id = uuid.uuid4()
    with patch("src.storage.repository.settings") as mock_settings:
        mock_settings.image_store_dir = str(tmp_path / "store")
        dest = save_image(str(src), item_id)
    assert os.path.exists(dest)
    assert str(item_id) in dest


def test_save_image_uses_uuid_not_user_filename(tmp_path):
    src = tmp_path / "malicious.png"
    src.write_bytes(b"fake")
    item_id = uuid.uuid4()
    with patch("src.storage.repository.settings") as mock_settings:
        mock_settings.image_store_dir = str(tmp_path / "store")
        dest = save_image(str(src), item_id)
    assert "malicious" not in dest
    assert str(item_id) in dest