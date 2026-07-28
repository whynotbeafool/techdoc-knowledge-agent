import json
from pathlib import Path

from app.corpus import build_canonical_document
from app.evaluation.dataset import validate_qa_dataset


def _build_record(tmp_path: Path) -> tuple[Path, Path, dict]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    source = tmp_path / "doc.txt"
    source.write_text("Evidence supports the answer.", encoding="utf-8")
    corpus_dir = tmp_path / "corpus"
    build_canonical_document(
        source,
        document_id="doc",
        revision="v1",
        corpus_dir=corpus_dir,
    )
    record = {
        "schema_version": "0.2",
        "guideline_version": "0",
        "question_id": "q001",
        "question": "What supports the answer?",
        "answerability": "answerable",
        "expected_behavior": "answer",
        "unanswerable_reason": None,
        "reasoning_type": "single_evidence",
        "reference_answer": "Evidence does.",
        "evidence": [
            {
                "evidence_id": "e001",
                "document_id": "doc",
                "revision": "v1",
                "page": None,
                "start_char": 0,
                "end_char": 29,
                "quote": "Evidence supports the answer.",
            }
        ],
        "annotation_status": "confirmed",
        "split": "dev",
        "annotator": "self",
        "created_at": "2026-07-28",
    }
    qa_path = tmp_path / "qa.jsonl"
    return qa_path, corpus_dir, record


def _write_record(path: Path, record: dict) -> None:
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")


def test_validate_qa_dataset_accepts_valid_answerable_record(tmp_path):
    qa_path, corpus_dir, record = _build_record(tmp_path)
    _write_record(qa_path, record)

    assert validate_qa_dataset(qa_path, corpus_dir) == []


def test_validate_qa_dataset_detects_quote_and_page_mismatch(tmp_path):
    qa_path, corpus_dir, record = _build_record(tmp_path)
    record["evidence"][0]["quote"] = "wrong"
    record["evidence"][0]["page"] = 1
    _write_record(qa_path, record)

    messages = [
        issue.message for issue in validate_qa_dataset(qa_path, corpus_dir)
    ]

    assert any("Quote mismatch" in message for message in messages)
    assert any("Page mismatch" in message for message in messages)


def test_validate_qa_dataset_enforces_refuse_field_combination(tmp_path):
    qa_path, corpus_dir, record = _build_record(tmp_path)
    record.update(
        {
            "answerability": "unanswerable",
            "expected_behavior": "refuse",
            "unanswerable_reason": "out_of_scope",
            "reasoning_type": "not_applicable",
            "reference_answer": "should be null",
        }
    )
    _write_record(qa_path, record)

    messages = [
        issue.message for issue in validate_qa_dataset(qa_path, corpus_dir)
    ]

    assert any("null reference_answer" in message for message in messages)
    assert any("requires no evidence" in message for message in messages)


def test_validate_qa_dataset_warns_for_long_quote(tmp_path):
    source = tmp_path / "doc.txt"
    source.write_text("x" * 301, encoding="utf-8")
    corpus_dir = tmp_path / "corpus"
    build_canonical_document(
        source,
        document_id="doc",
        revision="v1",
        corpus_dir=corpus_dir,
    )
    qa_path, _, record = _build_record(tmp_path / "other")
    record["evidence"][0].update(
        {
            "document_id": "doc",
            "start_char": 0,
            "end_char": 301,
            "quote": "x" * 301,
        }
    )
    _write_record(qa_path, record)

    issues = validate_qa_dataset(qa_path, corpus_dir)

    assert any(issue.severity == "warning" for issue in issues)
