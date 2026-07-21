"""Entry point: ``python -m openfinance_mcp``.

Transports:
  stdio  (default)  — for local MCP clients (Claude Desktop, IDEs).
  http              — Streamable HTTP, for running as a network service.
"""
from __future__ import annotations

import argparse

from .server import mcp


def main() -> None:
    parser = argparse.ArgumentParser(prog="openfinance-mcp")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="MCP transport (default: stdio).",
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host for http transport.")  # nosec B104
    parser.add_argument("--port", type=int, default=9030, help="Port for http transport.")
    args = parser.parse_args()

    if args.transport == "http":
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
