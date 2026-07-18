# Haystack Insurance Office

The original insurance-office architecture rebuilt in Python with Haystack while preserving the unchanged React frontend and the MCP service boundaries.

## Architecture

```text
React frontend (:5173)
        |
        v
Haystack API (:5100)
        |
        v
Insurance MCP Proxy (:5275)
        |
        +-- The Lion MCP (:5081)
        +-- The Blue Company MCP (:5082)
        +-- The Three Lines MCP (:5083)
```

Each company is an independent Streamable HTTP MCP server and owns its rates, adjustments, guarantees, exclusions, limits, and deductibles. The proxy exposes namespaced tools such as `thelion_get_quote`. Haystack discovers tools only from the proxy and never imports insurer calculations directly.

## Backend structure

- `backend/config.py` - centralized `.env` loading and typed process settings.
- `backend/app/main.py` - FastAPI assembly only.
- `backend/app/routes/` - chat, insurance, and system endpoints.
- `backend/app/schemas.py` - frontend-facing request models.
- `backend/application/insurance.py` - quote, coverage, and purchase orchestration.
- `backend/agent/` - prompt, Haystack agent, and model/TLS construction.
- `backend/domain/quotes.py` - issued-quote lifecycle and purchase validation.
- `backend/mcp_proxy/` - namespaced discovery, routing, and MCP client code.
- `backend/mcp_servers/company.py` - shared provider calculation and MCP tool factory.
- `backend/mcp_servers/lion.py`, `blue.py`, `three_lines.py` - provider-owned catalogs and pricing.
- `backend/mcp_servers/*_server.py` - independent company process entry points.
- `backend/mcp_audit.py` - correlated JSON audit logging.

Every company server exposes `get_quote`, `check_coverage`, and `purchase_policy`. The proxy exposes all nine company operations with namespaces.

Quotes include `quoteId` and `expiresAt`. A purchase must match an active quote issued by that company, and an issued quote can be purchased only once. `quoteId` is preferred; exact premium matching is supported for the unchanged conversational frontend.

## MCP audit logs

Every company-bound proxy invocation is traced with a generated correlation ID. The proxy and selected company server record the same `request_id`, tool, status, duration, and failures. Logs are rotating JSON Lines files:

- `backend/logs/mcp-proxy.log`
- `backend/logs/mcp-lion.log`
- `backend/logs/mcp-blue.log`
- `backend/logs/mcp-three-lines.log`

Argument names are logged, but customer values, premiums, results, and API keys are not. Configure logging with `MCP_LOG_DIR`, `MCP_LOG_MAX_BYTES`, and `MCP_LOG_BACKUP_COUNT`.

## Run locally

Requires Python 3.10+ and Node.js 20+.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements-dev.txt
Copy-Item backend\.env.example backend\.env
# Edit backend\.env and set OPENAI_API_KEY.
python run_services.py
```

Start the unchanged frontend in a second terminal:

```powershell
cd InsuranceOfficeUI
npm install
npm run dev
```

Open `http://localhost:5173`. The live agent requires `OPENAI_API_KEY`. `DEMO_MODE=true` enables a deliberately limited deterministic fallback.

`OPENAI_MODEL=gpt-4.1-mini` is the compatibility-first default. For a configured GPT-5.6 model used through Haystack's Chat Completions tool path, the model factory automatically supplies `reasoning_effort=none`. `OPENAI_REASONING_EFFORT` can override this explicitly.

## Verify

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

With the services running:

```powershell
.\.venv\Scripts\python.exe -m backend.tests.smoke_mcp
```

All policy data is illustrative and is not financial advice.
