import pytest
from app.evaluation.selective import select_working_point, selective_summary, validate_group_split
from app.rag.gating import ContextChunk, gate


def record(qid="new1", behavior="answer", **overrides):
    row = dict(
        question_id=qid,
        execution_status="ok",
        behavior=behavior,
        corpus_supported=True,
        context_sufficient=True,
        correct=True,
        complete=True,
        supported=True,
    )
    if behavior in {"refusal", None}:
        row.update(correct=None, complete=None, supported=None)
    return {**row, **overrides}


def test_mixed_correction_partial_unsupported_refusal_and_failure_denominators():
    rows = [
        record("1", "correction"),
        record("2", "partial", complete=False),
        record("3", supported=False),
        record("4", "refusal"),
        record("5", None, execution_status="system_error"),
    ]
    m = selective_summary(rows)["metrics"]
    assert m["answer_coverage"]["value"] == 3 / 5
    assert m["selective_risk"]["value"] == 2 / 3
    assert m["unsupported_answer_rate"]["value"] == 1 / 5
    assert m["end_to_end_valid_response_rate"]["value"] == 1 / 5
    assert m["false_refusal_rate"]["value"] == 1 / 5
    assert m["system_error_rate"]["value"] == 1 / 5


def test_all_refusal_and_empty_samples_have_no_zero_risk_reward():
    result = selective_summary([record(behavior="refusal")])["metrics"]
    assert result["answer_coverage"]["value"] == 0
    assert result["selective_risk"]["value"] is None
    assert result["selective_risk"]["denominator"] == 0
    assert all(m["value"] is None for m in selective_summary([])["metrics"].values())


def test_unknown_labels_withhold_risk_instead_of_dropping_hard_samples():
    m = selective_summary([record("1"), record("2", correct=None)])["metrics"]
    assert m["answer_coverage"]["value"] == 1
    assert m["selective_risk"]["denominator"] == 2
    assert m["selective_risk"]["value"] is None
    assert m["selective_risk"]["missing_label_rows"] == 1


def test_failures_cannot_masquerade_as_correct_refusals():
    with pytest.raises(ValueError):
        selective_summary([record(behavior="refusal", execution_status="system_error")])


def test_unknown_behavior_is_not_silently_refusal():
    metrics = selective_summary([record(behavior=None)])["metrics"]
    assert metrics["answer_coverage"]["value"] is None
    assert metrics["answer_coverage"]["denominator"] == 1


def test_c_ablation_zero_threshold_matches_b_and_a_never_gates():
    chunks = [ContextChunk("Python style", 2.0)]
    for score in (0, 2, 3):
        b = gate("What is the limit?", chunks, strategy="B", score_threshold=score)
        c = gate("What is the limit?", chunks, strategy="C", score_threshold=score, lexical_threshold=0)
        assert b["allow_generation"] == c["allow_generation"]
    assert (
        gate("What is the limit?", chunks, strategy="C", lexical_threshold=0.5)["allow_generation"] is False
    )
    assert gate("Question", [], strategy="A")["allow_generation"] is True
    assert gate("Question", [], strategy="B")["allow_generation"] is False


def test_no_answer_or_gold_record_is_accepted_at_gate_boundary():
    with pytest.raises(TypeError):
        gate("Question", [{"text": "data", "score": 1, "reference_answer": "leak"}], strategy="C")


def test_no_informative_tokens_and_threshold_ties_are_explicit():
    chunks = [ContextChunk("irrelevant", 2.0)]
    assert gate("What is it?", chunks, strategy="C", score_threshold=2, lexical_threshold=0)[
        "allow_generation"
    ]
    assert not gate("What is it?", chunks, strategy="C", score_threshold=2, lexical_threshold=0.25)[
        "allow_generation"
    ]


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), True])
def test_invalid_scores_rejected(bad):
    with pytest.raises(ValueError):
        gate("Question", [ContextChunk("data", bad)], strategy="B")


def test_group_split_leakage_and_exposed_test_rejected():
    with pytest.raises(ValueError, match="crosses"):
        validate_group_split(
            [
                {"question_id": "1", "group_id": "same", "split": "dev"},
                {"question_id": "2", "group_id": "same", "split": "test", "previously_exposed": False},
            ]
        )
    with pytest.raises(ValueError, match="unexposed"):
        validate_group_split([{"question_id": "old", "group_id": "g", "split": "test"}])


def test_legacy_ids_cannot_be_relabelled_as_unexposed_test():
    with pytest.raises(ValueError, match="unexposed"):
        validate_group_split(
            [{"question_id": "q001", "group_id": "new-name", "split": "test", "previously_exposed": False}]
        )


def candidate(rows, threshold=0, calls=1):
    return {
        "summary": selective_summary(rows),
        "score_threshold": threshold,
        "lexical_threshold": 0,
        "generation_call_n": calls,
    }


def test_selection_rejects_test_and_does_not_lower_infeasible_target():
    with pytest.raises(ValueError, match="development-only"):
        select_working_point([], split="test")
    result = select_working_point([candidate([record(behavior="refusal")])], split="dev")
    assert result["status"] == "infeasible" and result["selected"] is None


def test_selection_blocks_missing_labels_and_applies_tie_rules():
    good = candidate([record()], threshold=2, calls=1)
    missing = candidate([record(correct=None)])
    assert select_working_point([good, missing], split="dev")["status"] == "incomplete_annotations"
    costly = candidate([record()], threshold=0, calls=2)
    tie = candidate([record()], threshold=1, calls=1)
    result = select_working_point([good, costly, tie], split="dev")
    assert result["selected"] == tie


def test_semantic_contradictions_require_review():
    with pytest.raises(ValueError, match="Partial"):
        selective_summary([record(behavior="partial")])
    with pytest.raises(ValueError, match="contradicts"):
        selective_summary([record(context_sufficient=False)])
