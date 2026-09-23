from pathlib import Path


def ingest(source: str = "rag/documents") -> list[dict]:
    """Load Markdown procedure documents as citation-ready records."""
    return [
        {"source": path.name, "text": path.read_text(encoding="utf-8")}
        for path in Path(source).glob("*.md")
    ]
