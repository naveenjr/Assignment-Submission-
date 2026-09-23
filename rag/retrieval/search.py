from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import Embeddings

from rag.ingestion.ingest import ingest

ROOT = Path(__file__).parents[1] / "documents"
STOP_WORDS = {"procedure", "procedures", "maintenance", "guide", "guidance", "instruction"}


class LocalHashEmbeddings(Embeddings):
    """Dependency-light deterministic embeddings for the local demo corpus."""

    dimensions = 256

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in re.findall(r"[a-z0-9]+", text.lower()):
            position = int(hashlib.sha256(token.encode()).hexdigest(), 16) % self.dimensions
            vector[position] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


def retrieve(query: str, top_k: int = 3) -> list[dict]:
    """Run hybrid lexical/vector retrieval and return citation-ready snippets."""
    documents = ingest(str(ROOT))
    if not documents:
        return []
    index = FAISS.from_documents(documents, LocalHashEmbeddings())
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
