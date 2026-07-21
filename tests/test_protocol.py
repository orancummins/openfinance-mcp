"""Protocol-level tests: the MCP server exposes the expected tools and the
in-process tool registry works without hitting the network.
"""
from __future__ import annotations

import pytest

from openfinance_mcp.server import mcp

EXPECTED_TOOLS = {
    "create_access_token",
    "create_testing_customer",
    "list_customers",
    "get_customer",
    "delete_customer",
    "generate_connect_url",
    "get_customer_accounts",
    "get_customer_transactions",
    "generate_payment_success_indicators",
    "subscribe_txpush",
    "generate_voai_report",
}


@pytest.mark.asyncio
async def test_tools_registered():
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    missing = EXPECTED_TOOLS - names
    assert not missing, f"missing tools: {missing}"



