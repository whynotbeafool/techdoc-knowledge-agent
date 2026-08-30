"""Pure row construction and aggregation for generation behavior runs."""

from app.evaluation.behavior import refusal_behavior_metrics

COHORTS = ("all_annotations", "confirmed_only")


def build_generation_row(
    *,
    run_id: str,
    qa_record: dict,
    retrieval_row: dict,
    response: str,
) -> dict:
    """Combine one frozen QA item, retrieval result, and generated response."""
    question_id = qa_record["question_id"]
    if retrieval_row.get("question_id") != question_id:
        raise ValueError(
            "question_id mismatch: "
            f"qa={question_id}, retrieval={retrieval_row.get('question_id')}"
        )
    if not isinstance(retrieval_row.get("retrieved"), list):
        raise ValueError(f"retrieval row for {question_id} has no retrieved list")

    return {
        "run_id": run_id,
        "retrieval_run_id": retrieval_row["run_id"],
        "method": retrieval_row["method"],
        "question_id": question_id,
        "annotation_status": qa_record["annotation_status"],
        "expected_behavior": qa_record["expected_behavior"],
        "reasoning_type": qa_record["reasoning_type"],
        "retrieved": retrieval_row["retrieved"],
        "retrieval_metrics": retrieval_row.get("metrics"),
        "response": response,
        "metrics": refusal_behavior_metrics(
            qa_record["expected_behavior"],
            response,
        ),
    }


def build_generation_summary(rows: list[dict], *, run_id: str) -> dict:
    """Aggregate refusal confusion metrics by retrieval method and cohort."""
    cells = []
    retrieval_conditioned_cells = []
    for method in sorted({row["method"] for row in rows}):
        method_rows = [row for row in rows if row["method"] == method]
        for cohort in COHORTS:
            cohort_rows = [
                row
                for row in method_rows
                if cohort == "all_annotations"
                or row["annotation_status"] == "confirmed"
            ]
            cells.append(_summary_cell(method, cohort, cohort_rows))
            for condition, complete in (
                ("complete_evidence", True),
                ("incomplete_evidence", False),
            ):
                conditioned_rows = [
                    row
                    for row in cohort_rows
                    if row["expected_behavior"] != "refuse"
                    and isinstance(row.get("retrieval_metrics"), dict)
                    and row["retrieval_metrics"].get("complete_evidence_hit_at_5")
                    is complete
                ]
                conditioned_cell = _summary_cell(method, cohort, conditioned_rows)
                conditioned_cell["retrieval_condition"] = condition
                retrieval_conditioned_cells.append(conditioned_cell)

    return {
        "schema_version": "2",
        "run_id": run_id,
        "cells": cells,
        "retrieval_conditioned_cells": retrieval_conditioned_cells,
    }


def _summary_cell(method: str, cohort: str, rows: list[dict]) -> dict:
    evaluated = [
        row for row in rows if row["metrics"]["refusal_correct"] is not None
    ]
    true_positive = _count(evaluated, "refusal_true_positive")
    false_positive = _count(evaluated, "refusal_false_positive")
    false_negative = _count(evaluated, "refusal_false_negative")
    true_negative = (
        len(evaluated) - true_positive - false_positive - false_negative
    )
    system_error_n = sum(
        1 for row in rows if row["metrics"]["generation_system_error"]
    )

    return {
        "method": method,
        "cohort": cohort,
        "n": len(rows),
        "evaluated_n": len(evaluated),
        "system_error_n": system_error_n,
        "metrics": {
            "refusal_accuracy": _ratio(
                true_positive + true_negative,
                len(evaluated),
            ),
            "refusal_precision": _ratio(
                true_positive,
                true_positive + false_positive,
            ),
            "refusal_recall": _ratio(
                true_positive,
                true_positive + false_negative,
            ),
            "refusal_false_positive_rate": _ratio(
                false_positive,
                false_positive + true_negative,
            ),
            "generation_system_error_rate": _ratio(system_error_n, len(rows)),
        },
    }


def _count(rows: list[dict], metric_name: str) -> int:
    return sum(1 for row in rows if row["metrics"][metric_name] is True)


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 4)
