from app.evaluation.retrieval import BM25Retriever, retrieval_metrics
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
