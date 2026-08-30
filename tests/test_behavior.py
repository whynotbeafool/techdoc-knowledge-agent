import pytest
from app.evaluation.behavior import (
    classify_response_behavior,
    refusal_behavior_metrics,
)


def test_classify_response_behavior_recognizes_canonical_refusal_prefix():
    response = "  \n当前资料依据不足，无法从给定文档确定答案。"

    assert classify_response_behavior(response) == "refuse"


def test_classify_response_behavior_does_not_match_phrase_mentioned_later():
    response = "文档足以回答；因此不应输出‘当前资料依据不足’。"

    assert classify_response_behavior(response) == "answer"


def test_classify_response_behavior_recognizes_system_errors():
    assert classify_response_behavior("LLM未配置：缺少 API key") == "system_error"
    assert classify_response_behavior("LLM请求失败，请检查网络") == "system_error"


def test_classify_response_behavior_rejects_empty_or_non_string_responses():
    with pytest.raises(ValueError, match="non-empty string"):
        classify_response_behavior("   ")
    with pytest.raises(TypeError, match="must be a string"):
        classify_response_behavior(None)


def test_refusal_behavior_metrics_records_true_positive():
    metrics = refusal_behavior_metrics("refuse", "当前资料依据不足。")

    assert metrics == {
        "expected_refusal": True,
        "predicted_refusal": True,
        "refusal_correct": True,
        "refusal_true_positive": True,
        "refusal_false_positive": False,
        "refusal_false_negative": False,
        "generation_system_error": False,
    }


def test_refusal_behavior_metrics_exposes_false_negative_and_false_positive():
    false_negative = refusal_behavior_metrics("refuse", "答案是 500 毫秒。")
    false_positive = refusal_behavior_metrics("answer", "当前资料依据不足。")

    assert false_negative["refusal_false_negative"] is True
    assert false_negative["refusal_correct"] is False
    assert false_positive["refusal_false_positive"] is True
    assert false_positive["refusal_correct"] is False


def test_refusal_behavior_metrics_excludes_system_errors_from_accuracy():
    metrics = refusal_behavior_metrics("refuse", "LLM请求失败，请检查网络")

    assert metrics["generation_system_error"] is True
    assert metrics["predicted_refusal"] is None
    assert metrics["refusal_correct"] is None
    assert metrics["refusal_true_positive"] is None
    assert metrics["refusal_false_positive"] is None
    assert metrics["refusal_false_negative"] is None


def test_refusal_behavior_metrics_treats_correction_as_non_refusal_and_validates_behavior():
    metrics = refusal_behavior_metrics("correct_premise", "前提不成立；文档实际说明……")
    assert metrics["expected_refusal"] is False
    assert metrics["predicted_refusal"] is False
    assert metrics["refusal_correct"] is True

    with pytest.raises(ValueError, match="Unsupported expected_behavior"):
        refusal_behavior_metrics("unknown", "回答")
