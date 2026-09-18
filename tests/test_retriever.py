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
        start_char=10,
        end_char=50,
        document_id="doc",
        revision="v1",
    )

    retriever.index_chunks([chunk])
    results = retriever.query_chunks("What is FastAPI?", top_k=1)

    assert len(results) == 1
    assert results[0]["chunk_id"] == "doc.txt_p0_0"
    assert results[0]["source"] == "doc.txt"
    assert results[0]["page"] == 0  # page=None is stored as 0 — Chroma metadata can't hold None
    assert results[0]["start_char"] == 10
    assert results[0]["end_char"] == 50
    assert results[0]["document_id"] == "doc"
    assert results[0]["revision"] == "v1"


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
    retriever.close()


def test_describe_reports_the_live_collection_not_the_model_name(tmp_path):
    """The run config must record what governs ranking, read from live objects.

    The model declares cosine but the collection is created with Chroma's
    default l2; that only ranks identically because vectors are unit-normalised.
    All three facts are asserted here so a future embedder or Chroma default
    that breaks the equivalence fails loudly instead of silently changing
    results while the config still looks the same.
    """
    retriever = ChromaRetriever(str(tmp_path))
    try:
        settings = retriever.describe()
    finally:
        retriever.close()

    assert settings["collection_space"] == "l2"
    assert settings["model_declared_space"] == "cosine"
    assert settings["embeddings_unit_normalised"] is True

    # Identity of the artifact that actually embedded, not the shim around it.
    assert settings["implementation"] == "ONNXMiniLM_L6_V2"
    assert settings["model"] == "all-MiniLM-L6-v2"
    assert len(settings["model_sha256"]) == 64
    assert settings["max_tokens"] == 256
    assert settings["embedding_dim"] == 384


def test_describe_is_flat_so_the_report_table_can_render_it(tmp_path):
    retriever = ChromaRetriever(str(tmp_path))
    try:
        settings = retriever.describe()
    finally:
        retriever.close()

    assert all(not isinstance(v, (dict, list)) for v in settings.values())
