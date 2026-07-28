import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from app.corpus import LoadedCanonicalDocument, load_canonical_document

REQUIRED_FIELDS = {
    "schema_version",
    "guideline_version",
    "question_id",
    "question",
    "answerability",
    "expected_behavior",
    "unanswerable_reason",
    "reasoning_type",
    "reference_answer",
    "evidence",
    "annotation_status",
    "split",
    "annotator",
    "created_at",
}


@dataclass(frozen=True)
class ValidationIssue:
    severity: str
    question_id: str
    message: str


def load_qa_jsonl(path: Path) -> list[dict]:
    records = []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at {path}:{line_number}") from exc
            if not isinstance(record, dict):
                raise ValueError(f"Expected a JSON object at {path}:{line_number}")
            records.append(record)
    return records


def validate_qa_dataset(qa_path: Path, corpus_dir: Path) -> list[ValidationIssue]:
    records = load_qa_jsonl(qa_path)
    issues: list[ValidationIssue] = []
    seen_question_ids: set[str] = set()
    document_cache: dict[tuple[str, str], LoadedCanonicalDocument] = {}

    for record in records:
        question_id = record.get("question_id", "<missing>")
        missing = sorted(REQUIRED_FIELDS - record.keys())
        if missing:
            issues.append(
                ValidationIssue(
                    "error",
                    question_id,
                    f"Missing required fields: {', '.join(missing)}",
                )
            )
            continue

        if question_id in seen_question_ids:
            issues.append(
                ValidationIssue("error", question_id, "Duplicate question_id")
            )
        seen_question_ids.add(question_id)

        issues.extend(_validate_record_fields(record))
        issues.extend(_validate_evidence(record, corpus_dir, document_cache))

    return issues


def _validate_record_fields(record: dict) -> list[ValidationIssue]:
    question_id = record["question_id"]
    issues = []
    if record["schema_version"] != "0.2":
        issues.append(ValidationIssue("error", question_id, "Unsupported schema_version"))
    if record["guideline_version"] != "0":
        issues.append(
            ValidationIssue("error", question_id, "Unsupported guideline_version")
        )
    if not isinstance(record["question"], str) or not record["question"].strip():
        issues.append(ValidationIssue("error", question_id, "question must be non-empty"))
    if record["answerability"] not in {"answerable", "unanswerable"}:
        issues.append(ValidationIssue("error", question_id, "Invalid answerability"))
    if record["expected_behavior"] not in {
        "answer",
        "refuse",
        "correct_premise",
    }:
        issues.append(ValidationIssue("error", question_id, "Invalid expected_behavior"))
    if record["reasoning_type"] not in {
        "single_evidence",
        "multi_evidence",
        "multi_hop",
        "not_applicable",
    }:
        issues.append(ValidationIssue("error", question_id, "Invalid reasoning_type"))
    if record["annotation_status"] not in {"confirmed", "needs_review"}:
        issues.append(ValidationIssue("error", question_id, "Invalid annotation_status"))
    if record["split"] != "dev":
        issues.append(ValidationIssue("error", question_id, "v0 records must use dev split"))
    try:
        date.fromisoformat(record["created_at"])
    except (TypeError, ValueError):
        issues.append(ValidationIssue("error", question_id, "Invalid created_at date"))

    evidence = record["evidence"]
    if not isinstance(evidence, list):
        issues.append(ValidationIssue("error", question_id, "evidence must be an array"))
        return issues

    behavior = record["expected_behavior"]
    reference_answer = record["reference_answer"]
    if behavior == "answer":
        if record["answerability"] != "answerable":
            issues.append(
                ValidationIssue("error", question_id, "answer behavior must be answerable")
            )
        if record["unanswerable_reason"] is not None:
            issues.append(
                ValidationIssue(
                    "error",
                    question_id,
                    "answer behavior requires null unanswerable_reason",
                )
            )
        if not isinstance(reference_answer, str) or not reference_answer.strip():
            issues.append(
                ValidationIssue(
                    "error", question_id, "answer behavior requires reference_answer"
                )
            )
        if not evidence:
            issues.append(
                ValidationIssue("error", question_id, "answer behavior requires evidence")
            )
    elif behavior == "refuse":
        if record["answerability"] != "unanswerable":
            issues.append(
                ValidationIssue("error", question_id, "refuse behavior must be unanswerable")
            )
        if record["unanswerable_reason"] != "out_of_scope":
            issues.append(
                ValidationIssue(
                    "error", question_id, "refuse behavior requires out_of_scope reason"
                )
            )
        if reference_answer is not None:
            issues.append(
                ValidationIssue(
                    "error", question_id, "refuse behavior requires null reference_answer"
                )
            )
        if evidence:
            issues.append(
                ValidationIssue("error", question_id, "refuse behavior requires no evidence")
            )
        if record["reasoning_type"] != "not_applicable":
            issues.append(
                ValidationIssue(
                    "error", question_id, "refuse behavior requires not_applicable reasoning"
                )
            )
    elif behavior == "correct_premise":
        if record["answerability"] != "unanswerable":
            issues.append(
                ValidationIssue(
                    "error", question_id, "correct_premise must be unanswerable"
                )
            )
        if record["unanswerable_reason"] != "false_premise":
            issues.append(
                ValidationIssue(
                    "error", question_id, "correct_premise requires false_premise reason"
                )
            )
        if not isinstance(reference_answer, str) or not reference_answer.strip():
            issues.append(
                ValidationIssue(
                    "error", question_id, "correct_premise requires a correction"
                )
            )
        if not evidence:
            issues.append(
                ValidationIssue(
                    "error", question_id, "correct_premise requires counter-evidence"
                )
            )
        if record["reasoning_type"] == "not_applicable":
            issues.append(
                ValidationIssue(
                    "error",
                    question_id,
                    "correct_premise requires an evidence reasoning type",
                )
            )

    return issues


def _validate_evidence(
    record: dict,
    corpus_dir: Path,
    document_cache: dict[tuple[str, str], LoadedCanonicalDocument],
) -> list[ValidationIssue]:
    question_id = record["question_id"]
    evidence = record["evidence"]
    if not isinstance(evidence, list):
        return []

    issues = []
    seen_evidence_ids = set()
    required = {
        "evidence_id",
        "document_id",
        "revision",
        "page",
        "start_char",
        "end_char",
        "quote",
    }
    for item in evidence:
        if not isinstance(item, dict):
            issues.append(
                ValidationIssue("error", question_id, "Evidence item must be an object")
            )
            continue
        missing = sorted(required - item.keys())
        if missing:
            issues.append(
                ValidationIssue(
                    "error",
                    question_id,
                    f"Evidence is missing fields: {', '.join(missing)}",
                )
            )
            continue

        evidence_id = item["evidence_id"]
        if evidence_id in seen_evidence_ids:
            issues.append(
                ValidationIssue(
                    "error", question_id, f"Duplicate evidence_id: {evidence_id}"
                )
            )
        seen_evidence_ids.add(evidence_id)

        key = (item["document_id"], item["revision"])
        try:
            if key not in document_cache:
                document_cache[key] = load_canonical_document(
                    corpus_dir,
                    document_id=key[0],
                    revision=key[1],
                )
            document = document_cache[key]
        except (KeyError, OSError, ValueError) as exc:
            issues.append(
                ValidationIssue(
                    "error",
                    question_id,
                    f"Cannot load evidence revision {key[0]}@{key[1]}: {exc}",
                )
            )
            continue

        start = item["start_char"]
        end = item["end_char"]
        if (
            not isinstance(start, int)
            or isinstance(start, bool)
            or not isinstance(end, int)
            or isinstance(end, bool)
            or not 0 <= start < end <= len(document.text)
        ):
            issues.append(
                ValidationIssue(
                    "error", question_id, f"Invalid span for {evidence_id}: [{start}, {end})"
                )
            )
            continue

        actual_quote = document.text[start:end]
        if actual_quote != item["quote"]:
            issues.append(
                ValidationIssue(
                    "error", question_id, f"Quote mismatch for {evidence_id}"
                )
            )
        actual_page = next(
            (
                span["page"]
                for span in document.metadata["page_spans"]
                if span["start_char"] <= start < span["end_char"]
            ),
            None,
        )
        if actual_page != item["page"]:
            issues.append(
                ValidationIssue(
                    "error",
                    question_id,
                    f"Page mismatch for {evidence_id}: expected {actual_page}, got {item['page']}",
                )
            )
        if len(item["quote"]) > 300:
            issues.append(
                ValidationIssue(
                    "warning",
                    question_id,
                    f"{evidence_id} quote exceeds provisional 300-character limit",
                )
            )

    return issues
