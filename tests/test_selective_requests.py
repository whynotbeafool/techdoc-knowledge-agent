import importlib.util
import json
import math
import shutil
from pathlib import Path

import pytest
from app.rag import generator

ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT = ROOT / "results/selective/dev-preflight-20260929"


def module():
    spec = importlib.util.spec_from_file_location(
        "prepare_requests", ROOT / "scripts/prepare_selective_requests.py"
    )
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def test_real_requests_reproduce_prompts_without_api_or_labels(monkeypatch):
    tool = module()

    def forbidden(*args, **kwargs):
        raise AssertionError("Offline preparation must not initialize an API client")

    monkeypatch.setattr(generator, "OpenAI", forbidden)
    monkeypatch.setattr(generator, "get_llm_config", forbidden)
    requests, reviews, split = tool.prepare(PREFLIGHT, ROOT / "data/corpus")
    assert len(requests) == len(reviews) == len(split) == 30
    original = tool.read_rows(PREFLIGHT / "runtime-features.jsonl")
    for request, review in zip(requests, reviews):
        qid = request["question_id"]
        expected = generator.build_context(original[qid]["retrieved"])
        assert request["messages"][1]["content"] == f"资料：\n{expected}\n\n问题：{request['question']}"
        assert json.loads(request["prompt"]) == request["messages"]
        assert request["context_sha256"] == tool.content_hash(request["chunks"])
        assert review["request_sha256"] == tool.content_hash(request)
        assert review["generator_visible_messages"] == request["messages"]
        assert request["model"] is None and request["token_count"] is None
        assert review["required_facts"] is review["corpus_supported"] is review["context_sufficient"] is None
        assert not {"score", "features", "expected_behavior", "reference_answer", "strategy"} & review.keys()
        assert "response" not in request and "execution_status" not in request
        assert len(request["chunks"]) == len(request["retained_intervals"]) == 5


@pytest.mark.parametrize("mutation", ["hash", "question", "retrieval", "labels", "corpus"])
def test_preflight_inconsistencies_fail_before_output(tmp_path, mutation):
    tool = module()
    directory = tmp_path / "preflight"
    shutil.copytree(PREFLIGHT, directory)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    name = "runtime-features.jsonl"
    if mutation == "labels":
        name = "public-questions.jsonl"
    rows = [json.loads(line) for line in (directory / name).read_text(encoding="utf-8").splitlines()]
    if mutation in {"hash", "question"}:
        rows[0]["question"] = "changed question"
    elif mutation == "retrieval":
        rows[0]["retrieved"][0]["text"] = "changed context"
    elif mutation == "labels":
        rows[0]["reference_answer"] = "forbidden field"
    elif mutation == "corpus":
        manifest["corpus"][0]["revision"] = "wrong"
    (directory / name).write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8", newline="\n")
    if mutation != "hash":
        manifest["sha256"][name] = tool.sha((directory / name).read_bytes())
    (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError):
        tool.prepare(directory, ROOT / "data/corpus")


def test_cli_provenance_and_no_overwrite(tmp_path, monkeypatch):
    tool = module()
    output = tmp_path / "packet"
    monkeypatch.setattr(
        tool.sys, "argv", ["prepare", "--preflight", str(PREFLIGHT), "--output-dir", str(output)]
    )
    tool.main()
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["remote_calls"] == manifest["approved_remote_calls"] == manifest["semantic_labels"] == 0
    assert manifest["token_counts_verified"] is False and manifest["cost_estimate"] is None
    for name, expected in manifest["outputs_sha256"].items():
        assert tool.sha((output / name).read_bytes()) == expected
    for name, expected in manifest["source_sha256"].items():
        assert tool.sha((ROOT / name).read_bytes().replace(b"\r\n", b"\n")) == expected
    with pytest.raises(ValueError, match="new output"):
        tool.main()


@pytest.mark.parametrize("change", ["text", "coordinate", "rank", "score", "nan", "bool"])
def test_recomputation_tolerance_never_accepts_material_changes(change):
    tool = module()
    saved = [
        {"chunk_id": "a", "text": "a", "start_char": 0, "score": 2.0},
        {"chunk_id": "b", "text": "b", "start_char": 1, "score": 1.0},
    ]
    actual = json.loads(json.dumps(saved))
    if change == "text":
        actual[0]["text"] = "changed"
    elif change == "coordinate":
        actual[0]["start_char"] = 1
    elif change == "rank":
        actual.reverse()
    elif change == "score":
        actual[0]["score"] += 1e-6
    elif change == "nan":
        actual[0]["score"] = float("nan")
    elif change == "bool":
        actual[0]["score"] = True
    with pytest.raises(ValueError):
        tool.verify_ranked_context(actual, saved)


def test_recomputed_float_noise_preserves_saved_scores_and_hashes(monkeypatch):
    tool = module()
    original = tool.BM25Retriever.query_chunks

    def perturbed(self, *args, **kwargs):
        rows = original(self, *args, **kwargs)
        for row in rows:
            row["score"] = math.nextafter(row["score"], math.inf)
        return rows

    monkeypatch.setattr(tool.BM25Retriever, "query_chunks", perturbed)
    requests, _, _ = tool.prepare(PREFLIGHT, ROOT / "data/corpus")
    saved = tool.read_rows(ROOT / "results/selective/request-draft-20260930/requests.jsonl")
    assert requests == list(saved.values())
