from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

from rag.ingestion.ingest import ingest

ROOT = Path(__file__).parents[1] / "documents"
STOP_WORDS = {"procedure", "procedures", "maintenance", "guide", "guidance", "instruction"}


@lru_cache(maxsize=1)
def _embeddings() -> OpenAIEmbeddings:
    """Create the configured OpenAI embedding client once per process."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "replace-me":
        raise RuntimeError("Set OPENAI_API_KEY before using document retrieval.")
    return OpenAIEmbeddings(
        model=os.getenv("RAG_EMBEDDING_MODEL", "text-embedding-3-small"),
        api_key=api_key,
    )


def retrieve(query: str, top_k: int = 3) -> list[dict]:
    """Run OpenAI semantic retrieval plus lexical reranking."""
    documents = ingest(str(ROOT))
    if not documents:
        return []
    index = FAISS.from_documents(documents, _embeddings())
    vector_hits = index.similarity_search_with_score(
        query, k=min(len(documents), max(top_k * 3, 5))
    )
    terms = {
        term
        for term in re.findall(r"[a-z0-9]+", query.lower())
        if len(term) > 2 and term not in STOP_WORDS
    }
    ranked = []
    for document, distance in vector_hits:
        lexical = sum(document.page_content.lower().count(term) for term in terms)
        if lexical == 0 and float(distance) > 1.0:
            continue
        vector_score = 1.0 / (1.0 + float(distance))
        ranked.append(
            {
                "source": document.metadata["source"],
                "section": document.metadata["section"],
                "chunk": document.metadata["chunk"],
                "score": round(lexical + vector_score, 4),
                "excerpt": document.page_content[:800],
            }
        )
    return sorted(ranked, key=lambda item: item["score"], reverse=True)[:top_k]
