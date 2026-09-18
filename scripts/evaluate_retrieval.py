"""Run isolated BM25, Dense, and Hybrid-RRF retrieval on the frozen evaluation set."""

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

from app.corpus import (  # noqa: E402
    ACTIVE_REVISIONS_FILENAME,
    load_active_revision_records,
    load_canonical_document,
)
from app.evaluation.dataset import load_qa_jsonl, validate_qa_dataset  # noqa: E402
from app.evaluation.retrieval import (  # noqa: E402
    BM25Retriever,
    ReciprocalRankFusionRetriever,
    retrieval_metrics,
)
from app.evaluation.summary import build_run_summary  # noqa: E402
from app.rag.chunker import chunk_canonical_document  # noqa: E402
from app.rag.retriever import ChromaRetriever  # noqa: E402

DEFAULT_TOP_KS = (1, 3, 5)
RRF_RANK_CONSTANT = 60
RRF_CANDIDATE_DEPTH = 20


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
    summary_path = args.results_dir / f"{args.run_id}.summary.json"
    if output_path.exists() or config_path.exists() or summary_path.exists():
        print(f"ERROR run_id already exists: {args.run_id}")
        return 1

    manifest_records = load_active_revision_records(args.corpus_dir)
    qa_records = load_qa_jsonl(args.qa)
    revision_mismatches = _active_revision_mismatches(qa_records, manifest_records)
    if revision_mismatches:
        for mismatch in revision_mismatches:
            print(f"ERROR {mismatch}")
        return 1

    args.results_dir.mkdir(parents=True, exist_ok=True)

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

    rows = []
    bm25 = BM25Retriever(chunks)
    rows.extend(_evaluate_method(args.run_id, "bm25", bm25, qa_records))

    # A fresh temporary Chroma store prevents stale chunk IDs from contaminating runs.
    with tempfile.TemporaryDirectory(
        prefix=".techdoc-dense-",
        dir=args.results_dir,
    ) as dense_store:
        dense = ChromaRetriever(dense_store)
        try:
            dense_settings = dense.describe()
            dense.index_chunks(chunks)
            rows.extend(_evaluate_method(args.run_id, "dense", dense, qa_records))
            hybrid = ReciprocalRankFusionRetriever(
                {"bm25": bm25, "dense": dense},
                rank_constant=RRF_RANK_CONSTANT,
                candidate_depth=RRF_CANDIDATE_DEPTH,
            )
            rows.extend(_evaluate_method(args.run_id, "hybrid_rrf", hybrid, qa_records))
        finally:
            dense.close()

    with output_path.open("w", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(
                json.dumps(
                    row,
                    ensure_ascii=False,
                    sort_keys=True,
                    allow_nan=False,
                )
            )
            stream.write("\n")

    config = {
        "run_id": args.run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "qa_file": _portable_path(args.qa),
        "qa_hash": f"sha256:{hashlib.sha256(args.qa.read_bytes()).hexdigest()}",
        "active_revisions_file": _portable_path(
            args.corpus_dir / ACTIVE_REVISIONS_FILENAME
        ),
        "active_revisions_hash": (
            "sha256:"
            + hashlib.sha256(
                (args.corpus_dir / ACTIVE_REVISIONS_FILENAME).read_bytes()
            ).hexdigest()
        ),
        "chunk_size": args.chunk_size,
        "top_ks": list(DEFAULT_TOP_KS),
        "methods": {
            "bm25": {"k1": 1.5, "b": 0.75, "tokenizer": "[A-Za-z0-9_]+"},
            # Read from the live collection and embedder, never typed in;
            # see ChromaRetriever.describe() for what each field guards.
            "dense": {**dense_settings, "chromadb_version": version("chromadb")},
            "hybrid_rrf": {
                "implementation": "reciprocal_rank_fusion",
                "components": ["bm25", "dense"],
                "weights": "equal",
                "rank_constant": RRF_RANK_CONSTANT,
                "candidate_depth_per_component": RRF_CANDIDATE_DEPTH,
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
        json.dumps(
            config,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )

    summary = build_run_summary(rows, run_id=args.run_id)
    summary_path.write_text(
        json.dumps(
            summary,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )

    _print_summary(summary)
    print(f"Wrote {output_path}")
    print(f"Wrote {config_path}")
    print(f"Wrote {summary_path}")
    return 0


def _active_revision_mismatches(
    qa_records: list[dict], active_records: list[dict]
) -> list[str]:
    """Find gold or audit spans that do not belong to the active corpus."""
    active_by_document = {
        record["document_id"]: record["revision"] for record in active_records
    }
    mismatches = []
    for record in qa_records:
        references = list(record.get("evidence", []))
        audit = record.get("unanswerable_search")
        if isinstance(audit, dict):
            references.extend(audit.get("candidate_checks", []))
        for reference in references:
            document_id = reference["document_id"]
            revision = reference["revision"]
            active_revision = active_by_document.get(document_id)
            if revision != active_revision:
                mismatches.append(
                    f"{record['question_id']}: {document_id}@{revision} is not active "
                    f"(selected revision: {active_revision})"
                )
    return sorted(set(mismatches))


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
                "lexical_stratum": (record.get("lexical_overlap") or {}).get("stratum"),
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
                            "rrf_score",
                            "component_ranks",
                        )
                        if chunk.get(key) is not None
                    }
                    for chunk in retrieved
                ],
                "metrics": retrieval_metrics(record, retrieved, ks=DEFAULT_TOP_KS),
            }
        )
    return rows


def _print_summary(summary: dict) -> None:
    methods = sorted({cell["method"] for cell in summary["cells"]})
    for method in methods:
        answer_all = _summary_cell(summary, method, "answerable", "all_annotations")
        answer_confirmed = _summary_cell(
            summary,
            method,
            "answerable",
            "confirmed_only",
        )
        correction_all = _summary_cell(
            summary,
            method,
            "counter_evidence",
            "all_annotations",
        )
        correction_confirmed = _summary_cell(
            summary,
            method,
            "counter_evidence",
            "confirmed_only",
        )
        print(
            f"{method}: answerable macro Evidence Recall@5 "
            f"(all={_format_summary_metric(answer_all)}, n={answer_all['n']}; "
            f"confirmed-only={_format_summary_metric(answer_confirmed)}, "
            f"n={answer_confirmed['n']}); "
            f"false-premise counter-evidence Recall@5 "
            f"(all={_format_summary_metric(correction_all)}, n={correction_all['n']}; "
            f"confirmed-only={_format_summary_metric(correction_confirmed)}, "
            f"n={correction_confirmed['n']})"
        )


def _summary_cell(
    summary: dict,
    method: str,
    question_class: str,
    cohort: str,
) -> dict:
    return next(
        cell
        for cell in summary["cells"]
        if cell["method"] == method
        and cell["question_class"] == question_class
        and cell["cohort"] == cohort
        and cell["stratum_kind"] == "overall"
    )


def _format_summary_metric(cell: dict) -> str:
    if cell["metrics"] is None:
        return "n/a"
    return f"{cell['metrics']['evidence_recall_at_5']:.3f}"


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
