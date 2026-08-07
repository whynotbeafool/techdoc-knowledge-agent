"""Validate QA annotations against the temporary 30-question annotation plan."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .dataset import (
    ValidationIssue,
    lexical_overlap_score,
    lexical_overlap_stratum,
    load_qa_jsonl,
)

PLAN_QUESTION_ID = "<plan>"
VALID_BEHAVIORS = {"answer", "refuse", "correct_premise"}
VALID_REASONING_TYPES = {
    "single_evidence",
    "multi_evidence",
    "multi_hop",
    "not_applicable",
}
VALID_STRATA = {"low", "medium", "high", None}


@dataclass(frozen=True)
class ProgressCount:
    label: str
    completed: int
    target: int


@dataclass(frozen=True)
class AnnotationPlanProgress:
    completed: int
    target: int
    categories: tuple[ProgressCount, ...]
    strata: tuple[ProgressCount, ...]
    next_pending: str | None


@dataclass(frozen=True)
class AnnotationPlanReport:
    issues: tuple[ValidationIssue, ...]
    progress: AnnotationPlanProgress


def load_annotation_plan(path: Path) -> dict:
    """Load one annotation-plan JSON object."""
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON at {path}") from exc
    if not isinstance(plan, dict):
        raise ValueError(f"Expected a JSON object at {path}")
    return plan


def check_annotation_plan_files(qa_path: Path, plan_path: Path) -> AnnotationPlanReport:
    """Load QA and plan files, then run the pure plan-conformance checks."""
    return validate_annotation_plan(
        load_annotation_plan(plan_path),
        load_qa_jsonl(qa_path),
    )


def validate_annotation_plan(plan: dict, records: list[dict]) -> AnnotationPlanReport:
    """Check plan self-consistency, record conformance, progress, and final invariants."""
    issues, slots, slot_order, preexisting_ids = _validate_plan_definition(plan)
    record_by_id = _index_records(records)
    known_ids = set(slots) | preexisting_ids

    for question_id in record_by_id:
        if question_id not in known_ids:
            issues.append(
                ValidationIssue(
                    "error",
                    question_id,
                    "question_id is not declared by the annotation plan",
                )
            )

    for question_id, slot in slots.items():
        record = record_by_id.get(question_id)
        if record is not None:
            issues.extend(_validate_record_against_slot(record, slot))

    progress = _build_progress(slots, slot_order, set(record_by_id))
    all_expected_ids = set(slots) | preexisting_ids
    if all_expected_ids and all_expected_ids <= set(record_by_id):
        issues.extend(_validate_final_invariants(plan, slots, record_by_id))

    return AnnotationPlanReport(tuple(issues), progress)


def _validate_plan_definition(
    plan: dict,
) -> tuple[list[ValidationIssue], dict[str, dict], list[str], set[str]]:
    issues: list[ValidationIssue] = []
    if plan.get("plan_version") != "1":
        issues.append(ValidationIssue("error", PLAN_QUESTION_ID, "Unsupported plan_version"))

    preexisting = plan.get("preexisting_question_ids")
    if not isinstance(preexisting, list) or not all(isinstance(item, str) for item in preexisting):
        issues.append(
            ValidationIssue(
                "error",
                PLAN_QUESTION_ID,
                "preexisting_question_ids must be an array of strings",
            )
        )
        preexisting_ids: set[str] = set()
    else:
        preexisting_ids = set(preexisting)
        if len(preexisting_ids) != len(preexisting):
            issues.append(
                ValidationIssue(
                    "error", PLAN_QUESTION_ID, "preexisting_question_ids contains duplicates"
                )
            )

    raw_slots = plan.get("slots")
    if not isinstance(raw_slots, list):
        issues.append(ValidationIssue("error", PLAN_QUESTION_ID, "slots must be an array"))
        raw_slots = []

    slots: dict[str, dict] = {}
    slot_order: list[str] = []
    required_slot_fields = {
        "question_id",
        "reasoning_type",
        "expected_behavior",
        "target_stratum",
    }
    for index, slot in enumerate(raw_slots, start=1):
        if not isinstance(slot, dict):
            issues.append(
                ValidationIssue("error", PLAN_QUESTION_ID, f"Slot {index} must be an object")
            )
            continue
        question_id = slot.get("question_id", f"<slot-{index}>")
        missing = sorted(required_slot_fields - slot.keys())
        if missing:
            issues.append(
                ValidationIssue(
                    "error",
                    question_id,
                    f"Plan slot is missing fields: {', '.join(missing)}",
                )
            )
            continue
        if not isinstance(question_id, str):
            issues.append(
                ValidationIssue("error", PLAN_QUESTION_ID, f"Slot {index} has invalid question_id")
            )
            continue
        if question_id in slots:
            issues.append(ValidationIssue("error", question_id, "Duplicate plan question_id"))
            continue
        slots[question_id] = slot
        slot_order.append(question_id)
        if slot["reasoning_type"] not in VALID_REASONING_TYPES:
            issues.append(ValidationIssue("error", question_id, "Invalid plan reasoning_type"))
        if slot["expected_behavior"] not in VALID_BEHAVIORS:
            issues.append(ValidationIssue("error", question_id, "Invalid plan expected_behavior"))
        if slot["target_stratum"] not in VALID_STRATA:
            issues.append(ValidationIssue("error", question_id, "Invalid plan target_stratum"))

    issues.extend(_validate_question_id_range(plan, slots))
    issues.extend(_validate_planned_slot_count(plan, len(slots)))
    if preexisting_ids & set(slots):
        issues.append(
            ValidationIssue(
                "error",
                PLAN_QUESTION_ID,
                "preexisting_question_ids and slots must be disjoint",
            )
        )
    issues.extend(_validate_expected_distribution(plan, slots))
    issues.extend(_validate_final_category_definition(plan, len(preexisting_ids) + len(slots)))
    issues.extend(_validate_corpus_coverage_definition(plan))
    return issues, slots, slot_order, preexisting_ids


def _validate_planned_slot_count(plan: dict, actual_count: int) -> list[ValidationIssue]:
    expected_count = plan.get("planned_slot_count")
    if (
        not isinstance(expected_count, int)
        or isinstance(expected_count, bool)
        or expected_count < 1
    ):
        return [
            ValidationIssue("error", PLAN_QUESTION_ID, "planned_slot_count must be a positive integer")
        ]
    if actual_count != expected_count:
        return [
            ValidationIssue(
                "error",
                PLAN_QUESTION_ID,
                f"Plan must contain {expected_count} slots, got {actual_count}",
            )
        ]
    return []


def _validate_question_id_range(plan: dict, slots: dict[str, dict]) -> list[ValidationIssue]:
    spec = plan.get("question_id_range")
    if not isinstance(spec, dict):
        return [
            ValidationIssue("error", PLAN_QUESTION_ID, "question_id_range must be an object")
        ]
    prefix = spec.get("prefix")
    start = spec.get("start")
    end = spec.get("end")
    if (
        not isinstance(prefix, str)
        or not isinstance(start, int)
        or isinstance(start, bool)
        or not isinstance(end, int)
        or isinstance(end, bool)
        or start > end
    ):
        return [ValidationIssue("error", PLAN_QUESTION_ID, "Invalid question_id_range")]
    expected_ids = {f"{prefix}{number:03d}" for number in range(start, end + 1)}
    actual_ids = set(slots)
    if expected_ids == actual_ids:
        return []
    missing = ", ".join(sorted(expected_ids - actual_ids)) or "none"
    unexpected = ", ".join(sorted(actual_ids - expected_ids)) or "none"
    return [
        ValidationIssue(
            "error",
            PLAN_QUESTION_ID,
            f"Plan question_id range mismatch; missing: {missing}; unexpected: {unexpected}",
        )
    ]


def _validate_expected_distribution(plan: dict, slots: dict[str, dict]) -> list[ValidationIssue]:
    entries = plan.get("expected_distribution")
    if not isinstance(entries, list):
        return [
            ValidationIssue("error", PLAN_QUESTION_ID, "expected_distribution must be an array")
        ]
    expected: Counter[tuple[str, str, str | None]] = Counter()
    for entry in entries:
        if not isinstance(entry, dict):
            return [
                ValidationIssue(
                    "error", PLAN_QUESTION_ID, "expected_distribution entries must be objects"
                )
            ]
        key = (
            entry.get("reasoning_type"),
            entry.get("expected_behavior"),
            entry.get("target_stratum"),
        )
        count = entry.get("count")
        if (
            key[0] not in VALID_REASONING_TYPES
            or key[1] not in VALID_BEHAVIORS
            or key[2] not in VALID_STRATA
            or not isinstance(count, int)
            or isinstance(count, bool)
            or count < 1
            or key in expected
        ):
            return [
                ValidationIssue("error", PLAN_QUESTION_ID, "Invalid expected_distribution")
            ]
        expected[key] = count
    actual = Counter(
        (
            slot["reasoning_type"],
            slot["expected_behavior"],
            slot["target_stratum"],
        )
        for slot in slots.values()
        if {
            "reasoning_type",
            "expected_behavior",
            "target_stratum",
        }
        <= slot.keys()
    )
    if actual == expected:
        return []
    return [
        ValidationIssue(
            "error",
            PLAN_QUESTION_ID,
            "Plan slot distribution does not match expected_distribution",
        )
    ]


def _validate_final_category_definition(plan: dict, expected_total: int) -> list[ValidationIssue]:
    entries = plan.get("final_category_counts")
    if not isinstance(entries, list):
        return [
            ValidationIssue("error", PLAN_QUESTION_ID, "final_category_counts must be an array")
        ]
    total = 0
    seen: set[tuple[str, str | None]] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            return [ValidationIssue("error", PLAN_QUESTION_ID, "Invalid final_category_counts")]
        key = (entry.get("expected_behavior"), entry.get("reasoning_type"))
        count = entry.get("count")
        if (
            key[0] not in VALID_BEHAVIORS
            or (key[1] is not None and key[1] not in VALID_REASONING_TYPES)
            or not isinstance(count, int)
            or isinstance(count, bool)
            or count < 1
            or key in seen
        ):
            return [ValidationIssue("error", PLAN_QUESTION_ID, "Invalid final_category_counts")]
        seen.add(key)
        total += count
    if total != expected_total:
        return [
            ValidationIssue(
                "error",
                PLAN_QUESTION_ID,
                f"Final category count total must be {expected_total}, got {total}",
            )
        ]
    return []


def _validate_corpus_coverage_definition(plan: dict) -> list[ValidationIssue]:
    coverage = plan.get("corpus_coverage")
    if not isinstance(coverage, dict):
        return [ValidationIssue("error", PLAN_QUESTION_ID, "corpus_coverage must be an object")]
    document_ids = coverage.get("document_ids")
    minimum = coverage.get("min_per_document")
    maximum = coverage.get("max_per_document")
    if (
        not isinstance(document_ids, list)
        or not document_ids
        or not all(isinstance(item, str) for item in document_ids)
        or len(set(document_ids)) != len(document_ids)
        or not isinstance(minimum, int)
        or isinstance(minimum, bool)
        or not isinstance(maximum, int)
        or isinstance(maximum, bool)
        or not 0 <= minimum <= maximum
    ):
        return [ValidationIssue("error", PLAN_QUESTION_ID, "Invalid corpus_coverage")]
    return []


def _index_records(records: list[dict]) -> dict[str, dict]:
    indexed: dict[str, dict] = {}
    for record in records:
        question_id = record.get("question_id", "<missing>")
        indexed.setdefault(question_id, record)
    return indexed


def _validate_record_against_slot(record: dict, slot: dict) -> list[ValidationIssue]:
    question_id = slot["question_id"]
    issues = []
    for field in ("reasoning_type", "expected_behavior"):
        if record.get(field) != slot[field]:
            issues.append(
                ValidationIssue(
                    "error",
                    question_id,
                    f"{field} does not match plan: expected {slot[field]}, got {record.get(field)}",
                )
            )
    actual_stratum = _record_stratum(record, question_id, issues)
    if actual_stratum != slot["target_stratum"]:
        issues.append(
            ValidationIssue(
                "error",
                question_id,
                "lexical overlap stratum does not match plan: "
                f"expected {_stratum_label(slot['target_stratum'])}, "
                f"got {_stratum_label(actual_stratum)}",
            )
        )
    return issues


def _record_stratum(
    record: dict,
    question_id: str,
    issues: list[ValidationIssue],
) -> str | None:
    if record.get("expected_behavior") == "refuse":
        return None
    question = record.get("question")
    evidence = record.get("evidence")
    if not isinstance(question, str) or not isinstance(evidence, list):
        issues.append(
            ValidationIssue(
                "error",
                question_id,
                "Cannot recompute lexical overlap without question and evidence",
            )
        )
        return None
    return lexical_overlap_stratum(lexical_overlap_score(question, evidence))


def _build_progress(
    slots: dict[str, dict],
    slot_order: list[str],
    record_ids: set[str],
) -> AnnotationPlanProgress:
    category_targets: Counter[tuple[str, str | None]] = Counter()
    category_completed: Counter[tuple[str, str | None]] = Counter()
    stratum_targets: Counter[str | None] = Counter()
    stratum_completed: Counter[str | None] = Counter()
    for question_id in slot_order:
        slot = slots[question_id]
        category = _category_key(slot["expected_behavior"], slot["reasoning_type"])
        stratum = slot["target_stratum"]
        category_targets[category] += 1
        stratum_targets[stratum] += 1
        if question_id in record_ids:
            category_completed[category] += 1
            stratum_completed[stratum] += 1

    categories = tuple(
        ProgressCount(
            _category_label(category),
            category_completed[category],
            target,
        )
        for category, target in category_targets.items()
    )
    strata = tuple(
        ProgressCount(_stratum_label(stratum), stratum_completed[stratum], target)
        for stratum, target in stratum_targets.items()
    )
    next_pending = next((item for item in slot_order if item not in record_ids), None)
    return AnnotationPlanProgress(
        completed=sum(question_id in record_ids for question_id in slots),
        target=len(slots),
        categories=categories,
        strata=strata,
        next_pending=next_pending,
    )


def _validate_final_invariants(
    plan: dict,
    slots: dict[str, dict],
    record_by_id: dict[str, dict],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    expected_categories = {
        (entry["expected_behavior"], entry.get("reasoning_type")): entry["count"]
        for entry in plan.get("final_category_counts", [])
        if isinstance(entry, dict)
        and "expected_behavior" in entry
        and "count" in entry
    }
    actual_categories = Counter(
        _category_key(record.get("expected_behavior"), record.get("reasoning_type"))
        for question_id, record in record_by_id.items()
        if question_id in set(slots) | set(plan.get("preexisting_question_ids", []))
    )
    if actual_categories != expected_categories:
        issues.append(
            ValidationIssue(
                "error",
                PLAN_QUESTION_ID,
                "Final 30-question category counts do not match the plan",
            )
        )

    expected_strata = Counter(slot["target_stratum"] for slot in slots.values())
    actual_strata: Counter[str | None] = Counter()
    for question_id, slot in slots.items():
        record = record_by_id[question_id]
        actual = None
        if record.get("expected_behavior") != "refuse":
            question = record.get("question")
            evidence = record.get("evidence")
            if isinstance(question, str) and isinstance(evidence, list):
                actual = lexical_overlap_stratum(lexical_overlap_score(question, evidence))
        actual_strata[actual] += 1
    if actual_strata != expected_strata:
        issues.append(
            ValidationIssue(
                "error",
                PLAN_QUESTION_ID,
                "Final planned-question stratum counts do not match the plan",
            )
        )

    issues.extend(_corpus_coverage_warnings(plan, slots, record_by_id))
    return issues


def _corpus_coverage_warnings(
    plan: dict,
    slots: dict[str, dict],
    record_by_id: dict[str, dict],
) -> list[ValidationIssue]:
    coverage = plan.get("corpus_coverage", {})
    document_ids = coverage.get("document_ids", [])
    minimum = coverage.get("min_per_document")
    maximum = coverage.get("max_per_document")
    if not document_ids or not isinstance(minimum, int) or not isinstance(maximum, int):
        return []
    counts: Counter[str] = Counter()
    for question_id, slot in slots.items():
        if slot["expected_behavior"] == "refuse":
            continue
        evidence = record_by_id[question_id].get("evidence", [])
        record_documents = {
            item.get("document_id")
            for item in evidence
            if isinstance(item, dict) and isinstance(item.get("document_id"), str)
        }
        counts.update(record_documents)
    return [
        ValidationIssue(
            "warning",
            PLAN_QUESTION_ID,
            f"Corpus coverage for {document_id} is {counts[document_id]}; expected {minimum}-{maximum}",
        )
        for document_id in document_ids
        if not minimum <= counts[document_id] <= maximum
    ]


def _category_key(behavior: str | None, reasoning_type: str | None) -> tuple[str | None, str | None]:
    return (behavior, reasoning_type if behavior == "answer" else None)


def _category_label(category: tuple[str | None, str | None]) -> str:
    behavior, reasoning_type = category
    return f"{behavior}/{reasoning_type}" if reasoning_type else str(behavior)


def _stratum_label(stratum: str | None) -> str:
    return "N/A" if stratum is None else stratum
