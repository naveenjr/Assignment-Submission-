# Design decisions

- Python is used for the  working MCP, LangGraph, and Streamlit stack.
- The LLM uses LangChain tool calling; each tool delegates to MCP.
- The MCP server owns all Alarm API access.
- RAG is local and deterministic so the demo can run without a vector database.
- A real `OPENAI_API_KEY` is required for LLM execution and is never committed.
- Langfuse is deferred as an optional future observability service. If enabled,
  it should run locally with Docker Compose and receive only approved,
  redacted traces.
