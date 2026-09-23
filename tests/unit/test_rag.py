from rag.retrieval.search import retrieve


def test_retrieval_returns_procedure_source():
    results = retrieve("Boiler Feed Pump 102 discharge pressure")
    assert results
    assert results[0]["source"] == "boiler-feed-pump-102.md"
