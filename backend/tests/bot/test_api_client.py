"""Tests for bot API client error handling."""
import os
import sys

import pytest
import httpx
import respx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


@respx.mock
@pytest.mark.asyncio
async def test_list_work_orders_success():
    respx.get("http://localhost:8081/api/work-orders").mock(
        return_value=httpx.Response(200, json={"work_orders": [{"id": 1}], "count": 1})
    )
    from bot.api_client import list_work_orders
    result = await list_work_orders()
    assert result == [{"id": 1}]


@respx.mock
@pytest.mark.asyncio
async def test_list_work_orders_api_error():
    respx.get("http://localhost:8081/api/work-orders").mock(
        return_value=httpx.Response(503, text="Service unavailable")
    )
    from bot.api_client import list_work_orders, WACHAPIError
    with pytest.raises(WACHAPIError) as exc:
        await list_work_orders()
    assert exc.value.status_code == 503


@respx.mock
@pytest.mark.asyncio
async def test_approve_work_order():
    respx.post("http://localhost:8081/api/work-orders/5/approve").mock(
        return_value=httpx.Response(200, json={"id": 5, "status": "approved"})
    )
    from bot.api_client import approve_work_order
    result = await approve_work_order(5)
    assert result["status"] == "approved"
