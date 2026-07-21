# Open Finance US MCP

A standalone [Model Context Protocol](https://modelcontextprotocol.io) server
that wraps the **Mastercard Open Finance US (Finicity)** hosted APIs
(`https://api.finicity.com`). It is a separate codebase from Vima and vendors
its own Finicity client — no dependency on Vima's `apis/`, `execute()` wrapper,
or simulator.

## Layout

```
openfinance-mcp/
  src/openfinance_mcp/
    finicity_client.py   # vendored Finicity client (only depends on requests)
    server.py            # FastMCP server + tools
    models.py            # ToolResult envelope
    spec_defaults.py     # resolved spec decisions + open questions
    config/settings.py   # credential loader (env / dotenv / sibling vima config/.env)
    __main__.py          # stdio + streamable-http entry point
  tests/                 # unit, protocol (offline) + sandbox (live) suites
  console/               # separate, independently deployable demo UI
```

## Credentials

The server reads `OPEN_FINANCE_PARTNER_ID`, `OPEN_FINANCE_PARTNER_SECRET`,
`OPEN_FINANCE_APP_KEY`, `OPEN_FINANCE_API_BASE_URL`. Resolution order:

1. Process environment.
2. `OPENFINANCE_MCP_ENV_FILE` (a dotenv path).
3. A local `.env` in this repo.
4. **The sibling `../vima/config/.env`** — so it runs "for real" against the
   valid sandbox credentials you already have provisioned, with no copying.

## Run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[test,console]"

# local (stdio) MCP
python -m openfinance_mcp

# as a service (Streamable HTTP)
python -m openfinance_mcp --transport http --port 9030

# tests
pytest -m "not sandbox"   # offline
pytest -m sandbox         # live Finicity (needs creds)
```

## Demo console (separate deploy)

```bash
cd console
pip install -r requirements.txt
MCP_URL=http://localhost:9030/mcp uvicorn app:app --port 8080
# open http://localhost:8080
```

Or both together: `docker compose up --build`.

## Resolved spec decisions

| Question | Answer | Status |
|---|---|---|
| PSI path/body | `POST /payments/customers/{id}/accounts/{aid}/payment-success-indicators`, `{"transaction":{"settleByDate","amount"}}` | confirmed |
| VOAI slug | `voaHistory` | confirmed |
| TxPUSH body | `{"callbackUrl": <url>}` | confirmed |

The console's **Spec Decisions** tab renders these live from the running server.
