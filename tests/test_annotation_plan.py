import json
from pathlib import Path

from app.evaluation.plan import check_annotation_plan_files

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PLAN_PATH = PROJECT_ROOT / "data" / "eval" / "annotation-plan.json"


def _load_plan() -> dict:
    return json.loads(PLAN_PATH.read_text(encoding="utf-8"))


def _write_inputs(tmp_path: Path, plan: dict, records: list[dict]) -> tuple[Path, Path]:
    plan_path = tmp_path / "annotation-plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    qa_path = tmp_path / "qa.jsonl"
    qa_path.write_text(
        "".join(f"{json.dumps(record)}\n" for record in records),
        encoding="utf-8",
    )
    return qa_path, plan_path


def _evidence_record(
    question_id: str,
    reasoning_type: str,
    expected_behavior: str,
    stratum: str,
    document_id: str = "rag_paper",
) -> dict:
    question_by_stratum = {
        "low": "alpha beta gamma delta epsilon",
        "medium": "alpha beta gamma",
        "high": "alpha beta",
    }
    return {
        "question_id": question_id,
        "question": question_by_stratum[stratum],
        "reasoning_type": reasoning_type,
        "expected_behavior": expected_behavior,
        "evidence": [{"document_id": document_id, "quote": "alpha"}],
    }


def _record_for_slot(slot: dict, document_id: str | None = None) -> dict:
    if slot["expected_behavior"] == "refuse":
        return {
            "question_id": slot["question_id"],
            "question": "missing subject",
            "reasoning_type": slot["reasoning_type"],
            "expected_behavior": "refuse",
            "evidence": [],
        }
    return _evidence_record(
        slot["question_id"],
        slot["reasoning_type"],
        slot["expected_behavior"],
        slot["target_stratum"],
        document_id or "rag_paper",
    )


def _complete_records(plan: dict) -> list[dict]:
    records = [
        {"question_id": "q001", "expected_behavior": "answer", "reasoning_type": "single_evidence"},
        {"question_id": "q002", "expected_behavior": "refuse", "reasoning_type": "not_applicable"},
        {
            "question_id": "q003",
            "expected_behavior": "correct_premise",
            "reasoning_type": "single_evidence",
        },
        {"question_id": "q004", "expected_behavior": "answer", "reasoning_type": "multi_evidence"},
        {"question_id": "q005", "expected_behavior": "answer", "reasoning_type": "multi_hop"},
    ]
    document_ids = plan["corpus_coverage"]["document_ids"]
    evidence_index = 0
    for slot in plan["slots"]:
        document_id = None
        if slot["expected_behavior"] != "refuse":
            document_id = document_ids[evidence_index % len(document_ids)]
            evidence_index += 1
        records.append(_record_for_slot(slot, document_id))
    return records


def test_target_stratum_mismatch_returns_exactly_one_question_error(tmp_path):
    plan = _load_plan()
    record = _evidence_record("q006", "single_evidence", "answer", "high")
    qa_path, plan_path = _write_inputs(tmp_path, plan, [record])

    report = check_annotation_plan_files(qa_path, plan_path)
    errors = [issue for issue in report.issues if issue.severity == "error"]

    assert len(errors) == 1
    assert errors[0].question_id == "q006"


def test_empty_qa_is_valid_incomplete_progress(tmp_path):
    qa_path, plan_path = _write_inputs(tmp_path, _load_plan(), [])

    report = check_annotation_plan_files(qa_path, plan_path)

    assert report.issues == ()
    assert report.progress.completed == 0
    assert report.progress.next_pending == "q006"


def test_plan_distribution_mismatch_is_an_error(tmp_path):
    plan = _load_plan()
    plan["slots"][0]["target_stratum"] = "medium"
    qa_path, plan_path = _write_inputs(tmp_path, plan, [])

    report = check_annotation_plan_files(qa_path, plan_path)

    assert any(
        issue.severity == "error" and "distribution" in issue.message
        for issue in report.issues
    )


def test_complete_30_question_plan_has_no_errors(tmp_path):
    plan = _load_plan()
    qa_path, plan_path = _write_inputs(tmp_path, plan, _complete_records(plan))

    report = check_annotation_plan_files(qa_path, plan_path)

    assert [issue for issue in report.issues if issue.severity == "error"] == []
    assert [issue for issue in report.issues if issue.severity == "warning"] == []
    assert report.progress.completed == 25
    assert report.progress.next_pending is None


def test_question_id_outside_plan_is_an_error(tmp_path):
    qa_path, plan_path = _write_inputs(
        tmp_path,
        _load_plan(),
        [{"question_id": "q999"}],
    )

    report = check_annotation_plan_files(qa_path, plan_path)
    errors = [issue for issue in report.issues if issue.severity == "error"]

    assert len(errors) == 1
    assert errors[0].question_id == "q999"
