"""Run the specifically authorized 30-question DeepSeek pilot; offline by default."""

import argparse
import hashlib
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.evaluation.collection import ResponseCollector, digest  # noqa: E402
from app.evaluation.deepseek_transport import DeepSeekTransport  # noqa: E402

REVIEW = Path("results/selective/pre-generation-review-20261004")
OUTPUT = Path("results/selective/deepseek-pilot-20261004")
JOURNAL = Path(".venv/selective-generation-20261004/run.sqlite")


def read_rows(path):
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    if len({r["question_id"] for r in rows}) != len(rows):
        raise ValueError("Duplicate question IDs")
    return {r["question_id"]: r for r in rows}


def prepare(root=ROOT):
    lock = json.loads((root / REVIEW / "LOCK.json").read_text(encoding="utf-8"))
    if lock["status"] != "pre_generation_AI_exposed_dev_review_locked" or lock["question_n"] != 30:
        raise ValueError("Require the completed pilot pre-generation review")
    for name, expected in lock["sha256"].items():
        path = (root / name).resolve()
        if (
            not path.is_relative_to(root.resolve())
            or hashlib.sha256(path.read_bytes()).hexdigest() != expected
        ):
            raise ValueError("Locked input changed")
    requests = read_rows(root / "results/selective/request-draft-20260930/requests.jsonl")
    checks = read_rows(root / "results/selective/token-preflight-20261004/token-checks.jsonl")
    corpus = read_rows(root / REVIEW / "corpus-review.jsonl")
    reviews = read_rows(root / REVIEW / "context-review.jsonl")
    ids = {f"q{i:03}" for i in range(1, 31)}
    if any(set(rows) != ids for rows in (requests, checks, corpus, reviews)):
        raise ValueError("Pilot IDs differ")
    for qid, request in requests.items():
        review, check = reviews[qid], checks[qid]
        if (
            review["request_sha256"] != digest(request)
            or review["corpus_review_sha256"] != digest(corpus[qid])
            or review["context_sha256"] != digest(request["chunks"])
            or review["stage"] != "context_before_generation"
            or check["request_sha256"] != digest(request)
            or check["requested_model"] != "deepseek-flash"
            or check["thinking"] != "disabled"
        ):
            raise ValueError("Review/token/request binding differs")
    tokenizer_ids = {r["tokenizer_id"] for r in checks.values()}
    if len(tokenizer_ids) != 1:
        raise ValueError("Mixed tokenizers")
    config = dict(
        provider="deepseek",
        requested_model="deepseek-flash",
        endpoint="https://api.deepseek.com",
        approval_reference="user-delegated-budget-20261004-CNY1-30calls",
        tokenizer_id=next(iter(tokenizer_ids)),
        max_calls=30,
        max_input_tokens=4096,
        max_output_tokens=512,
        temperature=0.2,
        thinking="disabled",
        currency="CNY",
        input_price_per_million="2",
        output_price_per_million="8",
        cost_limit="1",
        price_reference="https://api-docs.deepseek.com/zh-cn/quick_start/pricing/;verified-20261004",
    )
    return requests, checks, config, lock


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--max-new-calls", type=int, default=1)
    args = parser.parse_args()
    if not 1 <= args.max_new_calls <= 30:
        parser.error("max-new-calls must be between 1 and 30")
    requests, checks, config, lock = prepare()
    if not args.execute:
        print(json.dumps({"status": "offline_preflight_passed", "requests": len(requests), "calls": 0}))
        return
    from dotenv import dotenv_values

    key = os.environ.get("DEEPSEEK_API_KEY") or dotenv_values(ROOT / ".env").get("DEEPSEEK_API_KEY")
    if not key:
        raise ValueError("DeepSeek credential is not configured")
    output = ROOT / OUTPUT
    output.mkdir(parents=True, exist_ok=True)
    binding = {"config": config, "pre_generation_lock_sha256": digest(lock)}
    manifest_path = output / "run-manifest.json"
    if manifest_path.exists():
        if not (ROOT / JOURNAL).exists():
            raise RuntimeError("Existing run lost its journal; cannot reset the authorized budget")
        saved = json.loads(manifest_path.read_text(encoding="utf-8"))
        if saved["binding"] != binding:
            raise ValueError("Run binding changed; no calls allowed")
    else:
        saved = {
            "binding": binding,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "scope": "AI-reviewed exposed development pilot; not heldout evidence",
            "implementation_sha256": {
                name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                for name in (
                    "scripts/collect_selective_pilot.py",
                    "backend/app/evaluation/collection.py",
                    "backend/app/evaluation/deepseek_transport.py",
                )
            },
        }
        with manifest_path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(saved, ensure_ascii=False, indent=2) + "\n")
    for name, sha in saved["implementation_sha256"].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != sha:
            raise ValueError("Collection implementation changed during run")
    # The journal is fixed for this authorization. Never change it to retry a failure.
    transport = DeepSeekTransport(key)
    try:
        collector = ResponseCollector(ROOT / JOURNAL, config, transport)
        with collector.connect() as db:
            previous = dict(db.execute("SELECT question_id,result_json FROM attempts"))
        if any(value is None for value in previous.values()):
            raise RuntimeError("Unresolved prior call; no automatic retry")
        if any(json.loads(value)["execution_status"] != "ok" for value in previous.values()):
            raise RuntimeError("Prior service failure; inspect before continuing; never retry it")
        observed_models = {json.loads(value)["model"] for value in previous.values()}
        if len(observed_models) > 1 or None in observed_models:
            raise RuntimeError("Returned model identity missing or changed; inspect run")
        new_n = 0
        for qid in sorted(requests):
            if qid in previous:
                continue
            row = collector.collect(requests[qid], checks[qid])
            new_n += 1
            observed_models.add(row["model"])
            print(
                json.dumps(
                    {
                        k: row[k]
                        for k in (
                            "question_id",
                            "execution_status",
                            "model",
                            "usage",
                            "finish_reason",
                            "cost_estimate",
                            "error_type",
                        )
                    }
                ),
                flush=True,
            )
            with collector.connect() as db:
                halted = db.execute("SELECT value FROM metadata WHERE key='halt_reason'").fetchone()
            if (
                row["execution_status"] != "ok"
                or halted
                or len(observed_models) > 1
                or new_n >= args.max_new_calls
            ):
                break
        with collector.connect() as db:
            count = db.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]
        snapshot = output / f"cache-{count:02}.jsonl"
        if not snapshot.exists():
            collector.export_cache(snapshot)
    finally:
        transport.close()


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, sqlite3.Error) as exc:
        # These are locally generated validation errors; provider errors are sanitized by the collector.
        raise SystemExit(str(exc)) from None
