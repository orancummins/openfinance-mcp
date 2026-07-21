"""Live sandbox smoke test — runs only when credentials resolve.

Verifies the vendored client can authenticate against Finicity and that the
end-to-end auth path (partner auth -> App-Token) works with your real creds.
"""
from __future__ import annotations

import pytest

from openfinance_mcp.finicity_client import OpenFinanceClient


@pytest.mark.sandbox
def test_partner_authentication(require_sandbox):
    s = require_sandbox
    client = OpenFinanceClient(s.partner_id, s.partner_secret, s.app_key, base_url=s.api_base_url)
    body, status = client.create_token()
    assert status == 200
    assert "message" in body


@pytest.mark.sandbox
def test_list_institutions(require_sandbox):
    s = require_sandbox
    client = OpenFinanceClient(s.partner_id, s.partner_secret, s.app_key, base_url=s.api_base_url)
    body, status = client.get_institutions(search="FinBank", limit=5)
    assert status == 200
    assert "institutions" in body


@pytest.mark.sandbox
def test_headless_finbank_link(require_sandbox):
    """Full happy path: create testing customer -> headless link -> read accounts."""
    from openfinance_mcp.finbank_profiles import DEFAULT_PROFILE
    from openfinance_mcp.testing_helpers import link_finbank_accounts

    s = require_sandbox
    client = OpenFinanceClient(s.partner_id, s.partner_secret, s.app_key, base_url=s.api_base_url)
    import time

    created, status = client.add_testing_customer(f"pytest_{int(time.time())}")
    assert status in (200, 201), created
    customer_id = str(created["id"])
    try:
        body, link_status = link_finbank_accounts(
            client,
            customer_id,
            DEFAULT_PROFILE.institution_id,
            DEFAULT_PROFILE.username,
            DEFAULT_PROFILE.password,
        )
        assert link_status == 200, body
        assert len(body.get("accounts", [])) >= DEFAULT_PROFILE.expected_min_accounts
    finally:
        client.delete_customer(customer_id)
