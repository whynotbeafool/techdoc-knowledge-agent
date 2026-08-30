from app.evaluation.generation import (
    build_generation_row,
    build_generation_summary,
)


def _qa(question_id, behavior, status="confirmed"):
    return {
        "question_id": question_id,
        "annotation_status": status,
        "expected_behavior": behavior,
        "reasoning_type": "not_applicable" if behavior == "refuse" else "single_evidence",
    }


def _retrieval(question_id, method="bm25", complete=True):
    return {
        "run_id": "retrieval-v1",
        "method": method,
        "question_id": question_id,
        "retrieved": [{"chunk_id": "doc_p0_0"}],
        "metrics": {"complete_evidence_hit_at_5": complete},
    }


def test_build_generation_row_combines_provenance_response_and_metrics():
    row = build_generation_row(
        run_id="generation-v1",
        qa_record=_qa("q021", "refuse"),
        retrieval_row=_retrieval("q021"),
        response="当前资料依据不足，无法确定延迟。",
    )

    assert row["run_id"] == "generation-v1"
    assert row["retrieval_run_id"] == "retrieval-v1"
    assert row["method"] == "bm25"
    assert row["response"] == "当前资料依据不足，无法确定延迟。"
    assert row["retrieval_metrics"]["complete_evidence_hit_at_5"] is True
    assert row["metrics"]["refusal_true_positive"] is True


def test_build_generation_row_rejects_mismatched_question_ids():
    try:
        build_generation_row(
            run_id="generation-v1",
            qa_record=_qa("q021", "refuse"),
            retrieval_row=_retrieval("q022"),
            response="当前资料依据不足。",
        )
    except ValueError as exc:
        assert "question_id mismatch" in str(exc)
    else:
        raise AssertionError("Expected mismatched question IDs to fail")


def test_build_generation_summary_reports_confusion_rates_and_system_errors():
    rows = [
        build_generation_row(
            run_id="generation-v1",
            qa_record=_qa("q001", "answer"),
            retrieval_row=_retrieval("q001"),
            response="有证据支持的回答。",
        ),
        build_generation_row(
            run_id="generation-v1",
            qa_record=_qa("q021", "refuse"),
            retrieval_row=_retrieval("q021"),
            response="当前资料依据不足。",
        ),
        build_generation_row(
            run_id="generation-v1",
            qa_record=_qa("q022", "refuse"),
            retrieval_row=_retrieval("q022"),
            response="错误地给出了答案。",
        ),
        build_generation_row(
            run_id="generation-v1",
            qa_record=_qa("q023", "refuse", status="needs_review"),
            retrieval_row=_retrieval("q023"),
            response="LLM请求失败，请检查网络",
        ),
    ]

    summary = build_generation_summary(rows, run_id="generation-v1")
    all_cell = next(
        cell
        for cell in summary["cells"]
        if cell["method"] == "bm25" and cell["cohort"] == "all_annotations"
    )
    confirmed_cell = next(
        cell
        for cell in summary["cells"]
        if cell["method"] == "bm25" and cell["cohort"] == "confirmed_only"
    )

    assert all_cell["n"] == 4
    assert all_cell["evaluated_n"] == 3
    assert all_cell["system_error_n"] == 1
    assert all_cell["metrics"] == {
        "refusal_accuracy": 0.6667,
        "refusal_precision": 1.0,
        "refusal_recall": 0.5,
        "refusal_false_positive_rate": 0.0,
        "generation_system_error_rate": 0.25,
    }
    assert confirmed_cell["n"] == 3
    assert confirmed_cell["system_error_n"] == 0


def test_build_generation_summary_uses_none_for_undefined_precision():
    row = build_generation_row(
        run_id="generation-v1",
        qa_record=_qa("q001", "answer"),
        retrieval_row=_retrieval("q001", method="dense"),
        response="有证据支持的回答。",
    )

    cell = build_generation_summary([row], run_id="generation-v1")["cells"][0]

    assert cell["metrics"]["refusal_precision"] is None
    assert cell["metrics"]["refusal_recall"] is None
    assert cell["metrics"]["refusal_false_positive_rate"] == 0.0


def test_generation_summary_splits_non_refusal_rows_by_retrieval_completeness():
    rows = [
        build_generation_row(
            run_id="generation-v2",
            qa_record=_qa("q001", "answer"),
            retrieval_row=_retrieval("q001", complete=True),
            response="有证据支持的回答。",
        ),
        build_generation_row(
            run_id="generation-v2",
            qa_record=_qa("q006", "answer"),
            retrieval_row=_retrieval("q006", complete=False),
            response="当前资料依据不足。",
        ),
        build_generation_row(
            run_id="generation-v2",
            qa_record=_qa("q021", "refuse"),
            retrieval_row=_retrieval("q021", complete=False),
            response="当前资料依据不足。",
        ),
    ]

    summary = build_generation_summary(rows, run_id="generation-v2")
    cells = {
        (cell["retrieval_condition"], cell["cohort"]): cell
        for cell in summary["retrieval_conditioned_cells"]
    }

    assert cells[("complete_evidence", "all_annotations")]["n"] == 1
    assert (
        cells[("complete_evidence", "all_annotations")]["metrics"]["refusal_accuracy"]
        == 1.0
    )
    assert cells[("incomplete_evidence", "all_annotations")]["n"] == 1
    assert (
        cells[("incomplete_evidence", "all_annotations")]["metrics"]["refusal_accuracy"]
        == 0.0
    )
