from retriever import Chunk, TfIdfIndex, get_index


def test_index_loads_all_strategy_docs():
    index = get_index()
    sources = {entry.chunk.source for entry in index.entries}
    assert "binary_search.md" in sources
    assert "common_mistakes.md" in sources
    assert "endgame.md" in sources
    assert "information_theory.md" in sources
    assert "persistence_and_tilt.md" in sources
    assert "range_narrowing.md" in sources


def test_retrieve_binary_search_query():
    index = get_index()
    results = index.retrieve("midpoint of the range halve eliminate candidates", k=2)
    assert len(results) > 0
    top_sources = {chunk.source for chunk in results}
    assert "binary_search.md" in top_sources or "information_theory.md" in top_sources


def test_retrieve_endgame_query():
    index = get_index()
    results = index.retrieve("only two candidates left forced move closing", k=1)
    assert len(results) == 1
    assert results[0].source == "endgame.md"


def test_retrieve_mistakes_query():
    index = get_index()
    results = index.retrieve("player repeating numbers ruled out anchoring", k=1)
    assert len(results) == 1
    assert results[0].source == "common_mistakes.md"


def test_retrieve_empty_query_returns_empty():
    assert get_index().retrieve("", k=2) == []
    assert get_index().retrieve("    ", k=2) == []


def test_retrieve_respects_k():
    results = get_index().retrieve("range guess midpoint candidates", k=3)
    assert len(results) <= 3


def test_index_handles_custom_corpus():
    chunks = [
        Chunk(title="A", source="a.md", text="apple banana apple"),
        Chunk(title="B", source="b.md", text="cherry date elderberry"),
    ]
    index = TfIdfIndex(chunks)
    results = index.retrieve("banana", k=1)
    assert results[0].source == "a.md"
