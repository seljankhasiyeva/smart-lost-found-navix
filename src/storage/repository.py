import asyncpg
import json
import logging
import os
import shutil
import uuid

from src.config import settings
from src.models import ItemCreate, ItemRecord
from src.core.interfaces import ItemRepositoryABC
from src.core.exceptions import ItemNotFound, StorageError

logger = logging.getLogger(__name__)


def _row_to_record(row) -> ItemRecord:
    d = dict(row)
    if isinstance(d.get("vlm_description"), str):
        try:
            d["vlm_description"] = json.loads(d["vlm_description"])
        except Exception:
            d["vlm_description"] = None
    if isinstance(d.get("embedding"), memoryview):
        d["embedding"] = bytes(d["embedding"])
    return ItemRecord(**d)


class ItemRepository(ItemRepositoryABC):
    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    async def create(self, item_id: uuid.UUID, item: ItemCreate) -> uuid.UUID:
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO items (id, status, user_text, image_path)
                    VALUES ($1, $2, $3, $4)
                    """,
                    item_id, item.status, item.user_text, item.image_path,
                )
                logger.info("item_created id=%s status=%s image=%s", item_id, item.status, item.image_path)
                return item_id
        except asyncpg.PostgresError as e:
            logger.error("db_create_failed error=%s", e)
            raise StorageError(str(e)) from e

    async def update_ai_fields(self, item_id, vlm_desc, embedding, confidence):
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE items
                    SET vlm_description = $1,
                        embedding       = $2,
                        confidence      = $3
                    WHERE id = $4
                    """,
                    json.dumps(vlm_desc), embedding, confidence, item_id,
                )
                logger.info("ai_fields_updated id=%s confidence=%.2f", item_id, confidence)
        except asyncpg.PostgresError as e:
            logger.error("db_update_failed id=%s error=%s", item_id, e)
            raise StorageError(str(e)) from e

    async def get_by_status(self, status: str) -> list[ItemRecord]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM items WHERE status = $1 ORDER BY created_at DESC",
                status,
            )
            return [_row_to_record(r) for r in rows]

    async def get_by_id(self, item_id: uuid.UUID) -> ItemRecord:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM items WHERE id = $1", item_id)
            if row is None:
                raise ItemNotFound(f"Item {item_id} not found")
            return _row_to_record(row)


def save_image(source_path: str, item_id: uuid.UUID) -> str:
    os.makedirs(settings.image_store_dir, exist_ok=True)
    ext = os.path.splitext(source_path)[1].lower()
    if ext not in (".jpg", ".jpeg", ".png"):
        raise ValueError(f"Unsupported image extension: {ext}")
    safe_filename = f"{item_id}{ext}"
    dest_path = os.path.join(settings.image_store_dir, safe_filename)
    shutil.copy2(source_path, dest_path)
    logger.info("image_saved src=%s dest=%s", source_path, dest_path)
    return dest_path


async def create_pool() -> asyncpg.Pool:
    logger.info("db_pool_creating")
    pool = await asyncpg.create_pool(
        settings.database_url, min_size=2, max_size=10, command_timeout=60,
    )
    logger.info("db_pool_ready")
    return pool
