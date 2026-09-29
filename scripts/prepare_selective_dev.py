"""Prepare exposed development inputs and runtime proxies; no LLM calls or scores of answers."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
from app.corpus import load_active_revision_records, load_canonical_document  # noqa: E402
from app.evaluation.integrity import verify_frozen_qa  # noqa: E402
from app.evaluation.retrieval import BM25Retriever  # noqa: E402
from app.evaluation.selective import validate_group_split  # noqa: E402
from app.rag.chunker import chunk_canonical_document  # noqa: E402
from app.rag.gating import ContextChunk, runtime_features  # noqa: E402


def write_jsonl(path, rows):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise ValueError("Use a new output directory")
    qa_path = ROOT / "data/eval/qa.jsonl"
    identity = verify_frozen_qa(qa_path)
    # Explicit projection: gold/answers/status must never be forwarded to runtime features.
    public = [
        {"question_id": r["question_id"], "question": r["question"]}
        for r in map(json.loads, qa_path.read_text(encoding="utf-8").splitlines())
    ]
    split = [
        {
            "question_id": r["question_id"],
            "group_id": "legacy-exposed-30",
            "split": "dev",
            "previously_exposed": True,
            "group_previously_exposed": True,
        }
        for r in public
    ]
    validate_group_split(split, enforce_assignment=True)
    chunks = []
    corpus = ROOT / "data/corpus"
    active_records = load_active_revision_records(corpus)
    for record in active_records:
        document = load_canonical_document(
            corpus, document_id=record["document_id"], revision=record["revision"]
        )
        chunks.extend(chunk_canonical_document(document, max_chars=800))
    bm25 = BM25Retriever(chunks)
    lookup = {c.chunk_id: c for c in chunks}
    rows = []
    for question in public:
        retrieved = bm25.query_chunks(question["question"], top_k=5)
        context = [ContextChunk(text=lookup[c["chunk_id"]].text, score=c["score"]) for c in retrieved]
        rows.append(
            {**question, "retrieved": retrieved, "features": runtime_features(question["question"], context)}
        )
    args.output_dir.mkdir(parents=True)
    write_jsonl(args.output_dir / "public-questions.jsonl", public)
    write_jsonl(args.output_dir / "split.jsonl", split)
    write_jsonl(args.output_dir / "runtime-features.jsonl", rows)
    manifest = {
        "protocol_version": "selective-v0.2-dev",
        "status": "features_only_no_generation",
        "qa_identity": identity,
        "question_n": len(public),
        "chunk_n": len(chunks),
        "corpus": [{k: r[k] for k in ("document_id", "revision", "text_hash")} for r in active_records],
        "method": "bm25",
        "top_k": 5,
        "chunk_size": 800,
        "generator_calls": 0,
        "semantic_labels": 0,
        "selected_thresholds": None,
        "note": "Exposed development data only. Feature values are not answer coverage or risk.",
        "sha256": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(args.output_dir.glob("*.jsonl"))
        },
        "implementation_sha256": {
            str(p.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [Path(__file__).resolve(), ROOT / "backend/app/rag/gating.py"]
        },
    }
    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"Prepared {len(rows)} dev feature records; zero generation calls.")


if __name__ == "__main__":
    main()
