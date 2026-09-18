"""Read-only sensitivity audit of saved retrieval intervals; prints JSON.

Full coverage refers to the selected gold characters, not semantic sufficiency.
No model calls, annotation changes, or modifications to saved runs are made.
"""

import argparse
import hashlib
import json
from pathlib import Path
from statistics import mean


def covered_length(start, end, intervals):
    """Length of the union clipped to a gold interval; overlap counts once."""
    cursor = start
    total = 0
    for left, right in sorted(intervals):
        left, right = max(start, left, cursor), min(end, right)
        if right > left:
            total += right - left
            cursor = right
    return total


def read_rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--qa", type=Path, default=Path("data/eval/qa.jsonl"))
    args = parser.parse_args()
    config = json.loads(args.run.with_suffix(".config.json").read_text(encoding="utf-8"))
    qa_hash = "sha256:" + hashlib.sha256(args.qa.read_bytes()).hexdigest()
    if config["qa_hash"] != qa_hash:
        raise ValueError("QA hash differs from the saved run")
    qa_rows = read_rows(args.qa)
    qa = {row["question_id"]: row for row in qa_rows}
    if len(qa) != len(qa_rows):
        raise ValueError("Duplicate question IDs")
    rows = read_rows(args.run)
    observations, affected = [], []
    seen = set()
    for row in rows:
        key = row["method"], row["question_id"]
        if key in seen:
            raise ValueError("Duplicate method/question row")
        seen.add(key)
        gold = qa[row["question_id"]]
        if not gold["evidence"]:
            continue
        for k in config["top_ks"]:
            fractions = []
            details = []
            for evidence in gold["evidence"]:
                start, end = evidence["start_char"], evidence["end_char"]
                intervals = [(c["start_char"], c["end_char"]) for c in row["retrieved"][:k]
                             if (c["document_id"], c["revision"]) ==
                             (evidence["document_id"], evidence["revision"])]
                covered = covered_length(start, end, intervals)
                fractions.append(covered / (end - start))
                if 0 < covered < end - start:
                    missing = [offset for offset in range(start, end)
                               if not any(left <= offset < right for left, right in intervals)]
                    details.append({"evidence_id": evidence["evidence_id"],
                                    "covered": covered, "length": end - start,
                                    "missing_text": "".join(evidence["quote"][offset - start]
                                                            for offset in missing),
                                    "missing_nonwhitespace": sum(
                                        not evidence["quote"][offset - start].isspace()
                                        for offset in missing)})
            any_recall = mean(f > 0 for f in fractions)
            any_complete = all(f > 0 for f in fractions)
            if abs(any_recall - row["metrics"][f"evidence_recall_at_{k}"]) > 1e-8:
                raise ValueError("Saved recall disagrees with interval audit")
            if any_complete != row["metrics"][f"complete_evidence_hit_at_{k}"]:
                raise ValueError("Saved complete-hit disagrees with interval audit")
            observation = {"method": row["method"], "question_id": row["question_id"],
                           "status": gold["annotation_status"], "class": gold["expected_behavior"],
                           "k": k, "any_recall": any_recall, "any_complete": float(any_complete),
                           "full_recall": mean(f == 1 for f in fractions),
                           "full_complete": float(all(f == 1 for f in fractions)),
                           "mean_gold_fraction": mean(fractions)}
            observations.append(observation)
            if details:
                affected.append({**observation, "partial_spans": details})
    cells = []
    for method in sorted({r["method"] for r in rows}):
        for category in ("answer", "correct_premise"):
            for cohort in ("confirmed_only", "all_annotations"):
                for k in config["top_ks"]:
                    selected = [r for r in observations if r["method"] == method and
                                r["class"] == category and r["k"] == k and
                                (cohort == "all_annotations" or r["status"] == "confirmed")]
                    cells.append({"method": method, "class": category, "cohort": cohort,
                                  "k": k, "n": len(selected), **{
                                      metric: (round(mean(r[metric] for r in selected), 6)
                                               if selected else None)
                                      for metric in ("any_recall", "full_recall", "any_complete",
                                                     "full_complete", "mean_gold_fraction")}})
    print(json.dumps({"run_id": config["run_id"], "qa_hash": qa_hash,
                      "run_hash": hashlib.sha256(args.run.read_bytes()).hexdigest(),
                      "cells": cells, "partial_cases": affected}, indent=2))


if __name__ == "__main__":
    main()
