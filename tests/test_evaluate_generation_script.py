import importlib.util
import json
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "evaluate_generation.py"
SPEC = importlib.util.spec_from_file_location("evaluate_generation_script", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def _qa_record(question_id="q021"):
    return {
        "question_id": question_id,
        "question": "What is the undocumented latency?",
        "annotation_status": "confirmed",
        "expected_behavior": "refuse",
        "reasoning_type": "not_applicable",
    }


def _retrieval_row(question_id="q021"):
    return {
        "run_id": "retrieval-v1",
        "method": "bm25",
        "question_id": question_id,
        "retrieved": [
            {
                "chunk_id": "guide.md_p0_0",
                "document_id": "guide",
                "revision": "v1",
                "start_char": 0,
                "end_char": 12,
            }
        ],
    }


def test_select_retrieval_rows_requires_exactly_one_row_per_question():
    qa_records = [_qa_record("q021"), _qa_record("q022")]

    try:
        MODULE._select_retrieval_rows([_retrieval_row("q021")], qa_records, "bm25")
    except ValueError as exc:
        assert "missing=['q022']" in str(exc)
    else:
        raise AssertionError("Expected a missing retrieval row to fail")


def test_rehydrate_chunks_uses_verified_canonical_offsets(monkeypatch, tmp_path):
    document = type(
        "Document",
        (),
        {
            "text": "evidence text",
            "metadata": {"source_file": "guide.md"},
        },
    )()
    monkeypatch.setattr(MODULE, "load_canonical_document", lambda *args, **kwargs: document)

    chunks = MODULE._rehydrate_chunks(
        _retrieval_row()["retrieved"],
        corpus_dir=tmp_path,
        document_cache={},
    )

    assert chunks == [
        {
            "chunk_id": "guide.md_p0_0",
            "source": "guide.md",
            "page": None,
            "text": "evidence tex",
            "document_id": "guide",
            "revision": "v1",
            "start_char": 0,
            "end_char": 12,
        }
    ]


def test_main_writes_immutable_generation_artifacts_without_secrets(
    monkeypatch, tmp_path, capsys
):
    qa_path = tmp_path / "qa.jsonl"
    retrieval_path = tmp_path / "retrieval.jsonl"
    results_dir = tmp_path / "generation"
    qa_path.write_text(json.dumps(_qa_record()) + "\n", encoding="utf-8")
    retrieval_path.write_text(json.dumps(_retrieval_row()) + "\n", encoding="utf-8")

    monkeypatch.setattr(MODULE, "validate_qa_dataset", lambda *args: [])
    monkeypatch.setattr(
        MODULE,
        "get_llm_config",
        lambda: {
            "provider": "deepseek",
            "model": "test-model",
            "base_url": "https://example.test",
            "api_key": "must-not-be-written",
        },
    )
    monkeypatch.setattr(
        MODULE,
        "_rehydrate_chunks",
        lambda *args, **kwargs: [{"chunk_id": "x", "source": "guide", "page": None, "text": "x"}],
    )
    monkeypatch.setattr(
        MODULE,
        "generate_answer",
        lambda question, chunks: "当前资料依据不足。",
    )
    monkeypatch.setattr(
        MODULE.sys,
        "argv",
        [
            str(SCRIPT_PATH),
            "--run-id",
            "generation-v1",
            "--method",
            "bm25",
            "--qa",
            str(qa_path),
            "--retrieval-run",
            str(retrieval_path),
            "--corpus-dir",
            str(tmp_path / "corpus"),
            "--results-dir",
            str(results_dir),
        ],
    )

    assert MODULE.main() == 0
    assert "Wrote" in capsys.readouterr().out
    output_text = (results_dir / "generation-v1.jsonl").read_text(encoding="utf-8")
    config_text = (results_dir / "generation-v1.config.json").read_text(encoding="utf-8")
    summary = json.loads(
        (results_dir / "generation-v1.summary.json").read_text(encoding="utf-8")
    )
    assert "must-not-be-written" not in config_text
    assert json.loads(output_text)["metrics"]["refusal_true_positive"] is True
    assert summary["cells"][0]["metrics"]["refusal_recall"] == 1.0


def test_main_refuses_to_overwrite_any_existing_artifact(monkeypatch, tmp_path, capsys):
    results_dir = tmp_path / "generation"
    results_dir.mkdir()
    (results_dir / "occupied.summary.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(
        MODULE.sys,
        "argv",
        [
            str(SCRIPT_PATH),
            "--run-id",
            "occupied",
            "--results-dir",
            str(results_dir),
        ],
    )

    assert MODULE.main() == 1
    assert "run_id already exists: occupied" in capsys.readouterr().out
