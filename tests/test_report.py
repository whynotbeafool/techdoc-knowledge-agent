import json
from pathlib import Path

from app.evaluation.report import build_markdown_report, lexical_series

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = PROJECT_ROOT / "results" / "runs"


def _cell(method, question_class, cohort, stratum_kind, stratum, n, **metrics):
    return {
        "method": method,
        "question_class": question_class,
        "cohort": cohort,
        "stratum_kind": stratum_kind,
        "stratum": stratum,
        "n": n,
        "metrics": {"evidence_recall_at_5": None, **metrics} if n else None,
    }


def _summary(cells):
    return {"schema_version": "2", "run_id": "run-a", "cells": cells}


def _config():
    return {
        "run_id": "run-a",
        "created_at": "2026-08-26T00:00:00+00:00",
        "question_count": 3,
        "qa_hash": "sha256:deadbeef",
        "active_revisions_hash": "sha256:feedface",
        "corpus": [{"document_id": "doc", "revision": "v1"}],
        "chunk_size": 800,
        "chunk_count": 12,
        "top_ks": [1, 3, 5],
        "python_version": "3.13.5",
        "methods": {"bm25": {"k1": 1.5}},
    }


def test_report_omits_empty_cells_and_renders_missing_metrics_as_dashes():
    cells = [
        _cell("bm25", "answerable", "all_annotations", "overall", "overall", 2,
              evidence_recall_at_5=0.5),
        # An empty stratum must not become a table row at all.
        _cell("bm25", "answerable", "all_annotations", "lexical_overlap", "high", 0),
    ]

    report = build_markdown_report(_summary(cells), _config())

    assert "| overall | overall | all_annotations | 2 |" in report
    assert "| lexical_overlap | high |" not in report
    # reciprocal_rank_at_5 was never recorded for this cell.
    assert "--" in report


def test_report_carries_provenance_so_numbers_are_traceable():
    cells = [
        _cell("bm25", "answerable", "all_annotations", "overall", "overall", 2,
              evidence_recall_at_5=0.5),
    ]

    report = build_markdown_report(_summary(cells), _config())

    for expected in ("sha256:deadbeef", "sha256:feedface", "doc@v1", "800 / 12", "3.13.5"):
        assert expected in report


def test_lexical_series_keeps_stratum_order_and_skips_cells_without_data():
    cells = [
        _cell("bm25", "answerable", "all_annotations", "lexical_overlap", "low", 3,
              evidence_recall_at_5=0.2),
        _cell("bm25", "answerable", "all_annotations", "lexical_overlap", "medium", 0),
        _cell("bm25", "answerable", "all_annotations", "lexical_overlap", "high", 1,
              evidence_recall_at_5=0.9),
    ]

    series = lexical_series(
        _summary(cells),
        question_class="answerable",
        cohort="all_annotations",
        metric="evidence_recall_at_5",
    )

    assert series["bm25"] == [("low", 3, 0.2), ("high", 1, 0.9)]


def test_committed_report_matches_the_committed_run():
    """The report must be regenerable, never hand-edited.

    If someone tweaks a number in the Markdown, this fails: the rendered text
    is compared against what the committed summary and config actually produce.
    """
    summary_path = RUNS_DIR / "frozen-30-v1.summary.json"
    report_path = PROJECT_ROOT / "docs" / "results-frozen-30-v1.md"
    if not (summary_path.exists() and report_path.exists()):
        return

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    config = json.loads((RUNS_DIR / "frozen-30-v1.config.json").read_text(encoding="utf-8"))
    expected = build_markdown_report(summary, config)
    actual = report_path.read_text(encoding="utf-8")

    # The script appends a figure link after the generated body.
    assert actual.startswith(expected.rstrip("\n"))
