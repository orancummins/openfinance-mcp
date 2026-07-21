"""Open Finance MCP Console — a standalone demo UI.

Deploys independently of the MCP server. Its only coupling is the MCP_URL it
connects to (Streamable HTTP). Acts as an MCP client bridge for the browser and
can run the local pytest suites.
"""
from __future__ import annotations

import asyncio
import os
import subprocess  # nosec B404 — used to run the project's own pytest suite
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

MCP_URL = os.getenv("MCP_URL", "http://localhost:9030/mcp")
# Path to the MCP repo so the console can run its tests. Defaults to the parent.
MCP_REPO_PATH = os.getenv("MCP_REPO_PATH", str(Path(__file__).resolve().parents[1]))

ENV_FILE = Path(MCP_REPO_PATH) / ".env"

_CRED_KEYS = [
    "OPEN_FINANCE_PARTNER_ID",
    "OPEN_FINANCE_PARTNER_SECRET",
    "OPEN_FINANCE_APP_KEY",
    "OPEN_FINANCE_API_BASE_URL",
]

app = FastAPI(title="Open Finance MCP Console")


@asynccontextmanager
async def mcp_session():
    async with streamablehttp_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


@app.get("/api/health")
async def health():
    try:
        async with mcp_session() as s:
            await s.list_tools()
        return {"mcp": "up", "url": MCP_URL}
    except Exception as e:  # noqa: BLE001 — surface any connection error to the UI
        return JSONResponse({"mcp": "down", "url": MCP_URL, "error": str(e)}, status_code=502)


@app.get("/api/tools")
async def tools():
    async with mcp_session() as s:
        listed = await s.list_tools()
    return [
        {"name": t.name, "description": t.description, "schema": t.inputSchema}
        for t in listed.tools
    ]


@app.post("/api/call")
async def call(body: dict):
    async with mcp_session() as s:
        result = await s.call_tool(body["name"], body.get("arguments", {}))
    return {
        "isError": result.isError,
        "content": [c.model_dump() for c in result.content],
        "structured": result.structuredContent,
    }


@app.get("/api/finbank-profiles")
async def finbank_profiles():
    """Return the verified FinBank sandbox test profiles."""
    async with mcp_session() as s:
        result = await s.call_tool("list_finbank_profiles", {})
    return result.structuredContent or {}


@app.post("/api/happy-path")
async def happy_path(body: dict):
    """Run the end-to-end sandbox happy path via the run_happy_path MCP tool."""
    profile_key = body.get("profile_key", "finbank_demo")
    async with mcp_session() as s:
        result = await s.call_tool("run_happy_path", {"profile_key": profile_key})
    return {
        "isError": result.isError,
        "structured": result.structuredContent,
    }


@app.get("/api/credentials")
async def get_credentials():
    """Return current .env credential values (local dev tool — values stay on this machine)."""
    from dotenv import dotenv_values  # noqa: PLC0415
    parsed = dotenv_values(ENV_FILE) if ENV_FILE.is_file() else {}
    return {
        "path": str(ENV_FILE),
        "values": {k: parsed.get(k, "") for k in _CRED_KEYS},
    }


@app.post("/api/credentials")
async def save_credentials(body: dict):
    """Write recognised credential keys to the repo-root .env file."""
    try:
        # Restrict writes to known keys only — prevents arbitrary env injection.
        new_vals = {k: str(body.get(k, "")) for k in _CRED_KEYS}

        existing_lines: list[str] = ENV_FILE.read_text().splitlines() if ENV_FILE.is_file() else []

        updated_keys: set[str] = set()
        result_lines: list[str] = []
        for line in existing_lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                result_lines.append(line)
                continue
            if "=" in stripped:
                key = stripped.split("=", 1)[0].strip()
                if key in new_vals:
                    result_lines.append(f"{key}={new_vals[key]}")
                    updated_keys.add(key)
                    continue
            result_lines.append(line)

        for k in _CRED_KEYS:
            if k not in updated_keys:
                result_lines.append(f"{k}={new_vals[k]}")

        ENV_FILE.write_text("\n".join(result_lines) + "\n")
        return {"saved": True, "path": str(ENV_FILE)}
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"saved": False, "error": str(exc)}, status_code=500)


@app.post("/api/tests/run")
async def run_tests(body: dict):
    marker = body.get("marker", "not sandbox")
    proc = await asyncio.create_subprocess_exec(
        "python", "-m", "pytest", "-m", marker, "-q", "--no-header",
        cwd=MCP_REPO_PATH,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    out, _ = await proc.communicate()
    return {"returncode": proc.returncode, "output": out.decode()[-20000:]}


app.mount("/", StaticFiles(directory=str(Path(__file__).parent / "static"), html=True), name="static")
