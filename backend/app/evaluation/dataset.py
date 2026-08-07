import json
import re
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

V1_REQUIRED_FIELDS = {"unanswerable_search", "lexical_overlap"}
CONTENT_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+")
CONTENT_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "did", "do", "does",
    "for", "from", "how", "in", "is", "it", "of", "on", "or", "that", "the",
    "this", "to", "was", "were", "what", "when", "where", "which", "who", "why",
    "with",
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
        issues.extend(
            _validate_search_audit(record, corpus_dir, document_cache)
        )

    return issues


def _validate_record_fields(record: dict) -> list[ValidationIssue]:
    question_id = record["question_id"]
    issues = []
    if record["schema_version"] not in {"0.2", "0.3"}:
        issues.append(ValidationIssue("error", question_id, "Unsupported schema_version"))
    if record["guideline_version"] not in {"0", "1"}:
        issues.append(
            ValidationIssue("error", question_id, "Unsupported guideline_version")
        )
    if (record["schema_version"], record["guideline_version"]) not in {
        ("0.2", "0"),
        ("0.3", "1"),
    }:
        issues.append(
            ValidationIssue(
                "error", question_id, "schema_version and guideline_version do not match"
            )
        )
    if record["guideline_version"] == "1":
        missing_v1 = sorted(V1_REQUIRED_FIELDS - record.keys())
        if missing_v1:
            issues.append(
                ValidationIssue(
                    "error",
                    question_id,
                    f"Missing v1 fields: {', '.join(missing_v1)}",
                )
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

    if record["guideline_version"] == "1" and not (V1_REQUIRED_FIELDS - record.keys()):
        issues.extend(_validate_v1_design_fields(record))

    return issues


def _validate_v1_design_fields(record: dict) -> list[ValidationIssue]:
    question_id = record["question_id"]
    issues = []
    search_audit = record["unanswerable_search"]
    overlap = record["lexical_overlap"]

    if record["expected_behavior"] == "refuse":
        if not isinstance(search_audit, dict):
            issues.append(
                ValidationIssue("error", question_id, "refuse requires unanswerable_search")
            )
    elif search_audit is not None:
        issues.append(
            ValidationIssue(
                "error", question_id, "unanswerable_search is only valid for refuse"
            )
        )

    if record["expected_behavior"] == "refuse":
        if overlap is not None:
            issues.append(
                ValidationIssue("error", question_id, "refuse requires null lexical_overlap")
            )
        return issues

    if not isinstance(overlap, dict):
        issues.append(
            ValidationIssue("error", question_id, "evidence-bearing records require lexical_overlap")
        )
        return issues
    if overlap.get("metric") != "question_content_token_recall_in_evidence":
        issues.append(ValidationIssue("error", question_id, "Invalid lexical overlap metric"))
        return issues
    expected_score = lexical_overlap_score(record["question"], record["evidence"])
    score = overlap.get("score")
    if not isinstance(score, (int, float)) or isinstance(score, bool):
        issues.append(ValidationIssue("error", question_id, "Invalid lexical overlap score"))
        return issues
    if abs(score - expected_score) > 0.00005:
        issues.append(
            ValidationIssue(
                "error",
                question_id,
                f"Lexical overlap score mismatch: expected {expected_score:.4f}, got {score}",
            )
        )
    expected_stratum = lexical_overlap_stratum(expected_score)
    if overlap.get("stratum") != expected_stratum:
        issues.append(
            ValidationIssue(
                "error",
                question_id,
                f"Lexical overlap stratum mismatch: expected {expected_stratum}",
            )
        )
    return issues


def lexical_overlap_score(question: str, evidence: list[dict]) -> float:
    question_tokens = _content_tokens(question)
    evidence_tokens = _content_tokens(
        " ".join(item.get("quote", "") for item in evidence if isinstance(item, dict))
    )
    if not question_tokens:
        return 0.0
    return round(len(question_tokens & evidence_tokens) / len(question_tokens), 4)


def lexical_overlap_stratum(score: float) -> str:
    if score < 0.25:
        return "low"
    if score < 0.50:
        return "medium"
    return "high"


def _content_tokens(text: str) -> set[str]:
    return {
        token
        for token in CONTENT_TOKEN_PATTERN.findall(text.lower())
        if token not in CONTENT_STOPWORDS
    }


def _validate_search_audit(
    record: dict,
    corpus_dir: Path,
    document_cache: dict[tuple[str, str], LoadedCanonicalDocument],
) -> list[ValidationIssue]:
    if record.get("guideline_version") != "1" or record.get("expected_behavior") != "refuse":
        return []
    question_id = record["question_id"]
    audit = record.get("unanswerable_search")
    if not isinstance(audit, dict):
        return []

    issues = []
    searched_terms = audit.get("searched_terms")
    searched_term_items = searched_terms if isinstance(searched_terms, list) else []
    distinct_terms = {
        term.strip().lower()
        for term in searched_term_items
        if isinstance(term, str) and term.strip()
    }
    if not isinstance(searched_terms, list) or len(distinct_terms) < 2:
        issues.append(
            ValidationIssue(
                "error",
                question_id,
                "unanswerable_search requires at least two distinct searched_terms",
            )
        )

    candidates = audit.get("candidate_checks")
    if not isinstance(candidates, list) or not candidates:
        issues.append(
            ValidationIssue(
                "error",
                question_id,
                "unanswerable_search requires at least one candidate check",
            )
        )
        return issues

    required = {
        "document_id",
        "revision",
        "start_char",
        "end_char",
        "quote",
        "reason_not_answer",
    }
    for index, candidate in enumerate(candidates, start=1):
        if not isinstance(candidate, dict):
            issues.append(
                ValidationIssue("error", question_id, f"Candidate check {index} must be an object")
            )
            continue
        missing = sorted(required - candidate.keys())
        if missing:
            issues.append(
                ValidationIssue(
                    "error",
                    question_id,
                    f"Candidate check {index} is missing fields: {', '.join(missing)}",
                )
            )
            continue
        if not isinstance(candidate["reason_not_answer"], str) or not candidate["reason_not_answer"].strip():
            issues.append(
                ValidationIssue(
                    "error", question_id, f"Candidate check {index} needs reason_not_answer"
                )
            )
        key = (candidate["document_id"], candidate["revision"])
        try:
            if key not in document_cache:
                document_cache[key] = load_canonical_document(
                    corpus_dir, document_id=key[0], revision=key[1]
                )
            document = document_cache[key]
        except (KeyError, OSError, ValueError) as exc:
            issues.append(
                ValidationIssue(
                    "error",
                    question_id,
                    f"Cannot load candidate revision {key[0]}@{key[1]}: {exc}",
                )
            )
            continue
        start = candidate["start_char"]
        end = candidate["end_char"]
        if (
            not isinstance(start, int)
            or isinstance(start, bool)
            or not isinstance(end, int)
            or isinstance(end, bool)
            or not 0 <= start < end <= len(document.text)
        ):
            issues.append(
                ValidationIssue(
                    "error", question_id, f"Invalid candidate span {index}: [{start}, {end})"
                )
            )
        elif document.text[start:end] != candidate["quote"]:
            issues.append(
                ValidationIssue("error", question_id, f"Candidate quote mismatch at {index}")
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
