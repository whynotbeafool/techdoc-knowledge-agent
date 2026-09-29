"""Semantic-label aggregation; never infers correctness from response prefixes."""

BEHAVIORS = {"answer", "correction", "partial", "refusal"}
ATTEMPTS = {"answer", "correction", "partial"}
LABELS = ("corpus_supported", "context_sufficient", "correct", "complete", "supported")


def and3(*values):
    if any(value is False for value in values):
        return False
    return None if any(value is None for value in values) else True


def not3(value):
    return None if value is None else not value


def rate(numerators, denominators):
    unknown_n = sum(n is None or d is None for n, d in zip(numerators, denominators))
    numerator = sum(n is True for n in numerators) if all(n is not None for n in numerators) else None
    denominator = sum(d is True for d in denominators) if all(d is not None for d in denominators) else None
    return {
        "numerator": numerator,
        "denominator": denominator,
        "missing_label_rows": unknown_n,
        "value": numerator / denominator if not unknown_n and denominator else None,
    }


def selective_summary(rows: list[dict]) -> dict:
    seen = set()
    attempted, errors, unsupported, valid, false_refusals = [], [], [], [], []
    corpus, sufficient, failed = [], [], []
    for row in rows:
        qid = row["question_id"]
        if not isinstance(qid, str) or not qid or qid in seen:
            raise ValueError("Expected distinct question IDs within one strategy/cohort cell")
        seen.add(qid)
        if row["execution_status"] not in {"ok", "system_error"}:
            raise ValueError("Invalid execution status")
        behavior = row["behavior"]
        if behavior is not None and behavior not in BEHAVIORS:
            raise ValueError("Invalid semantic behavior")
        for name in LABELS:
            if row[name] is not None and type(row[name]) is not bool:
                raise ValueError(f"{name} must be boolean or null")
        error = row["execution_status"] == "system_error"
        if error and behavior is not None:
            raise ValueError("System errors cannot be labeled as a normal response")
        if (error or behavior == "refusal") and any(
            row[k] is not None for k in ("correct", "complete", "supported")
        ):
            raise ValueError("No answer-quality labels for failures or pure refusals")
        if row["context_sufficient"] is True and row["corpus_supported"] is False:
            raise ValueError("Sufficient corpus-derived context contradicts unsupported corpus label")
        attempt = False if error else (behavior in ATTEMPTS if behavior is not None else None)
        refusal = False if error else (behavior == "refusal" if behavior is not None else None)
        if behavior == "partial" and row["complete"] is True:
            raise ValueError("Partial answers cannot be labeled complete")
        quality = and3(row["correct"], row["complete"], row["supported"])
        if quality is True and (row["context_sufficient"] is False or row["corpus_supported"] is False):
            raise ValueError("Valid supported answer contradicts insufficient context/corpus")
        attempted.append(attempt)
        errors.append(and3(attempt, not3(quality)))
        unsupported.append(and3(attempt, not3(row["supported"])))
        valid.append(and3(row["corpus_supported"], attempt, quality))
        false_refusals.append(and3(row["context_sufficient"], refusal))
        corpus.append(row["corpus_supported"])
        sufficient.append(row["context_sufficient"])
        failed.append(error)
    all_questions = [True] * len(rows)
    return {
        "schema_version": "selective-semantic-v1",
        "n": len(rows),
        "scope": "Requires supplied semantic judgments; no automatic correctness claims",
        "metrics": {
            "answer_coverage": rate(attempted, all_questions),
            "selective_risk": rate(errors, attempted),
            "unsupported_answer_rate": rate(unsupported, all_questions),
            "end_to_end_valid_response_rate": rate(valid, corpus),
            "false_refusal_rate": rate(false_refusals, sufficient),
            "system_error_rate": rate(failed, all_questions),
        },
    }


def validate_group_split(records: list[dict]) -> None:
    legacy_ids = {f"q{i:03d}" for i in range(1, 31)}
    groups = {}
    ids = set()
    for row in records:
        qid, group, split = row["question_id"], row["group_id"], row["split"]
        if not all(isinstance(v, str) and v for v in (qid, group)) or qid in ids:
            raise ValueError("Missing group/ID or duplicate question")
        ids.add(qid)
        if split not in {"dev", "test"}:
            raise ValueError("Invalid split")
        if split == "test" and (qid in legacy_ids or row.get("previously_exposed") is not False):
            raise ValueError("Test questions require an explicit unexposed declaration")
        if group in groups and groups[group] != split:
            raise ValueError("A source group crosses dev/test")
        groups[group] = split


def select_working_point(candidates: list[dict], *, split: str, min_coverage: float = 0.5) -> dict:
    """Choose a development working point; never retune on a heldout split."""
    if split != "dev":
        raise ValueError("Threshold selection is development-only")
    if not 0 <= min_coverage <= 1:
        raise ValueError("Invalid coverage target")
    eligible = []
    for candidate in candidates:
        metrics = candidate["summary"]["metrics"]
        coverage, risk = metrics["answer_coverage"], metrics["selective_risk"]
        if coverage["missing_label_rows"] or risk["missing_label_rows"]:
            return {"status": "incomplete_annotations", "selected": None}
        if coverage["value"] is not None and coverage["value"] >= min_coverage and risk["value"] is not None:
            eligible.append(candidate)
    if not eligible:
        return {"status": "infeasible", "selected": None}

    def key(candidate):
        metrics = candidate["summary"]["metrics"]
        return (
            metrics["selective_risk"]["value"],
            -metrics["answer_coverage"]["value"],
            candidate["generation_call_n"],
            candidate["score_threshold"],
            candidate["lexical_threshold"],
        )

    return {"status": "selected_on_dev", "selected": min(eligible, key=key)}
