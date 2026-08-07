import importlib.util
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "find_evidence.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("find_evidence", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


find_evidence = _load_script()


@pytest.mark.parametrize(
    ("text", "start", "end", "expected"),
    [
        # Widen a mid-sentence match out to its own sentence, not the neighbours.
        (
            "First one. Second has target here. Third one.",
            len("First one. Second has "),
            len("First one. Second has target"),
            "Second has target here.",
        ),
        # A match in the final sentence has no trailing delimiter to stop at.
        ("Only one. Trailing sentence with target", 34, 40, "Trailing sentence with target"),
        # A single sentence with no delimiters at all returns the whole span.
        ("no delimiters at all here", 3, 13, "no delimiters at all here"),
    ],
)
def test_sentence_span_widens_to_sentence_boundaries(text, start, end, expected):
    left, right = find_evidence._sentence_span(text, start, end)
    assert text[left:right] == expected


def test_sentence_span_trims_surrounding_whitespace():
    text = "First. \n\n  Padded target sentence.  \n Next."
    start = text.index("target")
    left, right = find_evidence._sentence_span(text, start, start + len("target"))

    assert text[left:right] == "Padded target sentence."
    assert not text[left].isspace()
    assert not text[right - 1].isspace()


def test_script_reuses_the_validator_overlap_functions():
    """The drafting aid must not reimplement the metric.

    If it computed overlap independently, a question could score as `high`
    while the validator disagreed, which is exactly the mismatch this tool
    exists to prevent.
    """
    from app.evaluation import dataset

    assert find_evidence.lexical_overlap_score is dataset.lexical_overlap_score
    assert find_evidence.lexical_overlap_stratum is dataset.lexical_overlap_stratum
    assert find_evidence._content_tokens is dataset._content_tokens
