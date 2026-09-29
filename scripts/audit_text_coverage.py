"""Audit saved rankings under coverage-v1, without changing runs or annotations."""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
from app.corpus import load_canonical_document  # noqa: E402
from app.evaluation.coverage import evidence_coverage  # noqa: E402
from app.evaluation.dataset import load_qa_jsonl, validate_qa_dataset  # noqa: E402
from app.evaluation.integrity import verify_frozen_qa  # noqa: E402


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(run, qa_path, corpus):
    config_path = run.with_suffix(".config.json")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    qa_hash = digest(qa_path)
    if config["qa_hash"] != "sha256:" + qa_hash:
        verify_frozen_qa(qa_path, config["qa_hash"])
    errors = [x for x in validate_qa_dataset(qa_path, corpus) if x.severity == "error"]
    if errors:
        raise ValueError(str(errors))
    questions = load_qa_jsonl(qa_path)
    qa = {x["question_id"]: x for x in questions}
    if len(qa) != len(questions):
        raise ValueError("Duplicate QA IDs")
    data = load_qa_jsonl(run)
    seen = set()
    methods = set()
    documents = {}
    observations = []
    top_ks = config["top_ks"]
    if not top_ks or len(set(top_ks)) != len(top_ks) or any(type(k) is not int or k < 1 for k in top_ks):
        raise ValueError("Expected distinct positive integer cutoffs")
    for row in data:
        key = row["method"], row["question_id"]
        if key in seen or row["question_id"] not in qa or row["run_id"] != config["run_id"]:
            raise ValueError("Duplicate/unknown row or wrong run identity")
        seen.add(key)
        methods.add(row["method"])
        question = qa[row["question_id"]]
        if any(row[f] != question[f] for f in ("annotation_status", "expected_behavior")):
            raise ValueError("Saved cohort metadata differs from QA")
        for chunk in row["retrieved"]:
            doc_key = chunk["document_id"], chunk["revision"]
            if doc_key not in documents:
                documents[doc_key] = load_canonical_document(
                    corpus, document_id=doc_key[0], revision=doc_key[1]
                )
            left, right = chunk["start_char"], chunk["end_char"]
            if (
                type(left) is not int
                or type(right) is not int
                or not 0 <= left < right <= len(documents[doc_key].text)
            ):
                raise ValueError("Retrieved coordinates are invalid")
        for k in top_ks:
            score = evidence_coverage(question["evidence"], row["retrieved"][:k])
            if question["evidence"]:
                if (
                    abs(score["recall_any"] - row["metrics"][f"evidence_recall_at_{k}"]) > 1e-8
                    or score["complete_any"] != row["metrics"][f"complete_evidence_hit_at_{k}"]
                ):
                    raise ValueError("Historical any-overlap score mismatch")
            observations.append(
                {
                    "method": row["method"],
                    "question_id": row["question_id"],
                    "expected_behavior": question["expected_behavior"],
                    "annotation_status": question["annotation_status"],
                    "k": k,
                    **score,
                }
            )
    if not methods or seen != {(m, q) for m in methods for q in qa}:
        raise ValueError("Run does not cover every question once per method")
    fields = [
        "recall_any",
        "complete_any",
        "recall_full_char",
        "complete_full_char",
        "recall_full_nonspace",
        "complete_full_nonspace",
        "mean_char_fraction",
        "mean_nonspace_fraction",
    ]
    cells = []
    for method in sorted(methods):
        for behavior in ("answer", "correct_premise"):
            for cohort in ("all_annotations", "confirmed_only"):
                for k in top_ks:
                    selected = [
                        r
                        for r in observations
                        if r["method"] == method
                        and r["expected_behavior"] == behavior
                        and r["k"] == k
                        and (cohort == "all_annotations" or r["annotation_status"] == "confirmed")
                    ]
                    metrics = {}
                    for field in fields:
                        values = [r[field] for r in selected if r[field] is not None]
                        metrics[field] = {
                            "n": len(values),
                            "sum": sum(values),
                            "mean": mean(values) if values else None,
                        }
                    cells.append(
                        {
                            "method": method,
                            "expected_behavior": behavior,
                            "cohort": cohort,
                            "k": k,
                            "question_n": len(selected),
                            "metrics": metrics,
                        }
                    )
    return {
        "schema_version": "coverage-v1",
        "status": "post_hoc_sensitivity",
        "whitespace_policy": "Python str.isspace; no other normalization",
        "python_version": sys.version.split()[0],
        "inputs": {
            "run": {"name": run.name, "sha256": digest(run)},
            "config": {"name": config_path.name, "sha256": digest(config_path)},
            "qa": {"name": qa_path.name, "sha256": qa_hash},
        },
        "implementation": {
            "script_sha256": digest(Path(__file__)),
            "module_sha256": digest(ROOT / "backend/app/evaluation/coverage.py"),
        },
        "scope": "Selected gold locations only; not semantic sufficiency or selective-answer coverage.",
        "cells": cells,
        "rows": observations,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--qa", type=Path, default=ROOT / "data/eval/qa.jsonl")
    parser.add_argument("--corpus", type=Path, default=ROOT / "data/corpus")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Refusing to overwrite an existing audit")
    report = audit(args.run, args.qa, args.corpus)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8", newline="\n") as out:
        json.dump(report, out, ensure_ascii=False, indent=2, allow_nan=False)
        out.write("\n")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
