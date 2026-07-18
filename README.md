# Insurance Office — Haystack + MCP

Insurance Office is a conversational insurance demo built with Python, Haystack, FastAPI, and the Model Context Protocol (MCP). It compares illustrative auto, home, and life policies from three independent insurance providers while preserving the original React frontend.

The assistant can:

- Answer general insurance questions conversationally.
- Explain guarantees, exclusions, limits, and deductibles.
- Request missing information before preparing a quote.
- Compare quotes from all three providers.
- Query one provider when a question is company-specific.
- Purchase a previously issued illustrative quote.

All prices and policy data are fictional and intended for demonstration only.

## Architecture

```text
React frontend :5173
        |
        | HTTP /api/chat, /api/quotes, /api/coverage, /api/purchase
        v
FastAPI + Haystack agent :5100
        |
        | MCP only
        v
Insurance MCP proxy :5275
        |
        +-- The Lion MCP :5081
        +-- The Blue Company MCP :5082
        +-- The Three Lines MCP :5083
```

The Haystack agent connects only to the MCP proxy. It does not import provider pricing functions or policy catalogs. The proxy exposes namespaced tools and forwards each invocation to the appropriate independent provider server.

### Request flow

1. The React frontend sends the user message and visible conversation history to `POST /api/chat`.
2. The Haystack agent decides whether the question requires a tool.
3. General questions are answered directly without MCP traffic.
4. Provider-specific facts and actions go through the MCP proxy.
5. The proxy creates a correlation ID and forwards the request to one provider server.
6. The provider returns structured data.
7. The agent interprets the tool result and writes a coherent response instead of displaying raw JSON.

### MCP tools

Each provider implements the same three operations:

| Operation | Purpose |
| --- | --- |
| `get_quote` | Issue an illustrative auto, home, or life quote. |
| `check_coverage` | Return structured guarantees, exclusions, limits, terms, and deductibles. |
| `purchase_policy` | Purchase an active quote previously issued by that provider. |

The proxy exposes nine namespaced tools, for example:

- `thelion_get_quote`
- `thebluecompany_check_coverage`
- `thethreelines_purchase_policy`

## Technology

- Python 3.10+
- Haystack 2.31
- FastAPI
- MCP Python SDK
- Haystack MCP integration
- OpenAI chat models
- React 19, TypeScript, and Vite
- Pytest

## Repository structure

```text
insurance-office-haystack/
├── backend/
│   ├── agent/
│   │   ├── model_factory.py     # OpenAI generator and Windows TLS setup
│   │   ├── prompt.py            # Conversation and tool-use policy
│   │   └── service.py           # Haystack agent and message history
│   ├── app/
│   │   ├── routes/              # Chat, insurance, and health endpoints
│   │   ├── errors.py            # API exception mapping and diagnostics
│   │   ├── main.py              # FastAPI application assembly
│   │   └── schemas.py           # HTTP request models
│   ├── application/
│   │   └── insurance.py         # Quote, coverage, and purchase orchestration
│   ├── domain/
│   │   └── quotes.py            # Issued-quote lifecycle and validation
│   ├── mcp_proxy/
│   │   ├── client.py            # Shared MCP client
│   │   └── server.py            # Namespaced proxy tools and routing
│   ├── mcp_servers/
│   │   ├── company.py           # Shared provider behavior and MCP factory
│   │   ├── coverage.py          # Structured coverage domain objects
│   │   ├── lion.py              # Lion pricing and policy catalog
│   │   ├── blue.py              # Blue pricing and policy catalog
│   │   ├── three_lines.py       # Three Lines pricing and policy catalog
│   │   └── *_server.py          # Independent MCP process entry points
│   ├── tests/                   # Unit, HTTP integration, and smoke tests
│   ├── config.py                # Centralized environment configuration
│   └── mcp_audit.py             # Correlated rotating JSON logs
├── InsuranceOfficeUI/           # Original React frontend
├── pyproject.toml                # Test and lint configuration
└── run_services.py               # Starts all five backend processes
```

## Prerequisites

Install:

- Python 3.10 or newer.
- Node.js 20 or newer.
- An OpenAI API key for conversational mode.

## Quick start on Windows

Run the following commands from the repository root:

```powershell
cd C:\Users\giuli\Desktop\Portfolio\insurance-office-haystack

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r backend\requirements-dev.txt

Copy-Item backend\.env.example backend\.env
notepad backend\.env
```

Set your API key in `backend/.env`:

```env
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4.1-mini
DEMO_MODE=false
```

Never commit `backend/.env` or paste the key into logs, issues, or chat messages.

### Start the backend

```powershell
python run_services.py
```

The launcher starts the services in dependency order:

| Service | Address |
| --- | --- |
| The Lion MCP | `http://127.0.0.1:5081/mcp` |
| The Blue Company MCP | `http://127.0.0.1:5082/mcp` |
| The Three Lines MCP | `http://127.0.0.1:5083/mcp` |
| Insurance MCP proxy | `http://127.0.0.1:5275/mcp` |
| FastAPI/Haystack API | `http://127.0.0.1:5100` |

Keep the terminal open. Press `Ctrl+C` to stop all five backend processes.

### Start the frontend

Open a second terminal:

```powershell
cd C:\Users\giuli\Desktop\Portfolio\insurance-office-haystack\InsuranceOfficeUI
npm install
npm run dev
```

Open `http://localhost:5173`.

The other `start:*` scripts currently present in the frontend `package.json` belong to the original .NET solution. They are not used by this Haystack backend. Use `npm run dev` for the frontend and `python run_services.py` for the backend.

## Configuration

Configuration is read from `backend/.env` by every backend process.

| Variable | Default | Description |
| --- | --- | --- |
| `OPENAI_API_KEY` | empty | Enables live conversational mode. |
| `OPENAI_MODEL` | `gpt-4.1-mini` | Model used by the Haystack agent. |
| `OPENAI_REASONING_EFFORT` | empty | Optional model-specific override. |
| `DEMO_MODE` | `false` | Enables the limited deterministic chat fallback when no API key exists. |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated allowed frontend origins. |
| `MCP_PROXY_URL` | `http://127.0.0.1:5275/mcp` | MCP proxy URL used by the API and agent. |
| `LION_MCP_URL` | `http://127.0.0.1:5081/mcp` | Lion server URL used by the proxy. |
| `BLUE_MCP_URL` | `http://127.0.0.1:5082/mcp` | Blue server URL used by the proxy. |
| `THREE_LINES_MCP_URL` | `http://127.0.0.1:5083/mcp` | Three Lines server URL used by the proxy. |
| `MCP_LOG_DIR` | `backend/logs` | Directory for MCP audit logs. |
| `MCP_LOG_MAX_BYTES` | `5000000` | Maximum size of one log file before rotation. |
| `MCP_LOG_BACKUP_COUNT` | `5` | Number of rotated files retained. |
| `QUOTE_TTL_SECONDS` | `1800` | Lifetime of an issued quote in seconds. |

### Model compatibility

`gpt-4.1-mini` is the compatibility-first default for Haystack's current Chat Completions tool integration.

When `OPENAI_MODEL` starts with `gpt-5.6`, the model factory automatically uses `reasoning_effort=none`. OpenAI currently rejects GPT-5.6 function tools through `/v1/chat/completions` when extended reasoning is enabled. Using higher reasoning effort with tools requires migrating the model integration to the Responses API.

## Chat behavior

The system prompt separates conversation from provider operations:

- General educational questions do not call MCP tools.
- A quote comparison calls all three `get_quote` tools.
- A question about one named provider calls only that provider's coverage tool.
- A purchase tool is called only after the user explicitly selects and confirms a quote.
- Tool responses are summarized into natural language.
- Prices and provider-specific facts are never invented.

The frontend sends the last visible user and assistant messages with every request. It does not currently persist conversations in a database.

## Quotes and purchases

Every company quote includes:

- `quoteId`
- `expiresAt`
- Annual and monthly premium
- Provider identity
- Coverage type
- Structured included guarantees

Each company maintains its own process-local issued-quote ledger. A purchase succeeds only when:

- The company previously issued a matching quote.
- The quote has not expired.
- The annual premium has not been changed.
- The quote has not already been purchased.

The ledger is intentionally in memory for this demo. Restarting a company server clears its issued quotes. A production implementation should store quotes and purchases in a persistent database and associate them with an authenticated customer.

## HTTP API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Check API, proxy, tool count, and chat mode. |
| `GET` | `/api/providers` | List configured providers. |
| `POST` | `/api/chat` | Send a conversational message and history. |
| `POST` | `/api/quotes` | Compare all provider quotes. |
| `GET` | `/api/coverage/{type}` | Inspect auto, home, or life coverage. |
| `POST` | `/api/purchase` | Purchase an active issued quote. |

### Health check

```powershell
Invoke-RestMethod http://127.0.0.1:5100/api/health
```

A correctly configured result reports:

```json
{
  "status": "ok",
  "engine": "Haystack",
  "proxy": "connected",
  "toolCount": 9,
  "mode": "live"
}
```

### Quote comparison

```powershell
$body = @{
  age = 35
  coverageType = "auto"
  assetValue = 25000
} | ConvertTo-Json

$quotes = Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:5100/api/quotes `
  -ContentType "application/json" `
  -Body $body

$quotes.quotes
```

### Coverage details

```powershell
Invoke-RestMethod "http://127.0.0.1:5100/api/coverage/auto?provider_id=blue"
```

### Purchase an issued quote

```powershell
$selected = $quotes.quotes | Where-Object providerId -eq "blue"

$body = @{
  providerId = $selected.providerId
  annualPremium = $selected.annualPremium
  quoteId = $selected.quoteId
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:5100/api/purchase `
  -ContentType "application/json" `
  -Body $body
```

## MCP audit logs

Every company-bound request produces correlated JSON Lines entries in:

- `backend/logs/mcp-proxy.log`
- `backend/logs/mcp-lion.log`
- `backend/logs/mcp-blue.log`
- `backend/logs/mcp-three-lines.log`

The proxy and company entries share the same `request_id`. Records include the service, event, company, tool, status, and duration. Customer ages, insured values, premiums, results, and API keys are deliberately omitted.

Example:

```json
{"service":"proxy","event":"route.completed","request_id":"...","company":"thebluecompany","tool":"thebluecompany_check_coverage","status":"success","duration_ms":396.55}
{"service":"blue","event":"tool.completed","request_id":"...","company":"blue","tool":"check_coverage","status":"success","duration_ms":1.97}
```

## Testing

Run the complete automated suite from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The suite covers:

- Provider pricing and age adjustments.
- Structured coverage catalogs.
- Quote and purchase validation.
- Conversation history construction.
- Model compatibility settings.
- API request contracts.
- MCP audit formatting.

With the backend services running, execute the live smoke test:

```powershell
.\.venv\Scripts\python.exe -m backend.tests.smoke_mcp
```

This verifies MCP discovery, proxy routing, quote issuance, verified purchase, and a live conversational API response.

## Troubleshooting

### Chat says it is not configured

Confirm that `backend/.env` contains a non-empty `OPENAI_API_KEY`, save the file, and restart `python run_services.py`. Check the mode with:

```powershell
(Invoke-RestMethod http://127.0.0.1:5100/api/health).mode
```

It should return `live`.

### `/api/chat` returns 502

Look at the backend terminal for the underlying model or MCP error. If using GPT-5.6 through the current Chat Completions integration, leave `OPENAI_REASONING_EFFORT` empty so the compatibility rule can select `none`.

### A service cannot bind to its port

Another backend instance is probably running. Find listeners with:

```powershell
Get-NetTCPConnection -State Listen |
  Where-Object LocalPort -in 5081,5082,5083,5100,5275 |
  Select-Object LocalPort,OwningProcess
```

Stop only the listed stale backend process IDs, then run `python run_services.py` again.

### Creating the virtual environment appears frozen

The first `python -m venv .venv` may spend time installing pip. Let it finish. If `.venv` already exists and works, activate it instead of recreating it.

### Backend startup takes time

Haystack imports can be slow on the first run. The launcher allows up to 90 seconds for each service and reports when all services are ready.

## Current limitations

- Provider data and purchases are illustrative.
- Quotes and purchases are stored only in memory.
- There is no authentication or customer database.
- Chat history is supplied by the frontend rather than persisted by the backend.
- The OpenAI integration currently uses Chat Completions rather than the Responses API.
- The original frontend is intentionally unchanged and still contains unused legacy `.NET` start scripts.

## Security notes

- Keep `backend/.env` out of version control.
- Never log or return the OpenAI API key.
- MCP audit records intentionally exclude business payload values.
- Add authentication, authorization, persistent storage, and durable audit retention before treating this architecture as production-ready.

## License

No license has been added yet. Add one before distributing or accepting external contributions.
