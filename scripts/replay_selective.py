"""Replay supplied baseline cache plus linked semantic reviews; never call a model."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.evaluation.replay import (  # noqa: E402
    LEXICAL_GRID,
    grouped_bootstrap,
    replay_development,
    replay_policy,
    score_grid,
)
from app.evaluation.selective import select_working_point, validate_group_split  # noqa: E402

PROTOCOL_VERSION = "selective-v0.2-dev"


def implementation_hashes():
    return {
        str(p.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (
            Path(__file__),
            ROOT / "backend/app/evaluation/replay.py",
            ROOT / "backend/app/evaluation/selective.py",
            ROOT / "backend/app/rag/gating.py",
        )
    }


def validate_development_report(dev):
    """Check internal selection consistency; this is not a signature or preregistration."""
    if dev.get("status") != "offline_development_replay" or dev.get("protocol_version") != PROTOCOL_VERSION:
        raise ValueError("Require a compatible development report")
    if dev.get("implementation_sha256") != implementation_hashes():
        raise ValueError("Development report implementation differs from current runner")
    split = dev.get("split_manifest")
    if not split or any(r["split"] != "dev" for r in split):
        raise ValueError("Development report requires a dev-only manifest")
    validate_group_split(split, enforce_assignment=True)
    ids = {r["question_id"] for r in split}
    events = dev["baseline"]["events"]
    if len(events) != len(ids) or {e["question_id"] for e in events} != ids:
        raise ValueError("Development baseline IDs differ from manifest")
    grid = score_grid([e["features"]["top_score"] for e in events], split="dev")
    if dev["score_grid"] != grid or dev["lexical_grid"] != list(LEXICAL_GRID):
        raise ValueError("Development candidate grid differs from its baseline")
    if type(dev.get("labels_complete")) is not bool:
        raise ValueError("Development report lacks label-completion declaration")
    for strategy in ("B", "C"):
        items = dev["candidates"][strategy]
        expected = [(t, u) for t in grid for u in ((0,) if strategy == "B" else LEXICAL_GRID)]
        actual = [(c["score_threshold"], c["lexical_threshold"]) for c in items]
        if actual != expected or any(c["strategy"] != strategy for c in items):
            raise ValueError("Development candidate set differs from declared grid")
        for c in items:
            candidate_events = c["events"]
            if len(candidate_events) != len(ids) or {e["question_id"] for e in candidate_events} != ids:
                raise ValueError("Development candidate IDs differ from manifest")
            if c["summary"]["n"] != len(ids) or c["generation_call_n"] != sum(
                e["allow_generation"] for e in candidate_events
            ):
                raise ValueError("Development candidate counts differ from events")
        for target in (0.5, 0.25, 0.75):
            selected = select_working_point(items, split="dev", min_coverage=target)
            if not dev["labels_complete"]:
                selected = {"status": "incomplete_annotations", "selected": None}
            if dev["selections"][strategy][str(target)] != selected:
                raise ValueError("Saved working point differs from deterministic development selection")


def digest(value):
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode(
            "utf-8"
        )
    ).hexdigest()


def load_rows(path):
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    ids = [r["question_id"] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate input question IDs")
    return {r["question_id"]: r for r in rows}


def join_inputs(cache, reviews, split):
    if not cache or cache.keys() != reviews.keys() or cache.keys() != split.keys():
        raise ValueError("Cache/review/split question IDs must match exactly")
    validate_group_split(list(split.values()), enforce_assignment=True)
    result = []
    for qid in sorted(cache):
        c, review = cache[qid], reviews[qid]
        for name in ("question", "prompt", "prompt_template", "provider", "replicate_id"):
            if not isinstance(c.get(name), str) or not c[name].strip():
                raise ValueError(f"Missing cache field: {name}")
        if c.get("requested_model") is not None and (
            not isinstance(c["requested_model"], str) or not c["requested_model"].strip()
        ):
            raise ValueError("Invalid requested model identity")
        if not isinstance(c.get("model"), str) or not c["model"].strip():
            if (
                c.get("execution_status") != "system_error"
                or not c.get("requested_model")
                or c.get("model") is not None
            ):
                raise ValueError("Returned model identity missing for successful/legacy cache")
        for name in ("decoding", "retrieval", "corpus_hashes"):
            if not isinstance(c.get(name), dict) or not c[name]:
                raise ValueError(f"Missing cache configuration: {name}")
        if c["retrieval"].get("method") != "bm25" or c["retrieval"].get("top_k") != 5:
            raise ValueError("Replay requires BM25 Top-5 cache")
        if c["execution_status"] not in {"ok", "system_error"} or not isinstance(c["response"], str):
            raise ValueError("Invalid baseline execution/response")
        if c["execution_status"] == "ok" and not c["response"].strip():
            raise ValueError("Successful cache response cannot be empty")
        context_hash = digest(c["chunks"])
        response_hash = hashlib.sha256(c["response"].encode("utf-8")).hexdigest()
        if (
            review.get("cache_sha256") != digest(c)
            or review.get("context_sha256") != context_hash
            or review.get("response_sha256") != response_hash
        ):
            raise ValueError("Review does not match exact cache/context/response")
        for name in ("reviewer_id", "reviewer_type", "reviewed_at", "rubric_version", "rationale"):
            if not isinstance(review.get(name), str) or not review[name].strip():
                raise ValueError(f"Missing review provenance: {name}")
        if review["rubric_version"] != PROTOCOL_VERSION:
            raise ValueError("Review rubric version differs from current protocol")
        if review["labels"]["execution_status"] != c["execution_status"]:
            raise ValueError("Review execution status differs from baseline")
        result.append(
            {
                **split[qid],
                "question": c["question"],
                "chunks": c["chunks"],
                "expected_behavior": review["expected_behavior"],
                "judgment": review["labels"],
            }
        )
    return result


def generation_config(cache):
    rows = list(cache.values())
    if not rows:
        raise ValueError("Empty generation cache")
    requested = [
        {
            **{
                k: r[k]
                for k in (
                    "provider",
                    "prompt_template",
                    "decoding",
                    "retrieval",
                    "corpus_hashes",
                    "replicate_id",
                )
            },
            "model": r.get("requested_model", r["model"]),
            "endpoint": r.get("endpoint"),
        }
        for r in rows
    ]
    if any(r != requested[0] for r in requested):
        raise ValueError("All cached rows must share a generation configuration")
    observed = {r["model"] for r in rows if r["execution_status"] == "ok"}
    if len(observed) > 1 or None in observed:
        raise ValueError("Returned model identity changed or is missing")
    return {"request": requested[0], "returned_model": next(iter(observed), None)}


def check_generation_config(dev, current):
    saved = dev.get("generation_config")
    if not saved or digest(saved) != dev.get("generation_config_sha256"):
        raise ValueError("Missing/inconsistent saved generation configuration")
    if saved["request"] != current["request"] or (
        saved["returned_model"] is not None
        and current["returned_model"] is not None
        and saved["returned_model"] != current["returned_model"]
    ):
        raise ValueError("Heldout generation configuration differs from development")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("cache", "reviews", "split", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--mode", choices=("dev", "test"), default="dev")
    parser.add_argument("--working-points", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Use a new output path")
    paths = {name: getattr(args, name) for name in ("cache", "reviews", "split")}
    rows = join_inputs(*(load_rows(paths[name]) for name in ("cache", "reviews", "split")))
    if any(r["split"] != args.mode for r in rows):
        raise ValueError("Input split differs from requested mode")
    if args.mode == "dev":
        if args.working_points:
            raise ValueError("Dev mode does not consume heldout working points")
        report = replay_development(rows)
    else:
        if not args.working_points:
            raise ValueError("Heldout replay requires saved dev working points")
        paths["working_points"] = args.working_points
        dev = json.loads(args.working_points.read_text(encoding="utf-8"))
        validate_development_report(dev)

        check_generation_config(dev, generation_config(load_rows(args.cache)))
        dev_split = dev.get("split_manifest")
        if not dev_split:
            raise ValueError("Development report lacks split provenance")
        dev_ids = {r["question_id"] for r in dev_split}
        dev_groups = {r["group_id"] for r in dev_split}
        if any(r["question_id"] in dev_ids or r["group_id"] in dev_groups for r in rows):
            raise ValueError("Heldout IDs/groups overlap development")
        outcomes, scored = {}, {}
        outcomes["A"], scored["A"] = replay_policy(rows, strategy="A")
        for strategy in ("B", "C"):
            choice = dev["selections"][strategy]["0.5"]
            if choice["status"] != "selected_on_dev":
                outcomes[strategy] = {"status": "no_development_working_point"}
                continue
            point = choice["selected"]
            outcomes[strategy], scored[strategy] = replay_policy(
                rows,
                strategy=strategy,
                score_threshold=point["score_threshold"],
                lexical_threshold=point["lexical_threshold"],
            )
        report = {
            "status": "offline_heldout_replay",
            "remote_calls": 0,
            "outcomes": outcomes,
            "bootstrap": grouped_bootstrap(scored),
        }
    config = generation_config(load_rows(args.cache))
    report["split_manifest"] = list(load_rows(args.split).values())
    report["protocol_version"] = PROTOCOL_VERSION
    report["implementation_sha256"] = implementation_hashes()
    report["generation_config"] = config
    report["generation_config_sha256"] = digest(config)
    report["inputs_sha256"] = {
        name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in paths.items()
    }
    report["review_scope"] = (
        "Metadata linkage checked; reviewer independence and semantic accuracy not certified"
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(f"Wrote {args.output}; zero remote calls")


if __name__ == "__main__":
    main()
