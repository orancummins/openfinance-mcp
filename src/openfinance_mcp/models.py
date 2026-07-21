"""Thin result envelope wrapping Finicity's native JSON payloads.

Tools return Finicity's response body verbatim under ``data`` so no fidelity is
lost, plus a small envelope (``ok``, ``status_code``, ``error``) that MCP
clients can branch on without parsing vendor-specific shapes.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    ok: bool = Field(description="True when the upstream HTTP status was < 400.")
    status_code: int = Field(description="Upstream Finicity HTTP status code.")
    data: Any = Field(default=None, description="Finicity's native response body.")
    error: str | None = Field(default=None, description="Error summary when ok is False.")


def wrap(result: tuple[Any, int]) -> ToolResult:
    """Convert a vendored client ``(body, status_code)`` tuple into a ToolResult."""
    body, status = result
    ok = status < 400
    error = None
    if not ok:
        if isinstance(body, dict):
            error = str(body.get("message") or body.get("error") or body)
        else:
            error = str(body)
    return ToolResult(ok=ok, status_code=status, data=body, error=error)
