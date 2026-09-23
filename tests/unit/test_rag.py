from rag.retrieval.search import retrieve
from rag.ingestion.ingest import ingest


def test_retrieval_returns_procedure_source():
    results = retrieve("Boiler Feed Pump 102 discharge pressure")
    assert results
    assert results[0]["source"] == "boiler-feed-pump-102.md"
    assert results[0]["section"]
    assert "excerpt" in results[0]


def test_retrieval_returns_empty_for_unknown_topic():
    assert retrieve("quantum telescope maintenance procedure") == []


def test_ingestion_creates_multiple_metadata_rich_chunks():
    documents = ingest("rag/documents")
    pump_chunks = [document for document in documents if document.metadata["asset_id"] == "BFP-102"]
    assert len(pump_chunks) > 1
    assert pump_chunks[0].metadata["revision"] == "Rev 2"
    assert "Document: Boiler Feed Pump 102 Operating Procedure" in pump_chunks[0].page_content
