from pathlib import Path

from rag.ingestion.ingest import ingest

ROOT = Path(__file__).parents[1] / "documents"


def retrieve(query: str, top_k: int = 3) -> list[dict]:
    """Return local procedure snippets ranked by simple term overlap."""
    terms = {term.lower() for term in query.replace("-", " ").split() if len(term) > 2}
    hits = []
    for document in ingest(str(ROOT)):
        text = document["text"]
        score = sum(text.lower().count(term) for term in terms)
        if score:
            hits.append({"source": document["source"], "score": score, "excerpt": text[:800]})
    return sorted(hits, key=lambda item: item["score"], reverse=True)[:top_k]
