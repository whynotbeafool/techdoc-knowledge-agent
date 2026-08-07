import importlib.util
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "evaluate_retrieval.py"
SPEC = importlib.util.spec_from_file_location("evaluate_retrieval_script", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def _row(method, behavior, status, recall):
    return {
        "method": method,
        "expected_behavior": behavior,
        "annotation_status": status,
        "metrics": {"evidence_recall_at_5": recall},
    }


def test_print_summary_reports_all_and_confirmed_only_and_averages_corrections(capsys):
    rows = [
        _row("bm25", "answer", "confirmed", 1.0),
        _row("bm25", "answer", "needs_review", 0.0),
        _row("bm25", "correct_premise", "confirmed", 1.0),
        _row("bm25", "correct_premise", "needs_review", 0.0),
    ]

    MODULE._print_summary(rows)
    output = capsys.readouterr().out

    assert (
        "answerable macro Evidence Recall@5 "
        "(all=0.500, n=2; confirmed-only=1.000, n=1)" in output
    )
    assert (
        "counter-evidence Recall@5 "
        "(all=0.500, n=2; confirmed-only=1.000, n=1)" in output
    )
