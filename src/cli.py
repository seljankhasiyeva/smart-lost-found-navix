# src/cli.py
import click
import logging

from src.config import settings
from src.services.retry import setup_logging
setup_logging(settings.log_level)
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Smart Lost & Found — Command Line Interface."""
    pass


@cli.command()
@click.argument("image_path")
@click.option("--text", required=True, help="Item description")
def register_lost(image_path, text):
    """Register a lost item."""
    pass  # Day 5-də implement ediləcək


@cli.command()
@click.argument("image_path")
@click.option("--text", required=True, help="Item description")
def register_found(image_path, text):
    """Register a found item."""
    pass


@cli.command()
@click.argument("item_id")
@click.option("--k", default=3, help="Number of matches to return")
def search_matches(item_id, k):
    """Find top-k matches for an item."""
    pass


@cli.command()
@click.option("--status", default=None, help="Filter by status: lost or found")
def list_items(status):
    """List all items."""
    pass


if __name__ == "__main__":
    cli()