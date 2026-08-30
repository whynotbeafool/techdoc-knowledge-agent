"""Pure behavior metrics for generated RAG responses."""

from typing import Literal

from app.core.response_contract import (
    GENERATION_SYSTEM_ERROR_PREFIXES,
    REFUSAL_PREFIX,
)

ResponseBehavior = Literal["answer", "refuse", "system_error"]
VALID_EXPECTED_BEHAVIORS = frozenset({"answer", "refuse", "correct_premise"})


def classify_response_behavior(response: str) -> ResponseBehavior:
    """Classify a response using the explicit generation contract.

    The canonical refusal marker must begin the response. Merely discussing the
    marker later in an answer is not counted as a refusal. Infrastructure errors
    are kept separate so they cannot inflate refusal accuracy.
    """
    if not isinstance(response, str):
        raise TypeError("response must be a string")

    normalized = response.lstrip()
    if not normalized:
        raise ValueError("response must be a non-empty string")
    if normalized.startswith(GENERATION_SYSTEM_ERROR_PREFIXES):
        return "system_error"
    if normalized.startswith(REFUSAL_PREFIX):
        return "refuse"
    return "answer"


def refusal_behavior_metrics(
    expected_behavior: str,
    response: str,
) -> dict[str, bool | None]:
    """Return per-example refusal metrics without external calls or state."""
    if expected_behavior not in VALID_EXPECTED_BEHAVIORS:
        raise ValueError(f"Unsupported expected_behavior: {expected_behavior}")

    expected_refusal = expected_behavior == "refuse"
    observed_behavior = classify_response_behavior(response)
    if observed_behavior == "system_error":
        return {
            "expected_refusal": expected_refusal,
            "predicted_refusal": None,
            "refusal_correct": None,
            "refusal_true_positive": None,
            "refusal_false_positive": None,
            "refusal_false_negative": None,
            "generation_system_error": True,
        }

    predicted_refusal = observed_behavior == "refuse"
    return {
        "expected_refusal": expected_refusal,
        "predicted_refusal": predicted_refusal,
        "refusal_correct": predicted_refusal == expected_refusal,
        "refusal_true_positive": predicted_refusal and expected_refusal,
        "refusal_false_positive": predicted_refusal and not expected_refusal,
        "refusal_false_negative": not predicted_refusal and expected_refusal,
        "generation_system_error": False,
    }
