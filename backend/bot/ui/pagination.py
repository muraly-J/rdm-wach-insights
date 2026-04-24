from __future__ import annotations

"""
bot/ui/pagination.py
─────────────────────
Generic pagination utility for list-based bot responses.
"""

import math
from typing import TypeVar

T = TypeVar("T")


def paginate(items: list[T], page: int, per_page: int = 10) -> tuple[list[T], int]:
    """Return (page_items, total_pages). page is 0-indexed.

    Args:
        items: The full list of items to paginate.
        page: Zero-based page index.
        per_page: Maximum number of items per page (default: 10).

    Returns:
        A tuple of (items on the requested page, total number of pages).
        If items is empty, returns ([], 0).
    """
    if not items:
        return [], 0

    total_pages = math.ceil(len(items) / per_page)
    start = page * per_page
    end = start + per_page
    return items[start:end], total_pages
