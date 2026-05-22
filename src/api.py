import os
import uuid
import tempfile
import logging
from typing import Optional
from contextlib import asynccontextmanager

import magic
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Request

from src.config import settings
from src.models import ItemRecord, MatchResult
from src.services.retry import setup_logging
from src.core.validation import validate_image, validate_status, validate_item_id
from src.core.exceptions import ImageValidationError, ValidationError, ItemNotFound
from src.storage.repository import create_pool, ItemRepository
from src.concurrency.pipeline import register_item, find_matches

setup_logging(settings.log_level)
logger = logging.getLogger(__name__)

ALLOWED_MIME_TYPES: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage DB connection pool lifecycle."""
    app.state.pool = await create_pool()
    logger.info("Database connection pool created.")
    yield
    await app.state.pool.close()
    logger.info("Database connection pool closed.")


app = FastAPI(
    title="Smart Lost & Found API",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _read_and_detect(image: UploadFile) -> tuple[bytes, str]:
    """
    Read the uploaded file, check size limits, and detect its real MIME type from bytes.
    """
    file_bytes = await image.read()

    # 1. Check max image size limit from settings (Day 4/5 requirement)
    max_bytes = settings.max_image_size_mb * 1024 * 1024
    if len(file_bytes) > max_bytes:
        logger.warning("Rejected upload: file size %d bytes exceeds limit.", len(file_bytes))
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds the maximum allowed limit of {settings.max_image_size_mb}MB.",
        )

    # 2. Detect MIME from actual bytes — never trust filename or Content-Type header.
    mime = magic.from_buffer(file_bytes[:2048], mime=True)
    ext = ALLOWED_MIME_TYPES.get(mime)

    if ext is None:
        logger.warning("Rejected upload with unsupported MIME type: %s", mime)
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{mime}'. Only JPEG and PNG are accepted.",
        )

    return file_bytes, ext


async def _register_item_endpoint(
    request: Request,
    image: UploadFile,
    text: str,
    status: str,
) -> dict:
    """
    Shared logic for /items/lost and /items/found.
    """
    file_bytes, ext = await _read_and_detect(image)

    tmp_path: Optional[str] = None
    try:
        # Secure temporary file creation
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        validate_image(tmp_path)

        repo = ItemRepository(request.app.state.pool)
        item_id = await register_item(repo, tmp_path, text, status)

        logger.info("Registered %s item: %s", status, item_id)
        return {"item_id": str(item_id)}

    except ImageValidationError as e:
        logger.warning("Image validation failed: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error while registering %s item.", status)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Safe cleanup ensures no file leaks
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception as le:
                logger.error("Failed to delete temp file %s: %s", tmp_path, le)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/items/lost", summary="Register a lost item")
async def register_lost(
    request: Request,
    image: UploadFile = File(..., description="JPEG or PNG image of the lost item"),
    text: str = Form(..., description="Short description of the lost item"),
):
    """Register a lost item with an image and a text description."""
    return await _register_item_endpoint(request, image, text, "lost")


@app.post("/items/found", summary="Register a found item")
async def register_found(
    request: Request,
    image: UploadFile = File(..., description="JPEG or PNG image of the found item"),
    text: str = Form(..., description="Short description of the found item"),
):
    """Register a found item with an image and a text description."""
    return await _register_item_endpoint(request, image, text, "found")


@app.get(
    "/items/{item_id}/matches",
    response_model=list[MatchResult],
    summary="Find top-k matches for an item",
)
async def get_matches(request: Request, item_id: str, k: int = 3):
    """
    Return the top-k matches from the opposite pool for the given item ID.
    """
    try:
        validate_item_id(item_id)
        repo = ItemRepository(request.app.state.pool)
        matches = await find_matches(repo, uuid.UUID(item_id), k)
        logger.info("Returned %d matches for item %s", len(matches), item_id)
        return matches
    except (ValidationError, ValueError) as e:
        logger.warning("Validation or value error for item_id %s: %s", item_id, e)
        raise HTTPException(status_code=400, detail=str(e))
    except ItemNotFound as e:
        logger.warning("Item not found: %s", item_id)
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error fetching matches for %s.", item_id)
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/items",
    response_model=list[ItemRecord],
    summary="List all items, optionally filtered by status",
)
async def list_items(request: Request, status: Optional[str] = None):
    """
    Return all registered items. Pass ?status=lost or ?status=found to filter.
    """
    try:
        if status:
            validate_status(status)

        repo = ItemRepository(request.app.state.pool)

        if status:
            items = await repo.get_by_status(status)
        else:
            lost = await repo.get_by_status("lost")
            found = await repo.get_by_status("found")
            items = lost + found

        logger.info("Listed %d items (status=%s).", len(items), status or "all")
        return items
    except ValidationError as e:
        logger.warning("Invalid status filter: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error listing items.")
        raise HTTPException(status_code=500, detail=str(e))