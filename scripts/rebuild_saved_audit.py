"""Rebuild saved-run audits without model calls or rewriting historical artifacts.

Run: python scripts/rebuild_saved_audit.py --output-dir <new directory>
"""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
from app.evaluation.behavior import refusal_behavior_metrics  # noqa: E402
from app.evaluation.generation import build_generation_summary, join_retrieval_metrics  # noqa: E402
from app.evaluation.integrity import verify_auxiliary_inputs, verify_frozen_qa  # noqa: E402
from app.evaluation.summary import build_run_summary  # noqa: E402


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def identity(path):
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def run_json(script, *args):
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script), *args],
        cwd=ROOT,
        capture_output=True,
        encoding="utf-8",
        check=True,
    )
    return json.loads(result.stdout)


def compare_summary_cells(old, current):
    if old is None or current is None:
        return {"comparable": False}

    def cell_key(cell):
        return tuple(cell[k] for k in ("method", "question_class", "cohort", "stratum"))

    def without_kind(cell):
        return {k: v for k, v in cell.items() if k != "stratum_kind"}

    lookup = {cell_key(c): without_kind(c) for c in current["cells"]}
    matching = sum(lookup.get(cell_key(c)) == without_kind(c) for c in old["cells"])
    return {
        "comparable": True,
        "matching": matching,
        "n": len(old["cells"]),
        "current_cell_count": len(current["cells"]),
        "note": "Compare historical cell metrics/counts by key; stratum_kind is later metadata. "
        "Current code also emits lexical cells absent from early schemas.",
    }


def build_audit():
    verify_auxiliary_inputs()
    qa = ROOT / "data/eval/qa.jsonl"
    checks = {"qa_identity": verify_frozen_qa(qa), "runs": []}
    for path in sorted((ROOT / "results/runs").glob("*.jsonl")):
        saved = path.with_suffix(".summary.json")
        data = rows(path)
        compatible = all("annotation_status" in row for row in data)
        current = build_run_summary(data, run_id=path.stem) if compatible else None
        old = json.loads(saved.read_text(encoding="utf-8")) if saved.exists() else None
        comparison = compare_summary_cells(old, current)
        checks["runs"].append(
            {
                **identity(path),
                "row_count": len(data),
                "historical_cells": comparison,
                "saved_summary": identity(saved) if saved.exists() else None,
                "summary_recomputed_equal": current == old if old and compatible else None,
                "current_schema_compatible": compatible,
                "explanation": "Current aggregation compared to historical schema; no rows changed."
                if compatible
                else "Legacy rows lack annotation_status; no cohort labels are invented."
                if old
                else "No historical summary was committed.",
            }
        )
    generation = ROOT / "results/generation/frozen-30-bm25-deepseek-v1.jsonl"
    retrieval = ROOT / "results/runs/frozen-30-v1.jsonl"
    config = json.loads(generation.with_suffix(".config.json").read_text(encoding="utf-8"))
    verify_frozen_qa(qa, config["qa_hash"])
    gen = rows(generation)
    joined = join_retrieval_metrics(gen, rows(retrieval))
    summary = build_generation_summary(joined, run_id=generation.stem)
    old = json.loads(generation.with_suffix(".summary.json").read_text(encoding="utf-8"))
    metric_equal = all(
        r["metrics"] == refusal_behavior_metrics(r["expected_behavior"], r["response"]) for r in gen
    )
    if not metric_equal or old["cells"] != summary["cells"]:
        raise ValueError("Historical generation scores changed")
    checks["runs"].append(
        {
            **identity(generation),
            "row_count": len(gen),
            "retrieval_input": identity(retrieval),
            "behavior_rows_recomputed_equal": metric_equal,
            "main_cells_equal": old["cells"] == summary["cells"],
            "summary_recomputed_equal": old == summary,
            "explanation": (
                "Schema 1 to 2: join exact retrieval inputs, add conditioning and metric-scope metadata. "
                "Original prefix-contract metrics retained."
            ),
        }
    )
    combined = ROOT / "results/runs/frozen-30-hybrid-rrf-v1.jsonl"
    saved_rows = rows(combined)
    sensitivity = []
    for excluded in ([], ["q017"], ["q016", "q017"]):
        for method in sorted({r["method"] for r in saved_rows}):
            selected = [
                r
                for r in saved_rows
                if r["method"] == method
                and r["expected_behavior"] == "answer"
                and r["annotation_status"] == "confirmed"
                and r.get("lexical_stratum") == "low"
                and r["question_id"] not in excluded
            ]
            sensitivity.append(
                {
                    "method": method,
                    "excluded": excluded,
                    "question_ids": [r["question_id"] for r in selected],
                    "n": len(selected),
                    **{
                        m: mean(r["metrics"][m] for r in selected)
                        for m in ("evidence_recall_at_5", "complete_evidence_hit_at_5")
                    },
                }
            )
    previous = ROOT / "results/audits/2026-09-23/audit-2026-09-23.jsonl"

    def strip(data):
        return [{k: v for k, v in row.items() if k != "run_id"} for row in data]

    comparison = {
        "historical": identity(combined),
        "saved_reproduction": identity(previous),
        "row_count": len(saved_rows),
        "exact_equal_excluding_run_id": strip(saved_rows) == strip(rows(previous)),
        "scope": "Recompare saved reproduction; this command does not rerun dense retrieval.",
    }
    page_issues = [
        {
            "question_id": r["question_id"],
            "invalid_page_chunks": sum(
                not isinstance(c.get("page"), int) or c["page"] <= 0 for c in r["retrieved"]
            ),
        }
        for r in gen
    ]
    return {
        "saved-artifact-checks.json": checks,
        "generation-recomputed-summary.json": summary,
        "low-overlap-sensitivity.json": {
            "input": identity(combined),
            "cells": sensitivity,
            "scope": "Post-hoc sensitivity; original full-sample results retained.",
        },
        "reproduction-comparison.json": comparison,
        "historical-generation-limitations.json": {
            "input": identity(generation),
            "metric_scope": "refusal-prefix contract only",
            "false_positive_ids": [r["question_id"] for r in gen if r["metrics"]["refusal_false_positive"]],
            "correct_premise_prefix_refusal_ids": [
                r["question_id"]
                for r in gen
                if r["expected_behavior"] == "correct_premise" and r["metrics"]["predicted_refusal"]
            ],
            "page_issue_rows": [r for r in page_issues if r["invalid_page_chunks"]],
            "page_provenance": (
                "Reconstructed from saved retrieval inputs and historical formatter; "
                "raw prompts were not saved."
            ),
            "semantic_rescoring": "Not performed; no keyword heuristic relabeling.",
        },
        "reannotation-mechanical-comparison.json": run_json(
            "check_locked_reannotation.py",
            "--packet",
            "data/eval/reannotation-20260923/input",
            "--output-dir",
            "data/eval/reannotation-20260923",
        ),
        "embedding-truncation.json": run_json("audit_embedding_truncation.py"),
        "evidence-coverage.json": run_json("audit_evidence_coverage.py", "--run", str(combined)),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise ValueError("Use a new output directory; historical audits are immutable")
    outputs = build_audit()
    args.output_dir.mkdir(parents=True)
    for name, content in outputs.items():
        (args.output_dir / name).write_text(
            json.dumps(content, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    manifest = {
        "scope": "Post-hoc integrity manifest, not external attestation. Does not hash itself.",
        "generator": identity(Path(__file__).resolve()),
        "outputs": {n: hashlib.sha256((args.output_dir / n).read_bytes()).hexdigest() for n in outputs},
    }
    (args.output_dir / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"Wrote {len(outputs)} audit artifacts and manifest to {args.output_dir}")


if __name__ == "__main__":
    main()
