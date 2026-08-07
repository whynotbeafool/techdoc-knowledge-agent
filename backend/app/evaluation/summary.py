"""Pure aggregation helpers for retrieval evaluation runs."""

from collections.abc import Iterable

QUESTION_CLASSES = {
    "answerable": "answer",
    "counter_evidence": "correct_premise",
}
COHORTS = ("all_annotations", "confirmed_only")
STRATA = ("overall", "single_evidence", "multi_evidence", "multi_hop")
METRIC_PREFIXES = (
    "evidence_recall_at_",
    "complete_evidence_hit_at_",
    "reciprocal_rank_at_",
)


def build_run_summary(rows: list[dict], *, run_id: str) -> dict:
    """Return deterministic method × class × cohort × stratum summary cells."""
    methods = sorted({row["method"] for row in rows})
    metric_names = _metric_names(rows)
    cells = []

    for method in methods:
        for question_class in QUESTION_CLASSES:
            for cohort in COHORTS:
                for stratum in STRATA:
                    cell_rows = _filter_rows(
                        rows,
                        method=method,
                        question_class=question_class,
                        cohort=cohort,
                        stratum=stratum,
                    )
                    cells.append(
                        {
                            "method": method,
                            "question_class": question_class,
                            "cohort": cohort,
                            "stratum": stratum,
                            "n": len(cell_rows),
                            "metrics": _mean_metrics(cell_rows, metric_names),
                        }
                    )

    return {
        "schema_version": "1",
        "run_id": run_id,
        "cells": cells,
    }


def _filter_rows(
    rows: list[dict],
    *,
    method: str,
    question_class: str,
    cohort: str,
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
            and (stratum == "overall" or row["reasoning_type"] == stratum)
        ),
        key=lambda row: row["question_id"],
    )


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
