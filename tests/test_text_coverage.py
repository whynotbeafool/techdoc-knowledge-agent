import importlib.util
from pathlib import Path

import pytest
from app.evaluation.coverage import evidence_coverage, span_coverage

ROOT = Path(__file__).resolve().parents[1]


def evidence(quote, start=0, revision="v1"):
    return {
        "document_id": "doc",
        "revision": revision,
        "start_char": start,
        "end_char": start + len(quote),
        "quote": quote,
    }


def chunk(start, end, revision="v1"):
    return {"document_id": "doc", "revision": revision, "start_char": start, "end_char": end}


def test_union_adjacent_duplicate_and_outside_intervals():
    r = span_coverage("abcde", 10, [(0, 11), (10, 13), (10, 13), (13, 20)])
    assert r["covered"] == 5 and r["full_char"] is True
    assert r == span_coverage("abcde", 10, [(10, 15)])


def test_whitespace_exception_does_not_remove_punctuation_or_change_offsets():
    r = span_coverage("甲\n\u00a0🙂!", 10, [(10, 11), (13, 14)])
    assert r["length"] == 5 and r["covered"] == 2
    assert r["nonspace_length"] == 3 and r["nonspace_covered"] == 2
    assert r["full_nonspace"] is False
    assert span_coverage("甲\n\u00a0🙂!", 10, [(10, 11), (13, 15)])["full_nonspace"] is True


def test_no_gold_or_only_whitespace_never_gets_vacuous_complete_credit():
    assert evidence_coverage([], [chunk(0, 5)])["complete_any"] is None
    r = evidence_coverage([evidence(" \n")], [chunk(0, 2)])
    assert r["complete_full_char"] is True
    assert r["complete_full_nonspace"] is None


def test_wrong_revision_is_not_a_hit_and_missing_second_span_is_not_complete():
    gold = [evidence("abc"), evidence("z", start=10)]
    r = evidence_coverage(gold, [chunk(0, 3), chunk(10, 11, revision="v2")])
    assert r["recall_any"] == 0.5 and r["complete_any"] is False
    assert r["mean_char_fraction"] == 0.5


@pytest.mark.parametrize("interval", [(-1, 4), (3, 3), (4, 2), (True, 4)])
def test_invalid_offsets_rejected(interval):
    with pytest.raises(ValueError):
        span_coverage("abcde", 0, [interval])


def test_real_run_matches_saved_primary_and_strict_audit_and_whitespace_diagnostic():
    spec = importlib.util.spec_from_file_location(
        "text_coverage_audit", ROOT / "scripts/audit_text_coverage.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    report = module.audit(
        ROOT / "results/runs/frozen-30-hybrid-rrf-v1.jsonl", ROOT / "data/eval/qa.jsonl", ROOT / "data/corpus"
    )
    cells = {
        c["method"]: c
        for c in report["cells"]
        if c["k"] == 5 and c["cohort"] == "confirmed_only" and c["expected_behavior"] == "answer"
    }
    for method, counts in [("bm25", (8, 6, 7)), ("dense", (7, 5, 6)), ("hybrid_rrf", (9, 8, 9))]:
        assert cells[method]["question_n"] == 17
        for metric, count in zip(("complete_any", "complete_full_char", "complete_full_nonspace"), counts):
            assert cells[method]["metrics"][metric]["sum"] == count
            assert cells[method]["metrics"][metric]["n"] == 17
