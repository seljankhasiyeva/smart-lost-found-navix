import asyncio
import logging
import uuid

from src.services.ai_service import describe_item, get_embedding, top_matches
from src.storage.repository import save_image
from src.models import ItemCreate, MatchResult
from src.core.interfaces import ItemRepositoryABC

logger = logging.getLogger(__name__)


async def register_item(
    repo: ItemRepositoryABC,
    image_path: str,
    description: str,
    status: str,
) -> uuid.UUID:
    """
    Register one item.

    Flow:
    1. Generate UUID in Python
    2. Save image to disk with UUID filename (path traversal safe)
    3. Write to DB once — image_path already known
    4. Run VLM + embedding CONCURRENTLY via asyncio.gather
    5. Write AI results to DB
    """
    # 1. UUID generated here — not by the database
    item_id = uuid.uuid4()

    # 2. Save image with UUID filename
    stored_path = save_image(image_path, item_id)
    logger.info("register_item_start id=%s status=%s", item_id, status)

    # 3. Write to DB once
    await repo.create(
        item_id,
        ItemCreate(
            status=status,
            user_text=description,
            image_path=stored_path,
        ),
    )

    # 4. VLM + embedding have no dependency on each other
    #    Run CONCURRENTLY — this is the main speedup
    vlm_desc, embedding = await asyncio.gather(
        describe_item(stored_path, description),
        get_embedding(description),
    )

    # 5. Write AI results to DB
    confidence = float(vlm_desc.get("confidence", 0.0))
    embedding_bytes = str(embedding).encode("utf-8")

    await repo.update_ai_fields(
        item_id,
        vlm_desc,
        embedding_bytes,
        confidence,
    )

    logger.info("register_item_done id=%s confidence=%.2f", item_id, confidence)
    return item_id


async def register_batch(
    repo: ItemRepositoryABC,
    items: list[tuple[str, str, str]],
) -> list[uuid.UUID]:
    """
    Register multiple items in parallel via asyncio.gather.
    items: list of (image_path, description, status)
    Semaphore in ai_service.py bounds actual AI concurrency.
    """
    logger.info("register_batch_start count=%d", len(items))
    tasks = [
        register_item(repo, img, desc, st)
        for img, desc, st in items
    ]
    results = await asyncio.gather(*tasks)
    logger.info("register_batch_done count=%d", len(results))
    return list(results)


async def find_matches(
    repo: ItemRepositoryABC,
    item_id: uuid.UUID,
    k: int = 3,
) -> list[MatchResult]:
    """
    Find top-k matches for an item from the opposite pool.
    lost  → searches in found pool
    found → searches in lost pool
    """
    item = await repo.get_by_id(item_id)

    opposite_status = "found" if item.status == "lost" else "lost"
    candidates = await repo.get_by_status(opposite_status)

    if not candidates:
        logger.info("find_matches_empty id=%s", item_id)
        return []

    query_vec = await get_embedding(item.user_text)

    # Decode stored embeddings
    cand_vecs = []
    valid_candidates = []
    for c in candidates:
        if c.embedding:
            try:
                vec = eval(c.embedding.decode("utf-8"))
                cand_vecs.append(vec)
                valid_candidates.append(c)
            except Exception:
                logger.warning("embedding_decode_failed id=%s", c.id)

    if not cand_vecs:
        return []

    raw_results = top_matches(query_vec, cand_vecs, k)

    return [
        MatchResult(
            item=valid_candidates[r.candidate_id],
            score=float(r.score),
            reason=str(valid_candidates[r.candidate_id].vlm_description),
        )
        for r in raw_results
    ]