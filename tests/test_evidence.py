import pytest
from app.corpus.canonical import LoadedCanonicalDocument
from app.evaluation.evidence import evidence_span_hits_chunk
from app.rag.chunker import chunk_canonical_document


@pytest.mark.parametrize(
    ("evidence", "chunk"),
    [
        ((1280, 1331), (1200, 1300)),  # Partial overlap at evidence start.
        ((1280, 1331), (1300, 1400)),  # Partial overlap at evidence end.
        ((1280, 1331), (1200, 1400)),  # Chunk fully contains evidence.
        ((1280, 1331), (1290, 1300)),  # Evidence fully contains chunk.
        ((1280, 1331), (1280, 1331)),  # Exact match.
    ],
)
def test_evidence_span_hits_chunk_for_any_positive_overlap(evidence, chunk):
    assert evidence_span_hits_chunk(*evidence, *chunk)


@pytest.mark.parametrize(
    ("evidence", "chunk"),
    [
        ((1280, 1331), (1000, 1200)),  # Disjoint before evidence.
        ((1280, 1331), (1400, 1500)),  # Disjoint after evidence.
        ((1280, 1331), (1200, 1280)),  # Touches evidence start only.
        ((1280, 1331), (1331, 1400)),  # Touches evidence end only.
    ],
)
def test_evidence_span_does_not_hit_without_positive_overlap(evidence, chunk):
    assert not evidence_span_hits_chunk(*evidence, *chunk)


@pytest.mark.parametrize(
    ("evidence", "chunk"),
    [
        ((-1, 10), (0, 10)),
        ((10, 10), (0, 10)),
        ((11, 10), (0, 10)),
        ((0, 10), (-1, 10)),
        ((0, 10), (10, 10)),
        ((0, 10), (11, 10)),
    ],
)
def test_evidence_span_rejects_invalid_intervals(evidence, chunk):
    with pytest.raises(ValueError):
        evidence_span_hits_chunk(*evidence, *chunk)


def test_canonical_chunk_offsets_connect_to_evidence_hit_mapping():
    text = "retrieval evidence\n\nunrelated paragraph"
    document = LoadedCanonicalDocument(
        text=text,
        metadata={
            "document_id": "doc001",
            "document_version": "v1",
            "source_file": "doc.txt",
            "page_spans": [{"page": None, "start_char": 0, "end_char": len(text)}],
        },
    )
    chunks = chunk_canonical_document(document, max_chars=20)
    evidence_start = text.index("evidence")
    evidence_end = evidence_start + len("evidence")

    hits = [
        chunk
        for chunk in chunks
        if evidence_span_hits_chunk(
            evidence_start,
            evidence_end,
            chunk.start_char,
            chunk.end_char,
        )
    ]

    assert len(hits) == 1
    assert "evidence" in hits[0].text
