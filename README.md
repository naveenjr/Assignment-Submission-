# Minimal Alarm Investigation Copilot

This submission follows the requested structure and implements one vertical slice:
Streamlit UI -> LangGraph LLM tool calling -> MCP client/server -> Alarm API simulator + RAG evidence.

## Run

```powershell
uv sync
$env:OPENAI_API_KEY = "your-key"
uv run uvicorn apps.backend.main:app --port 8000
uv run streamlit run apps/frontend/app.py
```

Or:

```powershell
docker compose up --build
```

### Fresh Windows environment with uv

Install `uv` if it is not already available:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Then create the project environment and install the locked dependencies:

```powershell
cd "C:\Users\Naveen\OneDrive\Desktop\ABB\Alarm-Investigation-and-Procedure-Guidance\submission"
uv sync
$env:OPENAI_API_KEY = "your-openai-api-key"
```

### Configuration from `.env`

Copy the safe template before starting the application:

```bash
cp .env.example .env
```

Edit `.env` and replace `replace-me` with your new LLM key:

```env
OPENAI_API_KEY=your-new-openai-api-key
LLM_MODEL=gpt-4o-mini
ALARM_API_BASE_URL=http://127.0.0.1:8000
ALARM_API_TOKEN=demo-token
RAG_EMBEDDING_MODEL=text-embedding-3-small
```

The application loads `.env` automatically through `python-dotenv`. `.env.example`
is only a template and must not contain a real secret. The `.env` file is ignored
by Git. RAG uses OpenAI embeddings, so the first retrieval request sends the
document chunks and query to OpenAI and requires a valid `OPENAI_API_KEY`.
Change `RAG_EMBEDDING_MODEL` only to another embedding model available to the
configured OpenAI account.

Use `uv run` for all project commands. It automatically uses the `.venv` created by `uv sync`:

```powershell
# Terminal 1
uv run uvicorn apps.backend.main:app --host 127.0.0.1 --port 8000

# Terminal 2
uv run streamlit run apps/frontend/app.py
```

To recreate the environment exactly from the lock file:

```powershell
uv sync --locked
```

## Test

```powershell
uv run pytest tests -q
```

The test suite includes:

- LLM configuration and fake-model graph execution
- MCP server startup and tool discovery
- RAG procedure retrieval
- Alarm API asset search

## Sample questions

Try these in the Streamlit UI:

- `Show active critical alarms for Boiler Feed Pump 102 and recommend immediate actions.`
- `What are the likely causes of alarm ALM-1001?`
- `Which assets are related to the high discharge pressure alarm on Boiler Feed Pump 102?`
- `What does the procedure recommend before isolating a pump for inspection?`
- `Show active alarms for Compressor 204 and summarize the operator response.`

## Structure

- `apps/backend/`: simulator API and LangGraph orchestrator
- `apps/frontend/`: Streamlit UI
- `mcp-servers/alarm-management/`: MCP server
- `connectors/`: Alarm API connector and demo data
- `rag/ingestion/`, `rag/retrieval/`, `rag/documents/`: RAG workflow
- `tests/`: unit and integration tests
- `docs/`: architecture, MCP, RAG, and limitations

## LLM tool-calling flow

The LLM receives typed LangChain tools. When it calls a tool, the tool opens an MCP client session, discovers the MCP server tools, invokes the requested MCP tool, and returns the result to the LangGraph message state. The MCP server then calls the Alarm API. The LLM receives RAG snippets and MCP results before writing the grounded answer.


## Future observability

Langfuse is intentionally not part of the current runtime dependencies. A
future local Docker Compose setup can run Langfuse at `http://localhost:3000`
and instrument the LangGraph invocation, MCP spans, and RAG retrieval with the
same correlation ID already shown in the UI. This keeps observability
optional and avoids adding another service or credential requirement to the
Version 1 submission.
