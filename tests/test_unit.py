"""Offline unit tests — no network, no credentials required."""
from __future__ import annotations

from openfinance_mcp.models import ToolResult, wrap
from openfinance_mcp.spec_defaults import DECISIONS, decisions_as_dicts


def test_wrap_success():
    r = wrap(({"customerId": "123"}, 201))
    assert isinstance(r, ToolResult)
    assert r.ok is True
    assert r.status_code == 201
    assert r.data == {"customerId": "123"}
    assert r.error is None


def test_wrap_error_extracts_message():
    r = wrap(({"code": 10000, "message": "bad request"}, 400))
    assert r.ok is False
    assert r.status_code == 400
    assert r.error == "bad request"


def test_wrap_error_plain_text():
    r = wrap(("upstream exploded", 503))
    assert r.ok is False
    assert r.error == "upstream exploded"


def test_all_open_questions_resolved():
    confirmed = {d.id for d in DECISIONS if d.status == "confirmed"}
    assert {"psi_path", "voai_slug", "txpush_body"} <= confirmed


def test_decisions_serialisable():
    payload = decisions_as_dicts()
    assert all("answer" in d and "status" in d for d in payload)
