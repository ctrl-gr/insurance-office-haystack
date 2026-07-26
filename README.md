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
        +-- Insurance Conditions RAG MCP :5084
```

The Haystack agent connects only to the MCP proxy. It does not import provider pricing functions or policy catalogs. The proxy exposes namespaced tools and forwards each invocation to the appropriate independent provider server.

### Request flow

1. The React frontend sends the user message and visible conversation history to `POST /api/chat`.
2. The Haystack agent decides whether the question requires a tool.
3. General questions are answered directly without MCP traffic.
4. Provider-specific facts and actions go through the MCP proxy.
5. The proxy creates a correlation ID and forwards the request to one provider or the conditions RAG server.
6. The selected service returns structured data or retrieved condition documents.
7. The agent interprets the tool result and writes a coherent response instead of displaying raw JSON.

### MCP tools

Each provider implements the same three operations:

| Operation | Purpose |
| --- | --- |
| `get_quote` | Issue an illustrative auto, home, or life quote. |
| `check_coverage` | Return structured guarantees, exclusions, limits, terms, and deductibles. |
| `purchase_policy` | Purchase an active quote previously issued by that provider. |

The proxy exposes nine provider tools plus one RAG tool, for example:

- `thelion_get_quote`
- `thebluecompany_check_coverage`
- `thethreelines_purchase_policy`
- `search_insurance_conditions`

The RAG tool searches derived PDF chunks through a custom Haystack retriever. It accepts `auto`, `home`, or `life`, maps that type to one shared policy for all three companies, and returns page-aware sources that the assistant can cite.

## Technology

- Python 3.10+
- Haystack 2.31
- FastAPI
- MCP Python SDK
- Haystack MCP integration
- MongoDB Atlas or Community, and PyMongo
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
│   ├── rag/
│   │   ├── repository.py        # Policy metadata, chunks, indexes, and queries
│   │   ├── pdf_ingestion.py     # PDF download, extraction, and Haystack chunking
│   │   ├── retriever.py         # Custom Haystack retrieval component
│   │   ├── service.py           # Haystack retrieval pipeline
│   │   └── server.py            # Conditions MCP process on port 5084
│   ├── tests/                   # Unit, HTTP integration, and smoke tests
│   ├── config.py                # Centralized environment configuration
│   └── mcp_audit.py             # Correlated rotating JSON logs
├── InsuranceOfficeUI/           # Original React frontend
├── pyproject.toml                # Test and lint configuration
└── run_services.py               # Starts all six backend processes
```

## Prerequisites

Install:

- Python 3.10 or newer.
- Node.js 20 or newer.
- A reachable MongoDB deployment (MongoDB Atlas or Community).
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
MONGODB_URI=mongodb+srv://your_user:your_url_encoded_password@your_cluster.mongodb.net/?appName=your_app
MONGODB_DATABASE=insurance_office
MONGODB_POLICIES_COLLECTION=policy_conditions
MONGODB_CHUNKS_COLLECTION=insurance_condition_chunks
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
| Insurance Conditions RAG MCP | `http://127.0.0.1:5084/mcp` |
| Insurance MCP proxy | `http://127.0.0.1:5275/mcp` |
| FastAPI/Haystack API | `http://127.0.0.1:5100` |

Keep the terminal open. Press `Ctrl+C` to stop all six backend processes.

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
| `CONDITIONS_MCP_URL` | `http://127.0.0.1:5084/mcp` | Conditions RAG server URL used by the proxy. |
| `MONGODB_URI` | `mongodb://127.0.0.1:27017` | MongoDB Atlas or Community connection string. Treat it as a secret. |
| `MONGODB_DATABASE` | `insurance_office` | Database containing the conditions collection. |
| `MONGODB_POLICIES_COLLECTION` | `policy_conditions` | Authoritative policy metadata and PDF URLs. |
| `MONGODB_CHUNKS_COLLECTION` | `insurance_condition_chunks` | Derived, searchable PDF chunks. |
| `MONGODB_SESSIONS_COLLECTION` | `chat_sessions` | Conversation session metadata and sequence counters. |
| `MONGODB_MESSAGES_COLLECTION` | `chat_messages` | Ordered user and assistant messages with citations. |
| `MONGODB_QUOTES_COLLECTION` | `insurance_quotes` | Durable session-bound provider quotes. |
| `MONGODB_PURCHASES_COLLECTION` | `policy_purchases` | Confirmed purchases linked to their issued quote. |
| `MONGODB_VECTOR_INDEX` | `condition_chunk_vector_index` | Atlas Vector Search index used by hybrid retrieval. |
| `MONGODB_SERVER_SELECTION_TIMEOUT_MS` | `5000` | Fail-fast MongoDB connection timeout. |
| `CONDITIONS_AUTO_INGEST` | `false` | Download and re-index changed PDFs when the RAG MCP starts. |
| `RAG_RETRIEVAL_MODE` | `text` | Retrieval strategy: `text` or `hybrid`. |
| `RAG_EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model used for policy chunks and questions. |
| `RAG_EMBEDDING_DIMENSIONS` | `1536` | Vector size; it must match the Atlas index. |
| `RAG_VECTOR_CANDIDATES` | `50` | Candidate vectors considered before ranking. |
| `RAG_HYBRID_RRF_K` | `60` | Reciprocal-rank-fusion constant for text and vector results. |
| `RAG_CHUNK_SIZE_WORDS` | `500` | Maximum word count per Haystack chunk. |
| `RAG_CHUNK_OVERLAP_WORDS` | `75` | Word overlap between adjacent chunks. |
| `PDF_DOWNLOAD_TIMEOUT_SECONDS` | `30` | Timeout for each policy PDF download. |
| `PDF_MAX_BYTES` | `25000000` | Maximum accepted PDF size. |
| `PDF_STORAGE_BEARER_TOKEN` | empty | Optional bearer token for protected PDF storage. |
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
- Detailed questions about policy wording, terms, exclusions, or limits call `search_insurance_conditions` and cite its source identifiers.
- Detailed conditions are shared across providers: `SafeCar26.1` for auto, `HomeSafe26.1` for home, and `BeSafe26.1` for life.
- A purchase tool is called only after the user explicitly selects and confirms a quote.
- Tool responses are summarized into natural language.
- Prices and provider-specific facts are never invented.

The frontend stores only an opaque `sessionId` in browser local storage. FastAPI loads the last server-managed messages from MongoDB before each Haystack run, then stores the new user message, assistant reply, and structured citations. Reloading the page or restarting the backend preserves the conversation.

## Insurance conditions RAG

Policy metadata stays in `policy_conditions`; PDF text is stored separately in `insurance_condition_chunks`. The first collection remains the source of truth, while the second can always be rebuilt. The RAG service creates a unique chunk identity index, a category/policy filter index, and a weighted text index.

The default `text` mode uses MongoDB `$text` search and requires no embedding calls. The optional `hybrid` mode combines exact text matches with semantic Atlas Vector Search using reciprocal rank fusion. If embedding or vector retrieval is temporarily unavailable, it logs the failure and falls back to text search. A custom Haystack component converts matching chunks into Haystack `Document` objects. The conditions MCP returns policy, page, chunk, and retrieval-mode metadata to the conversational agent.

Expected source document in `policy_conditions`:

```json
{
  "id": 1,
  "category": "Car",
  "name_conditions": "SafeCar26.1",
  "storage_url": "https://storage.example/safe-car-26.pdf"
}
```

Download changed PDFs, extract page text, split it with Haystack, and rebuild their chunks with:

```powershell
.\.venv\Scripts\python.exe -m backend.rag.pdf_ingestion
```

Repeated runs skip PDFs whose SHA-256 hash and ingestion version have not changed. Successful ingestion adds `rag_indexed_pdf_hash`, `rag_indexed_at`, `rag_ingestion_version`, and `rag_chunk_count` to the metadata document. Version changes force derived chunks to be rebuilt, which prevents stale citation formats from surviving a chunker upgrade. Each chunk records its original PDF page, position, text, hashes, and a citation such as `SafeCar26.1#page-3-chunk-2`.

### Enable hybrid retrieval

Hybrid mode requires a deployment that supports MongoDB `$vectorSearch`. In MongoDB Atlas, create a Vector Search index named `condition_chunk_vector_index` on `insurance_condition_chunks`:

```json
{
  "fields": [
    {
      "type": "vector",
      "path": "embedding",
      "numDimensions": 1536,
      "similarity": "cosine"
    },
    {
      "type": "filter",
      "path": "category"
    },
    {
      "type": "filter",
      "path": "name_conditions"
    }
  ]
}
```

Then update `backend/.env`:

```dotenv
RAG_RETRIEVAL_MODE=hybrid
MONGODB_VECTOR_INDEX=condition_chunk_vector_index
RAG_EMBEDDING_MODEL=text-embedding-3-small
RAG_EMBEDDING_DIMENSIONS=1536
```

Re-run ingestion after enabling hybrid mode:

```powershell
.\.venv\Scripts\python.exe -m backend.rag.pdf_ingestion
```

The ingestor notices that existing chunks do not have embeddings for the selected model and enriches them even when the PDF hash has not changed. Restart the backend services after ingestion.

### Evaluate retrieval

The grounded dataset in `backend/rag/evaluation_cases.json` contains natural-language questions, expected policies, pages, and required terms taken from the sample PDFs. Run it against the database configured in `backend/.env`:

```powershell
.\.venv\Scripts\python.exe -m backend.rag.evaluate
```

The report includes page hit rate, mean reciprocal rank, required-term recall, and per-case sources. Optional thresholds make the command suitable for CI:

```powershell
.\.venv\Scripts\python.exe -m backend.rag.evaluate `
  --top-k 5 `
  --min-hit-rate 0.90 `
  --min-term-recall 0.90
```

Run the evaluator once in `text` mode to record a baseline, then again in `hybrid` mode and compare the same cases.

The current `http://storage.com/...` values are placeholders unless that host is controlled by your application. Replace them with URLs that return actual PDF bytes. Scanned image-only PDFs require OCR before this pipeline can index them.

## Quotes and purchases

Every company quote includes:

- `quoteId`
- `expiresAt`
- Annual and monthly premium
- Provider identity
- Coverage type
- Structured included guarantees

All three company MCP processes share a MongoDB issued-quote ledger. Every quote is bound to the opaque conversation session that requested it. A purchase succeeds only when:

- The company previously issued a matching quote.
- The quote has not expired.
- The annual premium has not been changed.
- The quote has not already been purchased.
- The purchasing session is the session that requested the quote.

Quotes survive company-server and API restarts. Confirmed purchases are written to `policy_purchases`, while an atomic quote status update prevents a second purchase. Session binding provides isolation for the demo, but it is not a replacement for authenticated customer ownership.

The API and company services create their required MongoDB indexes idempotently on startup. The configured database user therefore needs permission to create indexes and read/write these four collections.

## HTTP API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Check API, proxy, tool count, and chat mode. |
| `GET` | `/api/providers` | List configured providers. |
| `POST` | `/api/sessions` | Create a persistent conversation. |
| `GET` | `/api/sessions/{id}/messages` | Resume a conversation from MongoDB. |
| `POST` | `/api/sessions/{id}/messages` | Send a message using server-managed history. |
| `DELETE` | `/api/sessions/{id}` | Delete a session and its messages. |
| `POST` | `/api/chat` | Legacy non-persistent compatibility endpoint. |
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
  "toolCount": 10,
  "mode": "live"
}
```

### Quote comparison

```powershell
$session = Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:5100/api/sessions

$body = @{
  age = 35
  coverageType = "auto"
  assetValue = 25000
  sessionId = $session.sessionId
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
  sessionId = $session.sessionId
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
- `backend/logs/mcp-conditions.log`

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
- Server-managed conversation persistence and restoration.
- Quote restart recovery and cross-session isolation.
- Model compatibility settings.
- API request contracts.
- MCP audit formatting.
- MongoDB condition ingestion, text/hybrid retrieval, fallback behavior, and grounded evaluation metrics.

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
  Where-Object LocalPort -in 5081,5082,5083,5084,5100,5275 |
  Select-Object LocalPort,OwningProcess
```

Stop only the listed stale backend process IDs, then run `python run_services.py` again.

### Creating the virtual environment appears frozen

The first `python -m venv .venv` may spend time installing pip. Let it finish. If `.venv` already exists and works, activate it instead of recreating it.

### Backend startup takes time

Haystack imports can be slow on the first run. The launcher allows up to 90 seconds for each service and reports when all services are ready.

### The Conditions RAG service does not start

Confirm that MongoDB is reachable using `MONGODB_URI`. For Atlas, allow your current IP in Network Access, create a database user, and URL-encode reserved characters in its password. For local Community, verify port `27017`:

```powershell
Get-NetTCPConnection -LocalPort 27017 -State Listen
```

Run `python -m backend.rag.pdf_ingestion` before starting the services. HTTP errors point to an invalid or inaccessible `storage_url`; a no-text error means the PDF requires OCR.

## Current limitations

- Provider data and purchases are illustrative.
- There is no authentication or customer database.
- Opaque session IDs isolate browser conversations but are bearer identifiers, not authenticated identities.
- The OpenAI integration currently uses Chat Completions rather than the Responses API.
- Hybrid retrieval requires a compatible MongoDB Vector Search index and incurs embedding API usage.
- The original frontend is intentionally unchanged and still contains unused legacy `.NET` start scripts.

## Security notes

- Keep `backend/.env` out of version control.
- Treat `MONGODB_URI` as a secret when it contains credentials.
- Never log or return the OpenAI API key.
- MCP audit records intentionally exclude business payload values.
- Add authentication, authorization, rate limiting, and durable audit retention before treating this architecture as production-ready.

## License

No license has been added yet. Add one before distributing or accepting external contributions.
