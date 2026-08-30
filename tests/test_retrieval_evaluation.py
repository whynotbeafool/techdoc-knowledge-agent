import pytest
from app.evaluation.retrieval import (
    BM25Retriever,
    ReciprocalRankFusionRetriever,
    retrieval_metrics,
)
from app.rag.chunker import Chunk


def test_bm25_ranks_exact_term_match_first():
    chunks = [
        Chunk("a", "a.txt", None, "kubernetes deployment", 0, 21, "a", "v1"),
        Chunk("b", "b.txt", None, "python formatting", 0, 17, "b", "v1"),
    ]

    results = BM25Retriever(chunks).query_chunks("kubernetes", top_k=2)

    assert results[0]["chunk_id"] == "a"
    assert results[0]["score"] > results[1]["score"]


def test_retrieval_metrics_compute_partial_and_complete_evidence_hits():
    record = {
        "evidence": [
            {
                "document_id": "doc",
                "revision": "v1",
                "start_char": 10,
                "end_char": 20,
            },
            {
                "document_id": "doc",
                "revision": "v1",
                "start_char": 30,
                "end_char": 40,
            },
        ]
    }
    ranked = [
        {
            "document_id": "doc",
            "revision": "v1",
            "start_char": 5,
            "end_char": 15,
        },
        {
            "document_id": "other",
            "revision": "v1",
            "start_char": 30,
            "end_char": 40,
        },
        {
            "document_id": "doc",
            "revision": "v1",
            "start_char": 35,
            "end_char": 45,
        },
    ]

    metrics = retrieval_metrics(record, ranked, ks=(1, 3))

    assert metrics["evidence_recall_at_1"] == 0.5
    assert metrics["complete_evidence_hit_at_1"] is False
    assert metrics["evidence_recall_at_3"] == 1.0
    assert metrics["complete_evidence_hit_at_3"] is True


class _StaticRetriever:
    def __init__(self, chunk_ids):
        self.chunk_ids = chunk_ids
        self.requested_top_k = []

    def query_chunks(self, question, top_k=5):
        self.requested_top_k.append(top_k)
        return [
            {
                "chunk_id": chunk_id,
                "document_id": "doc",
                "revision": "v1",
                "start_char": index,
                "end_char": index + 1,
                "score": 100 - index,
            }
            for index, chunk_id in enumerate(self.chunk_ids[:top_k])
        ]


def test_rrf_combines_component_ranks_and_removes_raw_scores():
    bm25 = _StaticRetriever(["shared", "bm25-only"])
    dense = _StaticRetriever(["dense-only", "shared"])
    retriever = ReciprocalRankFusionRetriever(
        {"bm25": bm25, "dense": dense},
        rank_constant=60,
        candidate_depth=20,
    )

    results = retriever.query_chunks("question", top_k=3)

    assert [result["chunk_id"] for result in results] == [
        "shared",
        "dense-only",
        "bm25-only",
    ]
    assert results[0]["rrf_score"] == pytest.approx(1 / 61 + 1 / 62)
    assert results[0]["component_ranks"] == {"bm25": 1, "dense": 2}
    assert "score" not in results[0]
    assert bm25.requested_top_k == [20]
    assert dense.requested_top_k == [20]


@pytest.mark.parametrize(
    ("retrievers", "rank_constant", "candidate_depth", "message"),
    [
        ({"bm25": _StaticRetriever([])}, 60, 20, "at least two"),
        (
            {"bm25": _StaticRetriever([]), "dense": _StaticRetriever([])},
            -1,
            20,
            "non-negative",
        ),
        (
            {"bm25": _StaticRetriever([]), "dense": _StaticRetriever([])},
            60,
            0,
            "positive",
        ),
    ],
)
def test_rrf_rejects_invalid_configuration(
    retrievers,
    rank_constant,
    candidate_depth,
    message,
):
    with pytest.raises(ValueError, match=message):
        ReciprocalRankFusionRetriever(
            retrievers,
            rank_constant=rank_constant,
            candidate_depth=candidate_depth,
        )
