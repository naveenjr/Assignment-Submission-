# Known limitations

- The alarm API and documents are synthetic demo data.
- The FAISS vector index uses deterministic local hash embeddings for an offline
  demo; production should evaluate a domain-tuned embedding model.
- LLM execution requires an OpenAI-compatible API key.
- MCP runs over stdio for local simplicity; production deployment should use an authenticated remote transport.
- Langfuse tracing is not enabled in Version 1. It is planned as an optional
  local Docker Compose service for future LLM, MCP, and RAG observability.
