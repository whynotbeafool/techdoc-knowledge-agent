import importlib.util
import json
from unittest.mock import MagicMock

import pytest
from app.evaluation.dataset import validate_qa_dataset
from app.evaluation.generation import build_generation_summary, join_retrieval_metrics
from app.evaluation.integrity import ROOT, verify_auxiliary_inputs, verify_frozen_qa
from app.evaluation.retrieval import BM25Retriever
from app.rag.chunker import Chunk
from app.rag.generator import build_context
from app.rag.retriever import ChromaRetriever, _chunk_metadata
from app.rag.uploads import upload_destination


def load_rows(path):
    return [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines() if s.strip()]


def test_real_frozen_qa_and_auxiliary_inputs():
    verify_frozen_qa(ROOT / "data/eval/qa.jsonl")
    verify_auxiliary_inputs()
    assert not [
        x
        for x in validate_qa_dataset(ROOT / "data/eval/qa.jsonl", ROOT / "data/corpus")
        if x.severity == "error"
    ]


def test_exact_legacy_newline_variant_allowed_but_modified_gold_rejected(tmp_path):
    data = (ROOT / "data/eval/qa.jsonl").read_bytes().replace(b"\r\n", b"\n")
    path = tmp_path / "qa.jsonl"
    path.write_bytes(data)
    assert verify_frozen_qa(path)["legacy_lf_serialization"]
    path.write_bytes(data + b"\n")
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_frozen_qa(path)


def test_historical_conditioning_and_scores():
    gen = load_rows(ROOT / "results/generation/frozen-30-bm25-deepseek-v1.jsonl")
    retrieval = load_rows(ROOT / "results/runs/frozen-30-v1.jsonl")
    joined = join_retrieval_metrics(gen, retrieval)
    summary = build_generation_summary(joined, run_id="check")
    assert [c["n"] for c in summary["retrieval_conditioned_cells"]] == [15, 9, 14, 9]
    assert summary["retrieval_conditioning_missing_n"] == 0
    assert all("retrieval_metrics" not in row for row in gen)
    assert build_generation_summary(gen, run_id="check")["retrieval_conditioning_missing_n"] == 24
    old = json.loads((ROOT / "results/generation/frozen-30-bm25-deepseek-v1.summary.json").read_text())
    assert summary["cells"] == old["cells"]


@pytest.mark.parametrize("failure", ["wrong_run", "wrong_chunks", "duplicate", "missing", "conflict"])
def test_join_rejects_wrong_provenance(failure):
    gen = load_rows(ROOT / "results/generation/frozen-30-bm25-deepseek-v1.jsonl")
    retrieval = load_rows(ROOT / "results/runs/frozen-30-v1.jsonl")
    if failure == "wrong_run":
        gen[0]["retrieval_run_id"] = "another-run"
    elif failure == "wrong_chunks":
        gen[0]["retrieved"] = []
    elif failure == "duplicate":
        retrieval.append(retrieval[0])
    elif failure == "missing":
        retrieval = []
    else:
        gen[0]["retrieval_metrics"] = {"complete_evidence_hit_at_5": "unknown"}
    with pytest.raises(ValueError):
        join_retrieval_metrics(gen, retrieval)


@pytest.mark.parametrize("page", [None, 0, -1])
def test_missing_page_never_rendered_as_real_page(page):
    context = build_context([{"source": "notes.md", "page": page, "chunk_id": "x", "text": "body"}])
    assert "页码不适用" in context
    assert "第None页" not in context and "第0页" not in context
    assert "notes.md" in context and "body" in context


def test_missing_page_key_and_positive_pdf_page():
    assert "页码不适用" in build_context([{"source": "x.txt", "chunk_id": "x", "text": "a"}])
    assert "第3页" in build_context([{"source": "x.pdf", "page": 3, "chunk_id": "x", "text": "a"}])
    chunk = Chunk(chunk_id="x", source="x.txt", page=None, text="body", start_char=0, end_char=4)
    assert "page" not in _chunk_metadata(chunk)


def test_old_zero_metadata_remains_readable_and_resources_close_on_failure():
    retriever = object.__new__(ChromaRetriever)
    retriever.client = MagicMock()
    retriever.query = MagicMock(
        return_value={
            "ids": [["x"]],
            "documents": [["body"]],
            "metadatas": [[{"source": "x.txt", "page": 0}]],
            "distances": [[0.1]],
        }
    )
    assert retriever.query_chunks("x")[0]["page"] is None
    with pytest.raises(RuntimeError), retriever:
        raise RuntimeError("downstream failure")
    retriever.client.close.assert_called_once()


@pytest.mark.parametrize(
    "name", ["../a.txt", r"..\a.txt", "/a.txt", "C:a.txt", "a.txt:evil", "CON.txt", "a.txt.", "a.exe"]
)
def test_upload_rejects_unsafe_names(tmp_path, name):
    with pytest.raises(ValueError):
        upload_destination(tmp_path, name)


def test_upload_accepts_unicode_basename(tmp_path):
    assert upload_destination(tmp_path, "技术说明.md") == tmp_path / "技术说明.md"


@pytest.mark.parametrize("k", [-1, 0])
def test_bm25_nonpositive_k_is_empty(k):
    chunk = Chunk(chunk_id="x", source="x.txt", page=None, text="body", start_char=0, end_char=4)
    assert BM25Retriever([chunk]).query_chunks("body", k) == []


def test_postlock_checker_accepts_archive_and_rejects_mutated_review(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "locked_check", ROOT / "scripts/check_locked_reannotation.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Exercise mutation detection without rewriting the archive.
    original = module.digest
    target = ROOT / "data/eval/reannotation-20260923/semantic-review.json"
    monkeypatch.setattr(module, "digest", lambda path: "0" * 64 if path == target else original(path))
    monkeypatch.setattr(
        module.sys,
        "argv",
        ["check", "--packet", str(target.parent / "input"), "--output-dir", str(target.parent)],
    )
    with pytest.raises(ValueError, match="Post-lock review hash mismatch"):
        module.main()
