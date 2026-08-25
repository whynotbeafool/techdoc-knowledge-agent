"""Pure aggregation helpers for retrieval evaluation runs."""

from collections.abc import Iterable

QUESTION_CLASSES = {
    "answerable": "answer",
    "counter_evidence": "correct_premise",
}
COHORTS = ("all_annotations", "confirmed_only")
REASONING_STRATA = ("single_evidence", "multi_evidence", "multi_hop")
LEXICAL_STRATA = ("low", "medium", "high")
# (stratum_kind, stratum) pairs. The two stratifications are reported side by
# side rather than crossed: guideline 6.1 requires a reasoning_type breakdown
# and 5.1 requires a lexical-overlap breakdown, neither asks for the product,
# and crossing them would be too sparse to interpret at this dataset size.
STRATA = (
    ("overall", "overall"),
    *(("reasoning_type", value) for value in REASONING_STRATA),
    *(("lexical_overlap", value) for value in LEXICAL_STRATA),
)
METRIC_PREFIXES = (
    "evidence_recall_at_",
    "complete_evidence_hit_at_",
    "reciprocal_rank_at_",
)


def build_run_summary(rows: list[dict], *, run_id: str) -> dict:
    """Return deterministic method × class × cohort × stratum summary cells.

    Cells carry ``stratum_kind`` because ``stratum`` now spans two independent
    axes. Only reasoning_type cells partition the cohort; lexical_overlap cells
    omit questions with no recorded overlap (out_of_scope items, and pilot
    records annotated before the field existed), so they need not sum to
    ``overall``.
    """
    methods = sorted({row["method"] for row in rows})
    metric_names = _metric_names(rows)
    cells = []

    for method in methods:
        for question_class in QUESTION_CLASSES:
            for cohort in COHORTS:
                for stratum_kind, stratum in STRATA:
                    cell_rows = _filter_rows(
                        rows,
                        method=method,
                        question_class=question_class,
                        cohort=cohort,
                        stratum_kind=stratum_kind,
                        stratum=stratum,
                    )
                    cells.append(
                        {
                            "method": method,
                            "question_class": question_class,
                            "cohort": cohort,
                            "stratum_kind": stratum_kind,
                            "stratum": stratum,
                            "n": len(cell_rows),
                            "metrics": _mean_metrics(cell_rows, metric_names),
                        }
                    )

    return {
        "schema_version": "2",
        "run_id": run_id,
        "cells": cells,
    }


def _filter_rows(
    rows: list[dict],
    *,
    method: str,
    question_class: str,
    cohort: str,
    stratum_kind: str,
    stratum: str,
) -> list[dict]:
    """Filter one cell; cohort is the only all/confirmed behavior switch."""
    expected_behavior = QUESTION_CLASSES[question_class]
    return sorted(
        (
            row
            for row in rows
            if row["method"] == method
            and row["expected_behavior"] == expected_behavior
            and (
                cohort == "all_annotations"
                or row["annotation_status"] == "confirmed"
            )
            and _in_stratum(row, stratum_kind, stratum)
        ),
        key=lambda row: row["question_id"],
    )


def _in_stratum(row: dict, stratum_kind: str, stratum: str) -> bool:
    if stratum_kind == "overall":
        return True
    if stratum_kind == "reasoning_type":
        return row["reasoning_type"] == stratum
    # Absent for out_of_scope questions and for runs produced before the field
    # was recorded; such rows belong to no lexical cell rather than crashing.
    return row.get("lexical_stratum") == stratum


def _metric_names(rows: Iterable[dict]) -> list[str]:
    return sorted(
        {
            name
            for row in rows
            for name in row["metrics"]
            if name.startswith(METRIC_PREFIXES)
        }
    )


def _mean_metrics(rows: list[dict], metric_names: list[str]) -> dict | None:
    if not rows:
        return None

    return {
        name: _round_mean(row["metrics"][name] for row in rows)
        for name in metric_names
    }


def _round_mean(values: Iterable[float | bool | None]) -> float | None:
    present_values = [float(value) for value in values if value is not None]
    if not present_values:
        return None
    return round(sum(present_values) / len(present_values), 4)
