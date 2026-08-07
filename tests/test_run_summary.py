import json

from app.evaluation.retrieval import retrieval_metrics
from app.evaluation.summary import build_run_summary


def _evidence(start=10, end=20):
    return {
        "document_id": "doc",
        "revision": "v1",
        "start_char": start,
        "end_char": end,
    }


def _chunk(start=10, end=20):
    return {
        "document_id": "doc",
        "revision": "v1",
        "start_char": start,
        "end_char": end,
    }


def _row(
    question_id,
    *,
    method="bm25",
    behavior="answer",
    status="confirmed",
    reasoning_type="single_evidence",
    recall_at_1=1.0,
    recall_at_3=1.0,
    recall_at_5=1.0,
    reciprocal_rank=1.0,
):
    return {
        "run_id": "run-a",
        "method": method,
        "question_id": question_id,
        "expected_behavior": behavior,
        "annotation_status": status,
        "reasoning_type": reasoning_type,
        "metrics": {
            "evidence_recall_at_1": recall_at_1,
            "evidence_recall_at_3": recall_at_3,
            "evidence_recall_at_5": recall_at_5,
            "complete_evidence_hit_at_1": recall_at_1 == 1.0,
            "complete_evidence_hit_at_3": recall_at_3 == 1.0,
            "complete_evidence_hit_at_5": recall_at_5 == 1.0,
            "first_relevant_rank": (
                None if reciprocal_rank in {None, 0.0} else round(1 / reciprocal_rank)
            ),
            "reciprocal_rank_at_5": reciprocal_rank,
        },
    }


def _cell(summary, **dimensions):
    return next(
        cell
        for cell in summary["cells"]
        if all(cell[key] == value for key, value in dimensions.items())
    )


def test_retrieval_metrics_preserve_reciprocal_rank_three_states():
    no_evidence = retrieval_metrics({"evidence": []}, [], ks=(1, 5))
    no_hit = retrieval_metrics({"evidence": [_evidence()]}, [_chunk(30, 40)], ks=(1, 5))
    rank_two = retrieval_metrics(
        {"evidence": [_evidence()]},
        [_chunk(30, 40), _chunk()],
        ks=(1, 5),
    )

    assert no_evidence["first_relevant_rank"] is None
    assert no_evidence["reciprocal_rank_at_5"] is None
    assert no_hit["first_relevant_rank"] is None
    assert no_hit["reciprocal_rank_at_5"] == 0.0
    assert rank_two["first_relevant_rank"] == 2
    assert rank_two["reciprocal_rank_at_5"] == 0.5


def test_summary_excludes_out_of_scope_and_keeps_empty_cells_null():
    rows = [
        _row("q001"),
        _row(
            "q002",
            behavior="refuse",
            reasoning_type="not_applicable",
            recall_at_1=None,
            recall_at_3=None,
            recall_at_5=None,
            reciprocal_rank=None,
        ),
    ]

    summary = build_run_summary(rows, run_id="run-a")
    overall = _cell(
        summary,
        method="bm25",
        question_class="answerable",
        cohort="all_annotations",
        stratum="overall",
    )
    empty = _cell(
        summary,
        method="bm25",
        question_class="counter_evidence",
        cohort="all_annotations",
        stratum="overall",
    )

    assert overall["n"] == 1
    assert empty["n"] == 0
    assert empty["metrics"] is None


def test_stratum_counts_sum_to_overall_and_recall_at_one_keeps_ceiling():
    multi_evidence_metrics = retrieval_metrics(
        {"evidence": [_evidence(10, 20), _evidence(30, 40)]},
        [_chunk(10, 20)],
        ks=(1, 3, 5),
    )
    rows = [
        _row("q001", reasoning_type="single_evidence"),
        _row(
            "q004",
            reasoning_type="multi_evidence",
            recall_at_1=0.5,
        ),
        _row(
            "q005",
            reasoning_type="multi_hop",
            status="needs_review",
            reciprocal_rank=1 / 3,
        ),
    ]
    rows[1]["metrics"] = multi_evidence_metrics

    summary = build_run_summary(rows, run_id="run-a")
    overall = _cell(
        summary,
        method="bm25",
        question_class="answerable",
        cohort="all_annotations",
        stratum="overall",
    )
    strata = [
        cell
        for cell in summary["cells"]
        if cell["method"] == "bm25"
        and cell["question_class"] == "answerable"
        and cell["cohort"] == "all_annotations"
        and cell["stratum"] != "overall"
    ]
    multi_evidence = _cell(
        summary,
        method="bm25",
        question_class="answerable",
        cohort="all_annotations",
        stratum="multi_evidence",
    )

    assert sum(cell["n"] for cell in strata) == overall["n"]
    assert multi_evidence["metrics"]["evidence_recall_at_1"] == 0.5
    assert overall["metrics"]["reciprocal_rank_at_5"] == 0.7778


def test_summary_is_deterministic_except_for_run_id_and_strict_json():
    rows = [
        _row("q001", method="dense"),
        _row("q001", method="bm25"),
        _row("q003", method="dense", behavior="correct_premise"),
        _row("q003", method="bm25", behavior="correct_premise"),
    ]

    first = build_run_summary(rows, run_id="run-a")
    second = build_run_summary(list(reversed(rows)), run_id="run-b")
    first["run_id"] = "<run-id>"
    second["run_id"] = "<run-id>"

    first_bytes = json.dumps(
        first,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
        allow_nan=False,
    ).encode()
    second_bytes = json.dumps(
        second,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
        allow_nan=False,
    ).encode()
    parsed = json.loads(
        first_bytes,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )

    assert first_bytes == second_bytes
    assert parsed["schema_version"] == "1"
