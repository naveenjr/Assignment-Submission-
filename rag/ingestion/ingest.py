from __future__ import annotations

import re
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

_HEADING = re.compile(r"(?m)^(#{1,3})\s+(.+?)\s*$")
_FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _metadata(text: str, path: Path) -> dict[str, str]:
    """Read simple YAML-like front matter without requiring a YAML parser."""
    match = _FRONTMATTER.match(text)
    values = {
        "source": path.name,
        "document_type": "markdown_procedure",
        "source_id": path.stem,
    }
    if not match:
        return values
    for line in match.group(1).splitlines():
        key, separator, value = line.partition(":")
        if separator:
            field = key.strip()
            values["source_id" if field == "source" else field] = value.strip()
    return values


def ingest(source: str = "rag/documents") -> list[Document]:
    """Load Markdown files into heading-aware, citation-ready chunks."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=120,
        separators=["\n\n", "\n", ". ", " "],
    )
    documents: list[Document] = []
    for path in sorted(Path(source).glob("*.md")):
        text = path.read_text(encoding="utf-8")
        metadata = _metadata(text, path)
        body = _FRONTMATTER.sub("", text, count=1)
        matches = list(_HEADING.finditer(body))
        sections = []
        if not matches:
            sections.append(("document", body))
        else:
            for index, match in enumerate(matches):
                end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
                sections.append((match.group(2).strip(), body[match.start():end].strip()))
        for heading, section in sections:
            for chunk_index, chunk in enumerate(splitter.split_text(section)):
                chunk_text = f"Document: {metadata.get('title', path.stem)}\nSection: {heading}\n\n{chunk}"
                documents.append(
                    Document(
                        page_content=chunk_text,
                        metadata={
                            **metadata,
                            "section": heading,
                            "chunk": chunk_index,
                        },
                    )
                )
    return documents
