"""Run isolated BM25 and Dense retrieval on the frozen evaluation set."""

import argparse
import hashlib
import json
import platform
import sys
import tempfile
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.corpus import load_canonical_document  # noqa: E402
from app.evaluation.dataset import load_qa_jsonl, validate_qa_dataset  # noqa: E402
from app.evaluation.retrieval import BM25Retriever, retrieval_metrics  # noqa: E402
from app.rag.chunker import chunk_canonical_document  # noqa: E402
from app.rag.retriever import ChromaRetriever  # noqa: E402

DEFAULT_TOP_KS = (1, 3, 5)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="pilot-5-v0")
    parser.add_argument("--chunk-size", type=int, default=800)
    parser.add_argument(
        "--qa",
        type=Path,
        default=PROJECT_ROOT / "data" / "eval" / "qa.jsonl",
    )
    parser.add_argument(
        "--corpus-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "corpus",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=PROJECT_ROOT / "results" / "runs",
    )
    args = parser.parse_args()

    issues = validate_qa_dataset(args.qa, args.corpus_dir)
    errors = [issue for issue in issues if issue.severity == "error"]
    if errors:
        for issue in errors:
            print(f"ERROR {issue.question_id}: {issue.message}")
        return 1

    output_path = args.results_dir / f"{args.run_id}.jsonl"
    config_path = args.results_dir / f"{args.run_id}.config.json"
    if output_path.exists() or config_path.exists():
        print(f"ERROR run_id already exists: {args.run_id}")
        return 1

    manifest_records = _load_jsonl(args.corpus_dir / "documents.jsonl")
    chunks = []
    for record in manifest_records:
        document = load_canonical_document(
            args.corpus_dir,
            document_id=record["document_id"],
            revision=record["revision"],
        )
        chunks.extend(
            chunk_canonical_document(document, max_chars=args.chunk_size)
        )

    qa_records = load_qa_jsonl(args.qa)
    rows = []
    bm25 = BM25Retriever(chunks)
    rows.extend(_evaluate_method(args.run_id, "bm25", bm25, qa_records))

    # A fresh temporary Chroma store prevents stale chunk IDs from contaminating runs.
    with tempfile.TemporaryDirectory(prefix="techdoc-dense-") as dense_store:
        dense = ChromaRetriever(dense_store)
        try:
            dense.index_chunks(chunks)
            rows.extend(_evaluate_method(args.run_id, "dense", dense, qa_records))
        finally:
            dense.close()

    args.results_dir.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            stream.write("\n")

    config = {
        "run_id": args.run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "qa_file": _portable_path(args.qa),
        "qa_hash": f"sha256:{hashlib.sha256(args.qa.read_bytes()).hexdigest()}",
        "chunk_size": args.chunk_size,
        "top_ks": list(DEFAULT_TOP_KS),
        "methods": {
            "bm25": {"k1": 1.5, "b": 0.75, "tokenizer": "[A-Za-z0-9_]+"},
            "dense": {
                "implementation": "chromadb.DefaultEmbeddingFunction",
                "model": "all-MiniLM-L6-v2",
                "chromadb_version": version("chromadb"),
            },
        },
        "python_version": platform.python_version(),
        "corpus": [
            {
                "document_id": record["document_id"],
                "revision": record["revision"],
                "text_hash": record["text_hash"],
            }
            for record in manifest_records
        ],
        "chunk_count": len(chunks),
        "question_count": len(qa_records),
    }
    config_path.write_text(
        json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    _print_summary(rows)
    print(f"Wrote {output_path}")
    print(f"Wrote {config_path}")
    return 0


def _evaluate_method(
    run_id: str,
    method: str,
    retriever,
    qa_records: list[dict],
) -> list[dict]:
    rows = []
    for record in qa_records:
        retrieved = retriever.query_chunks(record["question"], top_k=max(DEFAULT_TOP_KS))
        rows.append(
            {
                "run_id": run_id,
                "method": method,
                "question_id": record["question_id"],
                "annotation_status": record["annotation_status"],
                "expected_behavior": record["expected_behavior"],
                "reasoning_type": record["reasoning_type"],
                "retrieved": [
                    {
                        key: chunk.get(key)
                        for key in (
                            "chunk_id",
                            "document_id",
                            "revision",
                            "page",
                            "start_char",
                            "end_char",
                            "score",
                            "distance",
                        )
                        if chunk.get(key) is not None
                    }
                    for chunk in retrieved
                ],
                "metrics": retrieval_metrics(record, retrieved, ks=DEFAULT_TOP_KS),
            }
        )
    return rows


def _print_summary(rows: list[dict]) -> None:
    for method in ("bm25", "dense"):
        answer_rows = [
            row
            for row in rows
            if row["method"] == method and row["expected_behavior"] == "answer"
        ]
        confirmed_answer_rows = [
            row for row in answer_rows if row["annotation_status"] == "confirmed"
        ]
        correction_rows = [
            row
            for row in rows
            if row["method"] == method
            and row["expected_behavior"] == "correct_premise"
        ]
        confirmed_correction_rows = [
            row for row in correction_rows if row["annotation_status"] == "confirmed"
        ]
        print(
            f"{method}: answerable macro Evidence Recall@5 "
            f"(all={_mean_recall_at_5(answer_rows):.3f}, n={len(answer_rows)}; "
            f"confirmed-only={_mean_recall_at_5(confirmed_answer_rows):.3f}, "
            f"n={len(confirmed_answer_rows)}); "
            f"false-premise counter-evidence Recall@5 "
            f"(all={_format_optional_recall(correction_rows)}, n={len(correction_rows)}; "
            f"confirmed-only={_format_optional_recall(confirmed_correction_rows)}, "
            f"n={len(confirmed_correction_rows)})"
        )


def _mean_recall_at_5(rows: list[dict]) -> float:
    values = [row["metrics"]["evidence_recall_at_5"] for row in rows]
    return sum(values) / len(values) if values else float("nan")


def _format_optional_recall(rows: list[dict]) -> str:
    if not rows:
        return "n/a"
    return f"{_mean_recall_at_5(rows):.3f}"


def _load_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _portable_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
