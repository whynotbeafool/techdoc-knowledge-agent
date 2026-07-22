from app.rag.chunker import Chunk
from app.rag.retriever import ChromaRetriever


def test_index_and_query_returns_matching_chunk(tmp_path):
    """A chunk that's indexed should be retrievable via query_chunks() when the
    query text is semantically close to it. Uses tmp_path so each test gets its
    own throwaway Chroma database, isolated from the real data/vector_store/.
    """
    retriever = ChromaRetriever(str(tmp_path))
    chunk = Chunk(
        chunk_id="doc.txt_p0_0",
        source="doc.txt",
        page=None,
        text="FastAPI is a modern Python web framework",
    )

    retriever.index_chunks([chunk])
    results = retriever.query_chunks("What is FastAPI?", top_k=1)

    assert len(results) == 1
    assert results[0]["chunk_id"] == "doc.txt_p0_0"
    assert results[0]["source"] == "doc.txt"
    assert results[0]["page"] == 0  # page=None is stored as 0 — Chroma metadata can't hold None


def test_index_chunks_with_empty_list_does_nothing(tmp_path):
    """index_chunks([]) should be a no-op, not raise an error."""
    retriever = ChromaRetriever(str(tmp_path))
    retriever.index_chunks([])  # should not raise

    results = retriever.query_chunks("anything", top_k=5)
    assert results == []


def test_query_chunks_on_empty_collection_returns_empty_list(tmp_path):
    """Querying a fresh collection with nothing indexed should return [] cleanly,
    not raise — this is what lets ask.py / streamlit_app.py show a friendly
    "no results" message instead of crashing.
    """
    retriever = ChromaRetriever(str(tmp_path))
    results = retriever.query_chunks("anything", top_k=5)
    assert results == []
