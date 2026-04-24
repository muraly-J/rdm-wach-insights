"""Tests for bot/ui/pagination.py — paginate() utility."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

import pytest


# ── Basic 25-item scenario ─────────────────────────────────────────────────────

ITEMS_25 = list(range(25))


def test_paginate_page0_has_10_items():
    from bot.ui.pagination import paginate
    page_items, total_pages = paginate(ITEMS_25, page=0, per_page=10)
    assert len(page_items) == 10
    assert page_items == list(range(0, 10))


def test_paginate_page1_has_10_items():
    from bot.ui.pagination import paginate
    page_items, total_pages = paginate(ITEMS_25, page=1, per_page=10)
    assert len(page_items) == 10
    assert page_items == list(range(10, 20))


def test_paginate_page2_has_5_items():
    from bot.ui.pagination import paginate
    page_items, total_pages = paginate(ITEMS_25, page=2, per_page=10)
    assert len(page_items) == 5
    assert page_items == list(range(20, 25))


def test_paginate_25_items_total_pages_is_3():
    from bot.ui.pagination import paginate
    _, total_pages = paginate(ITEMS_25, page=0, per_page=10)
    assert total_pages == 3


# ── Edge cases ─────────────────────────────────────────────────────────────────

def test_paginate_empty_list_returns_empty_and_zero():
    from bot.ui.pagination import paginate
    page_items, total_pages = paginate([], page=0, per_page=10)
    assert page_items == []
    assert total_pages == 0


def test_paginate_single_page_exact_fit():
    from bot.ui.pagination import paginate
    items = list(range(5))
    page_items, total_pages = paginate(items, page=0, per_page=5)
    assert page_items == items
    assert total_pages == 1


def test_paginate_single_page_fewer_than_per_page():
    from bot.ui.pagination import paginate
    items = list(range(3))
    page_items, total_pages = paginate(items, page=0, per_page=10)
    assert page_items == items
    assert total_pages == 1


def test_paginate_out_of_bounds_page_returns_empty():
    from bot.ui.pagination import paginate
    page_items, total_pages = paginate(ITEMS_25, page=99, per_page=10)
    assert page_items == []
    assert total_pages == 3


def test_paginate_default_per_page_is_10():
    from bot.ui.pagination import paginate
    items = list(range(15))
    page_items, total_pages = paginate(items, page=0)
    assert len(page_items) == 10
    assert total_pages == 2


def test_paginate_single_item():
    from bot.ui.pagination import paginate
    page_items, total_pages = paginate(["only"], page=0, per_page=10)
    assert page_items == ["only"]
    assert total_pages == 1


def test_paginate_exactly_per_page_items():
    from bot.ui.pagination import paginate
    items = list(range(10))
    page_items, total_pages = paginate(items, page=0, per_page=10)
    assert page_items == items
    assert total_pages == 1


def test_paginate_preserves_item_types():
    from bot.ui.pagination import paginate
    items = [{"id": i} for i in range(12)]
    page_items, total_pages = paginate(items, page=1, per_page=10)
    assert len(page_items) == 2
    assert page_items[0] == {"id": 10}
    assert page_items[1] == {"id": 11}


# ── Return type checks ─────────────────────────────────────────────────────────

def test_paginate_returns_tuple():
    from bot.ui.pagination import paginate
    result = paginate(ITEMS_25, page=0, per_page=10)
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_paginate_first_element_is_list():
    from bot.ui.pagination import paginate
    page_items, _ = paginate(ITEMS_25, page=0, per_page=10)
    assert isinstance(page_items, list)


def test_paginate_second_element_is_int():
    from bot.ui.pagination import paginate
    _, total_pages = paginate(ITEMS_25, page=0, per_page=10)
    assert isinstance(total_pages, int)
