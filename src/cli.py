import asyncio
import uuid
import logging

import click

from src.config import settings
from src.services.retry import setup_logging
from src.storage.repository import create_pool, ItemRepository
from src.concurrency.pipeline import register_item, find_matches
from src.core.validation import validate_image, validate_status, validate_item_id
from src.core.exceptions import ImageValidationError, ValidationError, ItemNotFound

setup_logging(settings.log_level)
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Smart Lost & Found — Command Line Interface."""
    pass


# ---------------------------------------------------------------------------
# Internal helper — avoids duplicating pool open/close in every command
# ---------------------------------------------------------------------------

async def _with_pool(coro_fn):
    """Open a DB pool, run coro_fn(pool), close the pool."""
    pool = await create_pool()
    try:
        return await coro_fn(pool)
    finally:
        await pool.close()


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("image_path")
@click.option("--text", required=True, help="Short description of the lost item.")
def register_lost(image_path: str, text: str):
    """Register a lost item with IMAGE_PATH and a text description."""

    async def _run(pool):
        repo = ItemRepository(pool)
        item_id = await register_item(repo, image_path, text, "lost")
        click.echo(f"Registered lost item: {item_id}")

    try:
        validate_image(image_path)
        asyncio.run(_with_pool(_run))
    except ImageValidationError as e:
        click.echo(f"Validation error: {e}", err=True)
    except Exception as e:
        logger.exception("Unexpected error registering lost item.")
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.argument("image_path")
@click.option("--text", required=True, help="Short description of the found item.")
def register_found(image_path: str, text: str):
    """Register a found item."""

    async def _run(pool):
        repo = ItemRepository(pool)
        item_id = await register_item(repo, image_path, text, "found")
        click.echo(f"Registered found item: {item_id}")

    try:
        validate_image(image_path) 
        asyncio.run(_with_pool(_run))
    except ImageValidationError as e:
        click.echo(f"Validation error: {e}", err=True)
    except Exception as e:
        logger.exception("Unexpected error registering found item.")
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.argument("item_id")
@click.option("--k", default=3, show_default=True, help="Number of top matches to return.")
def search_matches(item_id: str, k: int):
    """Find top-k matches for the item with ITEM_ID."""

    async def _run(pool):
        repo = ItemRepository(pool)
        matches = await find_matches(repo, uuid.UUID(item_id), k)
        if not matches:
            click.echo("No matches found.")
            return
        for i, match in enumerate(matches, 1):
            click.echo(
                f"{i}. score={match.score:.4f}  id={match.item.id}  reason={match.reason}"
            )

    try:
        validate_item_id(item_id)
        asyncio.run(_with_pool(_run))
    except (ValidationError, ValueError) as e:
        click.echo(f"Validation error: {e}", err=True)
    except ItemNotFound as e:
        click.echo(f"Not found: {e}", err=True)
    except Exception as e:
        logger.exception("Unexpected error searching matches.")
        click.echo(f"Error: {e}", err=True)


@cli.command("list")
@click.option(
    "--status",
    default=None,
    help="Filter by status: lost or found. Omit to list all.",
)
def list_items(status: str):
    """List all registered items, optionally filtered by --status."""

    async def _run(pool):
        repo = ItemRepository(pool)
        if status:
            items = await repo.get_by_status(status)
        else:
            lost = await repo.get_by_status("lost")
            found = await repo.get_by_status("found")
            items = lost + found

        if not items:
            click.echo("No items found.")
            return

        for item in items:
            click.echo(
                f"id={item.id}  status={item.status}  text={item.user_text}"
            )

    try:
        if status:
            validate_status(status) 
        asyncio.run(_with_pool(_run))
    except ValidationError as e:
        click.echo(f"Validation error: {e}", err=True)
    except Exception as e:
        logger.exception("Unexpected error listing items.")
        click.echo(f"Error: {e}", err=True)


if __name__ == "__main__":
    cli()