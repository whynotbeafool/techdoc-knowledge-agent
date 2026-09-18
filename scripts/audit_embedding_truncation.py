"""Read-only audit: does the dense embedder truncate chunks, and does that hide gold evidence?

Chroma's DefaultEmbeddingFunction (ONNX all-MiniLM-L6-v2) calls
``enable_truncation(max_length=256)``, so any chunk longer than 256 tokens is
silently shortened before it is embedded. The model card alone cannot settle
whether that happens here: it depends on this corpus and this chunk size, so
it has to be measured.

Two distinct questions are reported separately, because they have different
consequences:

1. How many chunks are truncated at all. Truncated distractors are still
   scored, on less text than they contain, which cannot be ruled out as an
   influence on ranking.
2. Whether any gold evidence span falls past the truncation point. If it did,
   dense retrieval could not match that evidence by its own content and the
   dense baseline would be measuring truncation rather than semantics.

Makes no model calls beyond tokenisation, and writes nothing.

    python scripts/audit_embedding_truncation.py
"""

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.corpus import load_active_revision_records, load_canonical_document  # noqa: E402
from app.evaluation.evidence import evidence_span_hits_chunk  # noqa: E402
from app.evaluation.truncation import (  # noqa: E402
    evidence_beyond_visible_window,
    visible_character_count,
)
from app.rag.chunker import DEFAULT_MAX_CHARS, chunk_canonical_document  # noqa: E402


def _load_tokenizer():
    import chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 as onnx

    function = onnx.ONNXMiniLM_L6_V2()
    function._download_model_if_not_exists()
    tokenizer = function.tokenizer
    # Measure true lengths; the embedder's own truncation is what we are auditing.
    tokenizer.no_truncation()
    tokenizer.no_padding()
    return tokenizer, function.max_tokens()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-dir", type=Path, default=PROJECT_ROOT / "data" / "corpus")
    parser.add_argument("--qa", type=Path, default=PROJECT_ROOT / "data" / "eval" / "qa.jsonl")
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_MAX_CHARS)
    args = parser.parse_args()

    tokenizer, max_tokens = _load_tokenizer()

    chunks = []
    for record in load_active_revision_records(args.corpus_dir):
        document = load_canonical_document(
            args.corpus_dir,
            document_id=record["document_id"],
            revision=record["revision"],
        )
        chunks.extend(chunk_canonical_document(document, max_chars=args.chunk_size))

    encodings = {chunk.chunk_id: tokenizer.encode(chunk.text) for chunk in chunks}
    token_lengths = {cid: len(encoding.ids) for cid, encoding in encodings.items()}
    truncated = sorted(
        (cid for cid, n in token_lengths.items() if n > max_tokens),
        key=lambda cid: -token_lengths[cid],
    )

    qa_records = [
        json.loads(line)
        for line in args.qa.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    hidden = []
    for record in qa_records:
        for evidence in record.get("evidence") or []:
            for chunk in chunks:
                if chunk.document_id != evidence["document_id"]:
                    continue
                if chunk.revision != evidence["revision"]:
                    continue
                if not evidence_span_hits_chunk(
                    evidence["start_char"],
                    evidence["end_char"],
                    chunk.start_char,
                    chunk.end_char,
                ):
                    continue
                visible = visible_character_count(
                    encodings[chunk.chunk_id], len(chunk.text), max_tokens
                )
                lost = evidence_beyond_visible_window(
                    evidence_start=evidence["start_char"],
                    evidence_end=evidence["end_char"],
                    chunk_start=chunk.start_char,
                    chunk_end=chunk.end_char,
                    visible_chars=visible,
                )
                if lost:
                    hidden.append(
                        {
                            "question_id": record["question_id"],
                            "evidence_id": evidence["evidence_id"],
                            "chunk_id": chunk.chunk_id,
                            "lost_characters": lost,
                        }
                    )

    lengths = list(token_lengths.values())
    report = {
        "model_max_tokens": max_tokens,
        "chunk_size": args.chunk_size,
        "chunk_count": len(chunks),
        "token_length": {
            "min": min(lengths),
            "median": statistics.median(lengths),
            "mean": round(statistics.mean(lengths), 1),
            "max": max(lengths),
        },
        "truncated_chunks": len(truncated),
        "truncated_fraction": round(len(truncated) / len(chunks), 4),
        "worst_truncations": [
            {"chunk_id": cid, "tokens": token_lengths[cid], "lost_tokens": token_lengths[cid] - max_tokens}
            for cid in truncated[:5]
        ],
        "gold_evidence_hidden_by_truncation": hidden,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
