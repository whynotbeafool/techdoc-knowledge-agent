"""Build prospective groups from declared facts and ancestry, not model outputs.

This validates graph mechanics only. Fact identity and missing semantic links
still require review before the manifest is frozen.
"""

import hashlib
import json

from app.evaluation.selective import group_split, validate_group_split


def build_groups(records: list[dict]) -> list[dict]:
    """Propagate exposure through shared facts, ancestry and prior groups.

    Every row declares question_id, necessary_fact_ids, parent_question_ids,
    previously_exposed and prior_group_id (null for new questions). Include
    ancestor rows, even if they will not be part of a future evaluation.
    """
    rows = {}
    for row in records:
        qid = row["question_id"]
        if not isinstance(qid, str) or not qid.strip() or qid in rows:
            raise ValueError("Question IDs must be nonempty and unique")
        if type(row["previously_exposed"]) is not bool:
            raise ValueError("Explicit exposure required")
        for field in ("necessary_fact_ids", "parent_question_ids"):
            values = row[field]
            if not isinstance(values, list) or any(
                not isinstance(value, str) or not value.strip() for value in values
            ) or len(values) != len(set(values)):
                raise ValueError("Fact and parent IDs must be unique nonempty strings")
        if not row["necessary_fact_ids"]:
            raise ValueError("At least one declared necessary fact required")
        prior = row["prior_group_id"]
        if prior is not None and (not isinstance(prior, str) or not prior.strip()):
            raise ValueError("Prior group must be null or a nonempty string")
        rows[qid] = row

    roots = {qid: qid for qid in rows}

    def root(qid):
        while roots[qid] != qid:
            roots[qid] = roots[roots[qid]]
            qid = roots[qid]
        return qid

    def join(left, right):
        roots[root(left)] = root(right)

    owners = {}
    legacy_ids = {f"q{i:03d}" for i in range(1, 31)}
    for qid, row in rows.items():
        for parent in row["parent_question_ids"]:
            if parent not in rows or parent == qid:
                raise ValueError("Parent must reference another included question")
            join(qid, parent)
        keys = [("fact", fact) for fact in row["necessary_fact_ids"]]
        if row["prior_group_id"] is not None:
            keys.append(("prior", row["prior_group_id"]))
        if qid in legacy_ids or row["prior_group_id"] == "legacy-exposed-30":
            keys.append(("prior", "legacy-exposed-30"))
        for key in keys:
            if key in owners:
                join(qid, owners[key])
            else:
                owners[key] = qid

    components = {}
    for qid in rows:
        components.setdefault(root(qid), []).append(qid)
    output = []
    for members in components.values():
        members.sort()
        legacy = any(
            qid in legacy_ids or rows[qid]["prior_group_id"] == "legacy-exposed-30"
            for qid in members
        )
        exposed = legacy or any(rows[qid]["previously_exposed"] for qid in members)
        payload = json.dumps(members, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        group = "legacy-exposed-30" if legacy else "facts-" + hashlib.sha256(payload).hexdigest()
        for qid in members:
            output.append({
                "question_id": qid,
                "group_id": group,
                "previously_exposed": rows[qid]["previously_exposed"] or qid in legacy_ids,
                "group_previously_exposed": exposed,
                "split": group_split(group, previously_exposed=exposed),
            })
    output.sort(key=lambda row: row["question_id"])
    validate_group_split(output, enforce_assignment=True)
    return output
