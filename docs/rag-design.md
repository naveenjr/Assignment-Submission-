# RAG design

Documents are Markdown procedures, troubleshooting guides, and safety instructions in `rag/documents/`. `rag/ingestion/ingest.py` loads documents; `rag/retrieval/search.py` performs deterministic term-overlap retrieval and returns source names and excerpts for citations.

This minimal implementation has no external vector database. It handles no-result retrieval by returning an empty source list, and retrieved text is provided as evidence rather than executable instructions. The corpus is intentionally synthetic.
