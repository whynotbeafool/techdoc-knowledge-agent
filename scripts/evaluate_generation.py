"""Generate answers from a frozen retrieval run and score refusal behavior."""

import argparse
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.core.config import get_llm_config  # noqa: E402
from app.core.response_contract import REFUSAL_PREFIX  # noqa: E402
from app.corpus import load_canonical_document  # noqa: E402
from app.evaluation.dataset import load_qa_jsonl, validate_qa_dataset  # noqa: E402
from app.evaluation.generation import (  # noqa: E402
    build_generation_row,
    build_generation_summary,
)
from app.rag.generator import SYSTEM_PROMPT, generate_answer  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--method", default="bm25")
    parser.add_argument(
        "--qa",
        type=Path,
        default=PROJECT_ROOT / "data" / "eval" / "qa.jsonl",
    )
    parser.add_argument(
        "--retrieval-run",
        type=Path,
        default=PROJECT_ROOT / "results" / "runs" / "frozen-30-v1.jsonl",
    )
    parser.add_argument(
        "--corpus-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "corpus",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=PROJECT_ROOT / "results" / "generation",
    )
    args = parser.parse_args()

    output_path = args.results_dir / f"{args.run_id}.jsonl"
    config_path = args.results_dir / f"{args.run_id}.config.json"
    summary_path = args.results_dir / f"{args.run_id}.summary.json"
    if any(path.exists() for path in (output_path, config_path, summary_path)):
        print(f"ERROR run_id already exists: {args.run_id}")
        return 1

    issues = validate_qa_dataset(args.qa, args.corpus_dir)
    errors = [issue for issue in issues if issue.severity == "error"]
    if errors:
        for issue in errors:
            print(f"ERROR {issue.question_id}: {issue.message}")
        return 1

    qa_records = load_qa_jsonl(args.qa)
    retrieval_rows = _load_jsonl(args.retrieval_run)
    try:
        selected_rows = _select_retrieval_rows(
            retrieval_rows,
            qa_records,
            args.method,
        )
        llm_config = get_llm_config()
    except (KeyError, RuntimeError, TypeError, ValueError) as exc:
        print(f"ERROR {exc}")
        return 1

    qa_by_id = {record["question_id"]: record for record in qa_records}
    document_cache = {}
    rows = []
    for retrieval_row in selected_rows:
        question_id = retrieval_row["question_id"]
        qa_record = qa_by_id[question_id]
        try:
            chunks = _rehydrate_chunks(
                retrieval_row["retrieved"],
                corpus_dir=args.corpus_dir,
                document_cache=document_cache,
            )
        except (KeyError, TypeError, ValueError) as exc:
            print(f"ERROR {question_id}: {exc}")
            return 1
        response = generate_answer(qa_record["question"], chunks)
        rows.append(
            build_generation_row(
                run_id=args.run_id,
                qa_record=qa_record,
                retrieval_row=retrieval_row,
                response=response,
            )
        )

    config = {
        "schema_version": "1",
        "run_id": args.run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "qa_file": _portable_path(args.qa),
        "qa_hash": _sha256_file(args.qa),
        "retrieval_run_file": _portable_path(args.retrieval_run),
        "retrieval_run_hash": _sha256_file(args.retrieval_run),
        "retrieval_run_ids": sorted({row["run_id"] for row in selected_rows}),
        "method": args.method,
        "provider": llm_config["provider"],
        "model": llm_config["model"],
        "base_url": llm_config["base_url"],
        "system_prompt_hash": f"sha256:{_sha256_text(SYSTEM_PROMPT)}",
        "refusal_prefix": REFUSAL_PREFIX,
        "python_version": platform.python_version(),
        "question_count": len(rows),
    }
    summary = build_generation_summary(rows, run_id=args.run_id)

    args.results_dir.mkdir(parents=True, exist_ok=True)
    _write_jsonl(output_path, rows)
    _write_json(config_path, config)
    _write_json(summary_path, summary)

    _print_summary(summary)
    print(f"Wrote {output_path}")
    print(f"Wrote {config_path}")
    print(f"Wrote {summary_path}")
    return 0


def _select_retrieval_rows(
    retrieval_rows: list[dict],
    qa_records: list[dict],
    method: str,
) -> list[dict]:
    selected = [row for row in retrieval_rows if row.get("method") == method]
    rows_by_id = {}
    duplicates = []
    for row in selected:
        question_id = row.get("question_id")
        if question_id in rows_by_id:
            duplicates.append(question_id)
        rows_by_id[question_id] = row
    if duplicates:
        raise ValueError(f"duplicate retrieval rows: {sorted(set(duplicates))}")

    expected_ids = {record["question_id"] for record in qa_records}
    actual_ids = set(rows_by_id)
    if expected_ids != actual_ids:
        missing = sorted(expected_ids - actual_ids)
        extra = sorted(actual_ids - expected_ids)
        raise ValueError(
            f"retrieval rows do not match QA dataset; missing={missing}, extra={extra}"
        )
    return [rows_by_id[question_id] for question_id in sorted(expected_ids)]


def _rehydrate_chunks(
    retrieved: list[dict],
    *,
    corpus_dir: Path,
    document_cache: dict,
) -> list[dict]:
    chunks = []
    for rank, item in enumerate(retrieved, start=1):
        try:
            document_id = item["document_id"]
            revision = item["revision"]
            start_char = item["start_char"]
            end_char = item["end_char"]
            chunk_id = item["chunk_id"]
        except KeyError as exc:
            raise ValueError(f"retrieved rank {rank} is missing {exc.args[0]}") from exc
        if (
            not isinstance(start_char, int)
            or isinstance(start_char, bool)
            or not isinstance(end_char, int)
            or isinstance(end_char, bool)
        ):
            raise TypeError(f"retrieved rank {rank} has non-integer offsets")

        key = (document_id, revision)
        if key not in document_cache:
            document_cache[key] = load_canonical_document(
                corpus_dir,
                document_id=document_id,
                revision=revision,
            )
        document = document_cache[key]
        if start_char < 0 or start_char >= end_char or end_char > len(document.text):
            raise ValueError(f"retrieved rank {rank} has invalid canonical offsets")

        chunks.append(
            {
                "chunk_id": chunk_id,
                "source": document.metadata["source_file"],
                "page": item.get("page"),
                "text": document.text[start_char:end_char],
                "document_id": document_id,
                "revision": revision,
                "start_char": start_char,
                "end_char": end_char,
            }
        )
    return chunks


def _load_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    text = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n"
        for row in rows
    )
    path.write_text(text, encoding="utf-8", newline="\n")


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _print_summary(summary: dict) -> None:
    for cell in summary["cells"]:
        metrics = cell["metrics"]
        print(
            f"{cell['method']} {cell['cohort']}: "
            f"refusal_accuracy={_format_metric(metrics['refusal_accuracy'])}, "
            f"refusal_recall={_format_metric(metrics['refusal_recall'])}, "
            f"system_errors={cell['system_error_n']}/{cell['n']}"
        )


def _format_metric(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def _sha256_file(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _portable_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
