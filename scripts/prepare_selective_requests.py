"""Build draft request/review inputs from verified dev preflight; never call an API."""

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.corpus import load_active_revision_records, load_canonical_document  # noqa: E402
from app.evaluation.retrieval import BM25Retriever  # noqa: E402
from app.evaluation.selective import validate_group_split  # noqa: E402
from app.rag.chunker import chunk_canonical_document  # noqa: E402
from app.rag.gating import ContextChunk, runtime_features  # noqa: E402
from app.rag.generator import SYSTEM_PROMPT, build_context  # noqa: E402

INPUTS = ("public-questions.jsonl", "runtime-features.jsonl", "split.jsonl")
USER_TEMPLATE = "资料：\n{context}\n\n问题：{question}"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def content_hash(value):
    return sha(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode(
            "utf-8"
        )
    )


def read_rows(path):
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    ids = [r["question_id"] for r in rows]
    if not ids or any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != len(ids):
        raise ValueError("Expected nonempty unique question IDs")
    return {r["question_id"]: r for r in rows}


def verify_ranked_context(actual, recorded):
    """Allow numerical recomputation noise only; identity, order and text stay exact."""
    if len(actual) != len(recorded):
        raise ValueError("Preflight ranking length differs")
    for current, saved in zip(actual, recorded):
        if {k: v for k, v in current.items() if k != "score"} != {
            k: v for k, v in saved.items() if k != "score"
        }:
            raise ValueError("Preflight ranking/text/coordinates no longer reproduce")
        a, b = current.get("score"), saved.get("score")
        if any(type(v) not in (float, int) or not math.isfinite(v) for v in (a, b)) or not math.isclose(
            a, b, rel_tol=1e-12, abs_tol=1e-12
        ):
            raise ValueError("Preflight score differs beyond numerical tolerance")


def prepare(preflight, corpus):
    manifest = json.loads((preflight / "manifest.json").read_text(encoding="utf-8"))
    if (
        manifest.get("status") != "features_only_no_generation"
        or manifest.get("method") != "bm25"
        or manifest.get("top_k") != 5
        or manifest.get("chunk_size") != 800
    ):
        raise ValueError("Require the BM25 Top-5 / 800-character dev preflight")
    for name in INPUTS:
        if sha((preflight / name).read_bytes()) != manifest["sha256"][name]:
            raise ValueError(f"Preflight input hash mismatch: {name}")
    public, features, split = (read_rows(preflight / name) for name in INPUTS)
    if (
        public.keys() != features.keys()
        or public.keys() != split.keys()
        or len(public) != manifest["question_n"]
    ):
        raise ValueError("Preflight question sets/counts differ")
    if any(set(row) != {"question_id", "question"} for row in public.values()):
        raise ValueError("Public questions must contain only ID and question")
    validate_group_split(list(split.values()), enforce_assignment=True)
    if any(r["split"] != "dev" for r in split.values()):
        raise ValueError("This request preparation is dev-only")
    active = load_active_revision_records(corpus)

    def projection(row):
        return {k: row[k] for k in ("document_id", "revision", "text_hash")}

    if [projection(r) for r in active] != manifest["corpus"]:
        raise ValueError("Active corpus differs from preflight")
    chunks = []
    for record in active:
        document = load_canonical_document(
            corpus, document_id=record["document_id"], revision=record["revision"]
        )
        chunks.extend(chunk_canonical_document(document, max_chars=800))
    if len(chunks) != manifest["chunk_n"]:
        raise ValueError("Chunk count differs from preflight")
    retriever = BM25Retriever(chunks)
    requests, review_tasks = [], []
    template = json.dumps(
        {"system": SYSTEM_PROMPT, "user": USER_TEMPLATE}, ensure_ascii=False, sort_keys=True
    )
    for qid, question in public.items():
        recorded = features[qid]
        if question["question"] != recorded["question"]:
            raise ValueError("Public question differs from feature input")
        retrieved = retriever.query_chunks(question["question"], top_k=5)
        verify_ranked_context(retrieved, recorded["retrieved"])
        # Preserve the frozen score identity for context hashes and threshold ties.
        retrieved = recorded["retrieved"]
        context_chunks = [{"text": c["text"], "score": c["score"]} for c in retrieved]
        actual_features = runtime_features(question["question"], [ContextChunk(**c) for c in context_chunks])
        if actual_features != recorded["features"]:
            raise ValueError("Runtime features differ from verified context")
        user = USER_TEMPLATE.format(context=build_context(retrieved), question=question["question"])
        messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}]
        prompt = json.dumps(messages, ensure_ascii=False, separators=(",", ":"))
        intervals = [
            {
                k: c[k]
                for k in ("chunk_id", "document_id", "revision", "start_char", "end_char", "source", "page")
            }
            for c in retrieved
        ]
        request = {
            **question,
            "status": "draft_request_not_executed",
            "chunks": context_chunks,
            "retained_intervals": intervals,
            "messages": messages,
            "prompt": prompt,
            "prompt_template": template,
            "context_sha256": content_hash(context_chunks),
            "messages_sha256": content_hash(messages),
            "prompt_sha256": sha(prompt.encode("utf-8")),
            "provider": None,
            "model": None,
            "replicate_id": "0",
            "decoding_proposal": {"temperature": 0.2, "max_tokens": 512},
            "retrieval": {"method": "bm25", "top_k": 5, "chunk_size": 800, "k1": 1.5, "b": 0.75},
            "corpus_hashes": {r["document_id"] + "@" + r["revision"]: r["text_hash"] for r in active},
            "prompt_character_n": sum(len(m["content"]) for m in messages),
            "token_count": None,
            "token_count_status": "provider_tokenizer_and_chat_overhead_unverified",
        }
        requests.append(request)
        # No scores, gates, prior answers, historical targets or semantic labels are supplied.
        review_tasks.append(
            {
                **question,
                "scope": "exposed_dev_pre_generation_review_not_independent_blind_annotation",
                "generator_visible_messages": messages,
                "request_sha256": content_hash(request),
                "required_facts": None,
                "corpus_supported": None,
                "context_sufficient": None,
                "reviewer_id": None,
                "reviewer_type": None,
                "rationale": None,
            }
        )
    return requests, review_tasks, list(split.values())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, default=ROOT / "data/corpus")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise ValueError("Use a new output directory")
    requests, reviews, split = prepare(args.preflight, args.corpus)
    args.output_dir.mkdir(parents=True)
    for name, rows in (
        ("requests.jsonl", requests),
        ("context-review-tasks.jsonl", reviews),
        ("split.jsonl", split),
    ):
        with (args.output_dir / name).open("x", encoding="utf-8", newline="\n") as stream:
            for row in rows:
                stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
    sources = [
        Path(__file__),
        ROOT / "backend/app/rag/generator.py",
        ROOT / "backend/app/rag/citations.py",
        ROOT / "backend/app/core/response_contract.py",
        ROOT / "backend/app/rag/gating.py",
        ROOT / "backend/app/rag/chunker.py",
        ROOT / "backend/app/evaluation/retrieval.py",
    ]
    manifest = {
        "schema_version": "selective-request-draft-v1",
        "status": "not_ready_for_paid_generation",
        "protocol_version": "selective-v0.2-dev",
        "question_n": len(requests),
        "remote_calls": 0,
        "semantic_labels": 0,
        "approved_remote_calls": 0,
        "provider": None,
        "model": None,
        "proposed_max_input_tokens": 4096,
        "proposed_max_output_tokens": 512,
        "token_counts_verified": False,
        "cost_estimate": None,
        "prompt_character_range": [
            min(r["prompt_character_n"] for r in requests),
            max(r["prompt_character_n"] for r in requests),
        ],
        "preflight_manifest_sha256": sha((args.preflight / "manifest.json").read_bytes()),
        "inputs_sha256": {name: sha((args.preflight / name).read_bytes()) for name in INPUTS},
        "outputs_sha256": {p.name: sha(p.read_bytes()) for p in sorted(args.output_dir.glob("*.jsonl"))},
        "source_hash_policy": "CRLF-to-LF normalized source bytes",
        "source_sha256": {
            p.relative_to(ROOT).as_posix(): sha(p.read_bytes().replace(b"\r\n", b"\n")) for p in sources
        },
        "blockers": [
            "provider/model and price selection",
            "real tokenizer including message overhead",
            "explicit generation budget",
            "corpus/context review",
            "response logging adapter",
        ],
        "scope": "Draft requests and empty review tasks; not a response cache or new annotation.",
    }
    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"Prepared {len(requests)} draft requests and empty review tasks; zero API calls")


if __name__ == "__main__":
    main()
