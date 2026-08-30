import importlib.util
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "evaluate_retrieval.py"
SPEC = importlib.util.spec_from_file_location("evaluate_retrieval_script", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def _row(method, behavior, status, recall):
    return {
        "question_id": f"{method}-{behavior}-{status}",
        "method": method,
        "expected_behavior": behavior,
        "annotation_status": status,
        "reasoning_type": "single_evidence",
        "metrics": {"evidence_recall_at_5": recall},
    }


def test_print_summary_reports_all_and_confirmed_only_and_averages_corrections(capsys):
    rows = [
        _row("bm25", "answer", "confirmed", 1.0),
        _row("bm25", "answer", "needs_review", 0.0),
        _row("bm25", "correct_premise", "confirmed", 1.0),
        _row("bm25", "correct_premise", "needs_review", 0.0),
    ]

    summary = MODULE.build_run_summary(rows, run_id="test-run")
    MODULE._print_summary(summary)
    output = capsys.readouterr().out

    assert (
        "answerable macro Evidence Recall@5 "
        "(all=0.500, n=2; confirmed-only=1.000, n=1)" in output
    )
    assert (
        "counter-evidence Recall@5 "
        "(all=0.500, n=2; confirmed-only=1.000, n=1)" in output
    )


def test_summary_artifact_reserves_run_id(tmp_path, monkeypatch, capsys):
    qa_path = tmp_path / "empty.jsonl"
    qa_path.write_text("", encoding="utf-8")
    summary_path = tmp_path / "occupied.summary.json"
    summary_path.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(
        MODULE.sys,
        "argv",
        [
            str(SCRIPT_PATH),
            "--run-id",
            "occupied",
            "--qa",
            str(qa_path),
            "--results-dir",
            str(tmp_path),
        ],
    )

    assert MODULE.main() == 1
    assert "ERROR run_id already exists: occupied" in capsys.readouterr().out


def test_evaluation_rejects_gold_spans_from_inactive_revision():
    qa_records = [
        {
            "question_id": "q001",
            "evidence": [
                {"document_id": "guide", "revision": "v1"},
            ],
            "unanswerable_search": None,
        }
    ]
    active_records = [{"document_id": "guide", "revision": "v2"}]

    assert MODULE._active_revision_mismatches(qa_records, active_records) == [
        "q001: guide@v1 is not active (selected revision: v2)"
    ]


def test_evaluation_checks_unanswerable_candidate_revisions_too():
    qa_records = [
        {
            "question_id": "q002",
            "evidence": [],
            "unanswerable_search": {
                "candidate_checks": [
                    {"document_id": "guide", "revision": "v1"},
                ]
            },
        }
    ]
    active_records = [{"document_id": "guide", "revision": "v2"}]

    assert MODULE._active_revision_mismatches(qa_records, active_records) == [
        "q002: guide@v1 is not active (selected revision: v2)"
    ]


def test_evaluate_method_preserves_rrf_audit_fields():
    class FakeHybrid:
        def query_chunks(self, question, top_k=5):
            return [
                {
                    "chunk_id": "chunk-a",
                    "document_id": "doc",
                    "revision": "v1",
                    "start_char": 0,
                    "end_char": 10,
                    "rrf_score": 0.03,
                    "component_ranks": {"bm25": 1, "dense": 4},
                }
            ]

    qa_records = [
        {
            "question_id": "q001",
            "question": "question",
            "annotation_status": "confirmed",
            "expected_behavior": "answer",
            "reasoning_type": "single_evidence",
            "lexical_overlap": {"stratum": "low"},
            "evidence": [
                {
                    "document_id": "doc",
                    "revision": "v1",
                    "start_char": 0,
                    "end_char": 10,
                }
            ],
        }
    ]

    row = MODULE._evaluate_method("run", "hybrid_rrf", FakeHybrid(), qa_records)[0]

    assert row["retrieved"][0]["rrf_score"] == 0.03
    assert row["retrieved"][0]["component_ranks"] == {"bm25": 1, "dense": 4}
    assert row["metrics"]["complete_evidence_hit_at_5"] is True
