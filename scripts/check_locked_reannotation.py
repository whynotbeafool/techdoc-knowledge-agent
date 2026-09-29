"""Validate an already locked second pass and emit mechanical comparisons.

This is a post-lock reviewer tool. Never expose its output to a blind annotator
before their complete second pass is locked. Answer and evidence sufficiency
still require a separate semantic review; geometric overlap is not that review.
"""

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.corpus import load_active_revision_records  # noqa: E402
from app.evaluation.dataset import load_qa_jsonl, validate_qa_dataset  # noqa: E402
from app.evaluation.integrity import verify_auxiliary_inputs, verify_frozen_qa  # noqa: E402


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def overlap(left, right):
    return (left["document_id"], left["revision"]) == (right["document_id"], right["revision"]) and max(
        left["start_char"], right["start_char"]
    ) < min(left["end_char"], right["end_char"])


def agreement(left, right):
    n = len(left)
    matches = sum(a == b for a, b in zip(left, right))
    lc, rc = Counter(left), Counter(right)
    expected = sum(lc[k] * rc[k] for k in lc.keys() | rc.keys()) / n**2
    observed = matches / n
    return {
        "matches": matches,
        "n": n,
        "raw_agreement": observed,
        "cohen_kappa": (observed - expected) / (1 - expected) if expected < 1 else None,
    }


def validate_planned_ids(ids, plan_path):
    """Compare to the predeclared table, not merely a 14-of-30 cardinality."""
    planned = re.findall(r"^\| (q\d{3}) \|", plan_path.read_text(encoding="utf-8"), re.MULTILINE)
    if len(planned) != 14 or len(set(planned)) != 14:
        raise ValueError("Invalid predeclared reannotation subset")
    if len(ids) != 14 or set(ids) != set(planned):
        raise ValueError("Question IDs differ from predeclared reannotation subset")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", required=True, type=Path)
    parser.add_argument("--output-dir", type=Path, help="Defaults to PACKET/output")
    args = parser.parse_args()
    packet = args.packet.resolve()
    out = args.output_dir.resolve() if args.output_dir else packet / "output"
    lock = json.loads((out / "LOCK.json").read_text(encoding="utf-8"))
    if lock["status"] != "locked" or lock["prohibited_information_exposed"] is not False:
        raise ValueError("Require a locked batch with no declared prohibited exposure")
    artifacts = {}
    for name in ("annotations.jsonl", "dimensions.jsonl", "hesitations.md"):
        artifacts[name] = digest(out / name)
        if artifacts[name] != lock["artifacts"][name]["sha256"]:
            raise ValueError(f"Current {name} hash differs from LOCK.json")
    manifest_path = packet / "INPUT_MANIFEST.json"
    if digest(manifest_path) != lock["input_manifest_sha256"]:
        raise ValueError("Input manifest hash differs from LOCK.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for name, expected in manifest["files"].items():
        target = (packet / name).resolve()
        if not target.is_relative_to(packet) or digest(target) != expected:
            raise ValueError(f"Input path/hash mismatch: {name}")
    questions = load_qa_jsonl(packet / "questions.jsonl")
    second = load_qa_jsonl(out / "annotations.jsonl")
    dimensions = load_qa_jsonl(out / "dimensions.jsonl")
    ids = [r["question_id"] for r in questions]
    validate_planned_ids(ids, ROOT / "data/eval/reannotation-plan.md")
    if len(ids) != 14 or len(set(ids)) != 14:
        raise ValueError("Expected 14 unique input questions")
    for name, records in (("annotations", second), ("dimensions", dimensions)):
        if len(records) != 14 or {r["question_id"] for r in records} != set(ids):
            raise ValueError(f"Incomplete/duplicate {name}")
    question_by_id = {q["question_id"]: q["question"] for q in questions}
    if any(r["question"] != question_by_id[r["question_id"]] for r in dimensions):
        raise ValueError("Dimensions changed a frozen question")
    main_records = load_active_revision_records(ROOT / "data/corpus")
    packet_records = load_qa_jsonl(packet / "corpus/documents.jsonl")

    def key(r):
        return r["document_id"], r["revision"]

    if sorted(main_records, key=key) != sorted(packet_records, key=key):
        raise ValueError("Packet corpus differs from main active revisions")
    if json.loads((packet / "corpus/active-revisions.json").read_text(encoding="utf-8")) != json.loads(
        (ROOT / "data/corpus/active-revisions.json").read_text(encoding="utf-8")
    ):
        raise ValueError("Active revisions differ")
    for record in packet_records:
        name = record["canonical_text_file"]
        if (packet / "corpus" / name).read_bytes() != (ROOT / "data/corpus" / name).read_bytes():
            raise ValueError(f"Canonical bytes differ: {name}")
    review_manifest = json.loads(
        (ROOT / "data/eval/reannotation-review-manifest.json").read_text(encoding="utf-8")
    )
    for name, expected in review_manifest["files"].items():
        target = (ROOT / name).resolve()
        if not target.is_relative_to(ROOT) or digest(target) != expected:
            raise ValueError(f"Post-lock review hash mismatch: {name}")
    receipt = json.loads((out / "intake-receipt.json").read_text(encoding="utf-8"))
    combined = ROOT / "data/eval/reannotation.jsonl"
    previous_n = receipt["previous_record_count"]
    combined_rows = load_qa_jsonl(combined)
    if (
        receipt["appended_record_count"] != len(second)
        or combined_rows[previous_n:] != second
        or len(combined_rows) != previous_n + len(second)
    ):
        raise ValueError("Cumulative reannotation differs from locked batch")
    previous_bytes = b"".join(combined.read_bytes().splitlines(keepends=True)[:previous_n])
    if hashlib.sha256(previous_bytes).hexdigest() != receipt["previous_reannotation_sha256"]:
        raise ValueError("Historical reannotation prefix changed")
    receipt_checks = {
        "combined_reannotation_sha256": digest(combined),
        "appended_annotations_sha256": digest(out / "annotations.jsonl"),
        "lock_sha256": digest(out / "LOCK.json"),
        "input_manifest_sha256": digest(manifest_path),
    }
    if any(receipt[k] != value for k, value in receipt_checks.items()):
        raise ValueError("Intake receipt disagrees with artifacts")
    review = json.loads((out / "semantic-review.json").read_text(encoding="utf-8"))
    if len(review["rows"]) != 14 or {r["question_id"] for r in review["rows"]} != set(ids):
        raise ValueError("Incomplete semantic review")
    by_id = {r["question_id"]: r for r in second}
    if any(by_id[q["question_id"]]["question"] != q["question"] for q in questions):
        raise ValueError("Second pass changed a frozen question")
    issues = validate_qa_dataset(out / "annotations.jsonl", ROOT / "data/corpus")
    if any(i.severity == "error" for i in issues):
        raise ValueError(str(issues))
    # First-pass labels are opened only after lock and independent input checks.
    first_path = ROOT / "data/eval/qa.jsonl"
    first_identity = verify_frozen_qa(first_path, receipt["first_pass_sha256"])
    verify_auxiliary_inputs()
    first = {r["question_id"]: r for r in load_qa_jsonl(first_path)}
    if any(first[q["question_id"]]["question"] != q["question"] for q in questions):
        raise ValueError("Input packet differs from frozen first-pass questions")
    comparison = []
    for qid in ids:
        a, b = first[qid], by_id[qid]
        ea, eb = a["evidence"], b["evidence"]
        comparison.append(
            {
                "question_id": qid,
                "support_equal": (a["answerability"], a["unanswerable_reason"])
                == (b["answerability"], b["unanswerable_reason"]),
                "topology_equal": a["reasoning_type"] == b["reasoning_type"],
                "first_topology": a["reasoning_type"],
                "second_topology": b["reasoning_type"],
                "first_answer": a["reference_answer"],
                "second_answer": b["reference_answer"],
                "first_status": a["annotation_status"],
                "second_status": b["annotation_status"],
                "first_lexical": a.get("lexical_overlap"),
                "second_lexical": b.get("lexical_overlap"),
                "each_first_span_overlaps_second": all(any(overlap(x, y) for y in eb) for x in ea)
                if ea and eb
                else None,
                "each_second_span_overlaps_first": all(any(overlap(x, y) for x in ea) for y in eb)
                if ea and eb
                else None,
            }
        )

    def support(record):
        return record["answerability"], record["unanswerable_reason"]

    report = {
        "lock_sha256": digest(out / "LOCK.json"),
        "artifact_sha256": artifacts,
        "warning_messages": [i.message for i in issues if i.severity == "warning"],
        "support": agreement([support(first[i]) for i in ids], [support(by_id[i]) for i in ids]),
        "topology": agreement(
            [first[i]["reasoning_type"] for i in ids], [by_id[i]["reasoning_type"] for i in ids]
        ),
        "first_pass_identity": first_identity,
        "topology_evidence_bearing": agreement(
            [first[i]["reasoning_type"] for i in ids if by_id[i]["evidence"]],
            [by_id[i]["reasoning_type"] for i in ids if by_id[i]["evidence"]],
        ),
        "annotation_status": agreement(
            [first[i]["annotation_status"] for i in ids], [by_id[i]["annotation_status"] for i in ids]
        ),
        "second_A_counts": dict(Counter(r["A"]["judgment"] for r in dimensions)),
        "exact_reference_answers": {
            "matches": sum(first[i]["reference_answer"] == by_id[i]["reference_answer"] for i in ids),
            "n": len(ids),
            "note": "All exact matches are null refusal answers; not a semantic score.",
        },
        "rows": comparison,
        "limitations": [
            "Lock exposure/identity declarations require reviewer inspection.",
            "A has no explicit first-pass quality judgments: no retrospective agreement rate.",
            "D semantic coverage and E semantic sufficiency are not automatically scored.",
            "Span overlap is geometric only; refusal candidate locations are not gold evidence.",
        ],
    }
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
