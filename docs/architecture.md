# Minimal architecture

![Architecture diagram](architecture-diagram.png)

```text
Streamlit UI
    -> LangGraph orchestrator
       -> LLM with bound tools
          -> MCP client (stdio)
             -> Alarm MCP server
                -> Alarm API simulator
       -> RAG retrieval
    -> grounded answer + document citations + tool messages
```

The LLM chooses the next typed tool. At investigation startup, the gateway
discovers MCP tools and generates the LangGraph adapters from their schemas;
there are no duplicated operational tool declarations in the orchestrator.
Every generated adapter calls the MCP client. The MCP server is the only
component allowed to call the Alarm API. RAG evidence is added to the graph
state before final synthesis.

The gateway performs `tools/list` before every invocation, validates that the
requested tool exists, passes the investigation correlation ID to MCP, and
records discovery/invocation/completion events for the Streamlit trace. The
LLM can chain the result of asset search into alarm retrieval and then into
summary, correlation, or recommendations.

## Boundary rule

- **MCP owns operations:** asset lookup, alarm retrieval, summaries, correlation, and recommendations are all MCP tools. The LLM never calls the Alarm API or connector directly.
- **RAG owns information:** RAG only reads local procedures and returns source snippets. It cannot change alarms, call plant APIs, or execute instructions.
- **LangGraph owns orchestration:** it routes LLM tool calls and feeds MCP results back to the LLM.

The LangChain `@tool` functions in `apps/backend/orchestrator.py` are thin adapters required by LangGraph's tool-calling interface. They do not implement business operations; each immediately invokes the same-named MCP tool. This is the only intentional exception to having the LLM-facing tools physically declared in the MCP server.

The physical folders intentionally match the assignment:

- `apps/backend`: API simulator and orchestration
- `apps/frontend`: Streamlit
- `mcp-servers/alarm-management`: MCP server
- `rag/ingestion`, `rag/retrieval`, `rag/documents`: document workflow
- `connectors`: source-system connector
- `tests/unit`, `tests/integration`, `tests/e2e`: automated checks
