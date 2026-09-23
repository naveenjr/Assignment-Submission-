# Known limitations

- The alarm API and documents are synthetic demo data.
- RAG embeddings use the external OpenAI `text-embedding-3-small` model and
  therefore require an API key and approval to send document text externally.
- LLM execution requires an OpenAI-compatible API key.
- MCP runs over stdio for local simplicity; production deployment should use an authenticated remote transport.
- Langfuse tracing is not enabled in Version 1. It is planned as an optional
  local Docker Compose service for future LLM, MCP, and RAG observability.
