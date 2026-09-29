import ast
import hashlib
import importlib.util
import json
import math
from pathlib import Path

import pytest
from app.evaluation.coverage import evidence_coverage
from app.evaluation.replay import grouped_bootstrap, replay_development, score_grid
from app.evaluation.selective import (
    group_split,
    select_working_point,
    selective_summary,
    validate_group_split,
)
from app.rag.gating import ContextChunk, gate

ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def judgment(qid="1", behavior="answer", **updates):
    row = dict(
        question_id=qid,
        behavior=behavior,
        execution_status="ok",
        corpus_supported=True,
        context_sufficient=True,
        correct=True,
        complete=True,
        supported=True,
    )
    if behavior == "refusal":
        row.update(correct=None, complete=None, supported=None)
    return {**row, **updates}


def candidate(rows, t=0, u=0):
    return dict(
        summary=selective_summary(rows), generation_call_n=len(rows), score_threshold=t, lexical_threshold=u
    )


@pytest.mark.parametrize(
    "field,bad",
    [
        ("score_threshold", float("nan")),
        ("score_threshold", float("inf")),
        ("lexical_threshold", -1),
        ("lexical_threshold", True),
        ("generation_call_n", -1),
    ],
)
def test_selector_rejects_malformed_candidate_even_after_unknown(field, bad):
    c = candidate([judgment()])
    c[field] = bad
    with pytest.raises(ValueError):
        select_working_point([candidate([judgment(correct=None)]), c], split="dev")


def test_risk_before_coverage_and_inclusive_half_boundary():
    lower_risk = candidate([judgment("1"), judgment("2", "refusal")], t=2)
    higher_coverage = candidate([judgment("1"), judgment("2", correct=False)], t=0)
    selected = select_working_point([higher_coverage, lower_risk], split="dev")
    assert selected["selected"] == lower_risk
    assert lower_risk["summary"]["metrics"]["answer_coverage"]["value"] == 0.5


def test_lexical_tie_and_zero_token_ablation():
    chunks = [ContextChunk("alpha", 2)]
    assert gate("alpha beta", chunks, strategy="C", score_threshold=2, lexical_threshold=0.5)[
        "allow_generation"
    ]
    assert not gate("alpha beta", chunks, strategy="C", lexical_threshold=math.nextafter(0.5, 1))[
        "allow_generation"
    ]
    for question in ("What is it?", "中文"):
        for context in (chunks, []):
            assert (
                gate(question, context, strategy="B")["allow_generation"]
                == gate(question, context, strategy="C", lexical_threshold=0)["allow_generation"]
            )


def test_gate_import_boundary_and_top5_contract():
    tree = ast.parse((ROOT / "backend/app/rag/gating.py").read_text(encoding="utf-8"))
    imports = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    imports += [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
    assert set(imports) <= {"math", "re", "dataclasses"}
    with pytest.raises(ValueError, match="five"):
        gate("alpha", [ContextChunk("alpha", 1)] * 6, strategy="C")
    with pytest.raises(ValueError, match="ranked"):
        gate("alpha", [ContextChunk("alpha", 1), ContextChunk("alpha", 2)], strategy="B")


def test_legacy_group_and_group_exposure_are_required():
    row = dict(
        question_id="renamed-q001",
        group_id="legacy-exposed-30",
        split="test",
        previously_exposed=False,
        group_previously_exposed=False,
    )
    with pytest.raises(ValueError):
        validate_group_split([row])
    row["group_id"] = "new"
    row.pop("group_previously_exposed")
    with pytest.raises(ValueError):
        validate_group_split([row])


@pytest.mark.parametrize("group", ["g0", "g1", "new-fact", "α"])
def test_split_matches_exact_hash_formula(group):
    expected = (
        "test"
        if int(hashlib.sha256(("selective-v0.1|" + group).encode()).hexdigest(), 16) % 5 == 0
        else "dev"
    )
    assert group_split(group, previously_exposed=False) == expected
    assert group_split(group, previously_exposed=True) == "dev"
    row = dict(
        question_id="new",
        group_id=group,
        split=expected,
        previously_exposed=False,
        group_previously_exposed=False,
    )
    validate_group_split([row], enforce_assignment=True)
    row["split"] = "dev" if expected == "test" else "test"
    with pytest.raises(ValueError):
        validate_group_split([row], enforce_assignment=True)


def test_planned_subset_rejects_same_cardinality_replacement():
    check = load_script("check_locked_reannotation")
    questions = ROOT / "data/eval/reannotation-20260923/input/questions.jsonl"
    ids = [json.loads(line)["question_id"] for line in questions.read_text(encoding="utf-8").splitlines()]
    plan = ROOT / "data/eval/reannotation-plan.md"
    check.validate_planned_ids(ids, plan)
    ids[0] = "q007"
    with pytest.raises(ValueError, match="predeclared"):
        check.validate_planned_ids(ids, plan)


def test_coverage_fraction_denominators_and_nonempty_na_cell():
    audit = load_script("audit_text_coverage")
    gold = dict(document_id="d", revision="v1", start_char=0, end_char=4, quote="a  b")
    chunk = dict(document_id="d", revision="v1", start_char=0, end_char=1)
    r = evidence_coverage([gold], [chunk])
    assert r["mean_char_fraction"] == 0.25
    assert r["mean_nonspace_fraction"] == 0.5
    blank = {**gold, "quote": "    "}
    missing = evidence_coverage([blank], [chunk])
    assert missing["evidence_n"] == 1
    assert audit.aggregate_values([r["mean_nonspace_fraction"], missing["mean_nonspace_fraction"]]) == {
        "n": 1,
        "sum": 0.5,
        "mean": 0.5,
    }


def test_full_saved_coverage_rows_and_cells_match_current_math():
    audit = load_script("audit_text_coverage")
    old = json.loads((ROOT / "results/audits/2026-09-28/text-coverage-v1.json").read_text(encoding="utf-8"))
    current = audit.audit(
        ROOT / "results/runs/frozen-30-hybrid-rrf-v1.jsonl", ROOT / "data/eval/qa.jsonl", ROOT / "data/corpus"
    )
    assert current["rows"] == old["rows"]
    assert current["cells"] == old["cells"]
    assert len(current["rows"]) == 270 and len(current["cells"]) == 36


def test_config_lf_hash_portable(tmp_path):
    audit = load_script("audit_text_coverage")
    a, b = tmp_path / "lf", tmp_path / "crlf"
    a.write_bytes(b'{"a": 1}\n')
    b.write_bytes(b'{"a": 1}\r\n')
    assert audit.lf_digest(a) == audit.lf_digest(b)


def test_score_grid_exact_ties_bounds_and_dev_only():
    grid = score_grid([2, 1, 2, None], split="dev")
    assert grid == [math.nextafter(1.0, -math.inf), 1.0, 2.0, math.nextafter(2.0, math.inf)]
    with pytest.raises(ValueError):
        score_grid([1], split="test")
    with pytest.raises(ValueError):
        score_grid([float("nan")], split="dev")


def replay_rows():
    return [
        dict(
            question_id=str(i),
            question="alpha beta",
            chunks=[dict(text="alpha", score=i + 1)],
            group_id="legacy-exposed-30",
            split="dev",
            previously_exposed=True,
            group_previously_exposed=True,
            expected_behavior=target,
            judgment=judgment(str(i)),
        )
        for i, target in enumerate(("answer", "correct_premise", "refuse"))
    ]


def test_replay_has_grid_targets_ablation_and_no_label_masking():
    rows = replay_rows()
    report = replay_development(rows)
    assert report["remote_calls"] == 0
    assert len(report["candidates"]["B"]) == 5 and len(report["candidates"]["C"]) == 25
    assert all(c["n"] == 1 for c in report["baseline"]["by_target"].values())
    for b, c in zip(report["candidates"]["B"], report["candidates"]["C"][::5]):
        assert b["summary"] == c["summary"]
    rows[0]["judgment"]["correct"] = None
    report = replay_development(rows)
    assert report["selections"]["C"]["0.5"]["status"] == "incomplete_annotations"


def test_bootstrap_paired_duplicates_and_undefined_risk():
    rows = [dict(judgment("1"), group_id="g1"), dict(judgment("2", "refusal"), group_id="g2")]
    result = grouped_bootstrap({"A": rows, "B": rows})
    assert result == grouped_bootstrap({"A": rows, "B": rows})
    assert result["resamples"] == 2000
    risk = result["intervals"]["A"]["selective_risk"]
    assert 0.20 < risk["undefined_fraction"] < 0.30
    assert result["paired_differences"]["B"]["selective_risk"]["interval_95"] == [0, 0]
    refusals = [dict(judgment(str(i), "refusal"), group_id=str(i)) for i in range(2)]
    risk = grouped_bootstrap({"A": refusals})["intervals"]["A"]["selective_risk"]
    assert risk["undefined_fraction"] == 1 and risk["interval_95"] is None
    assert grouped_bootstrap({"A": rows[:1]})["status"] == "insufficient_groups"
    with pytest.raises(ValueError):
        grouped_bootstrap({"A": [rows[0], rows[0]]})
    with pytest.raises(ValueError):
        grouped_bootstrap({"A": rows, "B": rows[:1]})


def test_known_split_assignments():
    assert group_split("g0", previously_exposed=False) == "dev"
    assert group_split("g7", previously_exposed=False) == "test"


def make_cli_inputs(tmp_path, module, split_kind):
    groups = [
        f"cli-g{i}" for i in range(100) if group_split(f"cli-g{i}", previously_exposed=False) == split_kind
    ][:2]
    cache, reviews, split = [], [], []
    for i, group in enumerate(groups):
        qid = f"{split_kind}-{i}"
        c = dict(
            question_id=qid,
            question="alpha beta",
            chunks=[dict(text="alpha beta", score=i + 1)],
            response="alpha beta",
            execution_status="ok",
            prompt="answer alpha beta",
            prompt_template="answer {question}",
            provider="synthetic-unit-test",
            model="fixture",
            decoding={"temperature": 0},
            replicate_id="0",
            retrieval={"method": "bm25", "top_k": 5},
            corpus_hashes={"fixture": "0" * 64},
        )
        review = dict(
            question_id=qid,
            labels=judgment(qid),
            expected_behavior="answer",
            cache_sha256=module.digest(c),
            context_sha256=module.digest(c["chunks"]),
            response_sha256=hashlib.sha256(c["response"].encode()).hexdigest(),
            reviewer_id="test-fixture",
            reviewer_type="synthetic",
            reviewed_at="2026-09-29",
            rubric_version="selective-v0.2-dev",
            rationale="Unit test only, never research data",
        )
        cache.append(c)
        reviews.append(review)
        split.append(
            dict(
                question_id=qid,
                group_id=group,
                split=split_kind,
                previously_exposed=False,
                group_previously_exposed=False,
            )
        )
    paths = {}
    for name, rows in (("cache", cache), ("reviews", reviews), ("split", split)):
        p = tmp_path / (split_kind + "-" + name + ".jsonl")
        p.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8", newline="\n")
        paths[name] = p
    return paths


def test_replay_cli_dev_then_heldout_and_provenance(tmp_path, monkeypatch):
    module = load_script("replay_selective")
    outputs = {}
    for mode in ("dev", "test"):
        paths = make_cli_inputs(tmp_path, module, mode)
        output = tmp_path / (mode + "-output.json")
        args = ["replay", "--mode", mode, "--output", str(output)]
        for name, path in paths.items():
            args += ["--" + name, str(path)]
        if mode == "test":
            args += ["--working-points", str(outputs["dev"])]
        monkeypatch.setattr(module.sys, "argv", args)
        module.main()
        report = json.loads(output.read_text(encoding="utf-8"))
        assert report["remote_calls"] == 0
        assert len(report["inputs_sha256"]) == (3 if mode == "dev" else 4)
        outputs[mode] = output
    assert report["bootstrap"]["resamples"] == 2000
    assert report["outcomes"]["C"]["summary"]["metrics"]["selective_risk"]["value"] == 0
    cache, reviews, split = (module.load_rows(paths[k]) for k in ("cache", "reviews", "split"))
    next(iter(reviews.values()))["cache_sha256"] = "bad"
    with pytest.raises(ValueError, match="Review does not match"):
        module.join_inputs(cache, reviews, split)
    with pytest.raises(ValueError, match="new output"):
        module.main()


def test_old_audit_entry_accepts_both_registered_qa_bytes(tmp_path, monkeypatch, capsys):
    module = load_script("audit_evidence_coverage")
    raw = (ROOT / "data/eval/qa.jsonl").read_bytes()
    lf = raw.replace(b"\r\n", b"\n")
    lines = lf.splitlines(keepends=True)
    original = b"".join(
        line.replace(b"\n", b"\r\n") if i in {1, 2, 3, 4, 5, 7, 8} else line
        for i, line in enumerate(lines, 1)
    )
    for data in (lf, original):
        qa = tmp_path / "qa.jsonl"
        qa.write_bytes(data)
        monkeypatch.setattr(
            module.sys,
            "argv",
            ["audit", "--run", str(ROOT / "results/runs/frozen-30-hybrid-rrf-v1.jsonl"), "--qa", str(qa)],
        )
        module.main()
        assert json.loads(capsys.readouterr().out)


def test_historical_strict_audit_cells_match():
    module = load_script("audit_text_coverage")
    old = json.loads(
        (ROOT / "results/audits/2026-09-23-fixes/evidence-coverage.json").read_text(encoding="utf-8")
    )
    new = module.audit(
        ROOT / "results/runs/frozen-30-hybrid-rrf-v1.jsonl", ROOT / "data/eval/qa.jsonl", ROOT / "data/corpus"
    )
    index = {(c["method"], c["expected_behavior"], c["cohort"], c["k"]): c for c in new["cells"]}
    for c in old["cells"]:
        current = index[c["method"], c["class"], c["cohort"], c["k"]]
        for old_name, new_name in (
            ("any_recall", "recall_any"),
            ("full_recall", "recall_full_char"),
            ("any_complete", "complete_any"),
            ("full_complete", "complete_full_char"),
        ):
            assert current["metrics"][new_name]["mean"] == pytest.approx(c[old_name], abs=1e-6)


def test_current_audit_hashes_and_data_match():
    module = load_script("audit_text_coverage")
    saved = json.loads(
        (ROOT / "results/audits/2026-09-29-fixes/text-coverage-v1.json").read_text(encoding="utf-8")
    )
    new = module.audit(
        ROOT / "results/runs/frozen-30-hybrid-rrf-v1.jsonl", ROOT / "data/eval/qa.jsonl", ROOT / "data/corpus"
    )
    for key in ("rows", "cells", "implementation"):
        assert saved[key] == new[key]
    for key in ("run", "config", "qa"):
        assert saved["inputs"][key]["sha256"] == new["inputs"][key]["sha256"]


def test_bootstrap_missing_labels_only_withhold_dependent_intervals():
    a = [dict(judgment("1", correct=None), group_id="g1"), dict(judgment("2"), group_id="g2")]
    b = [dict(judgment("1"), group_id="g1"), dict(judgment("2"), group_id="g2")]
    result = grouped_bootstrap({"A": a, "B": b}, resamples=200)
    assert result["intervals"]["A"]["selective_risk"]["interval_95"] is None
    assert result["intervals"]["A"]["answer_coverage"]["interval_95"] == [1, 1]
    assert result["intervals"]["B"]["selective_risk"]["interval_95"] == [0, 0]
    assert result["paired_differences"]["B"]["selective_risk"]["interval_95"] is None
    assert result["paired_differences"]["B"]["answer_coverage"]["interval_95"] == [0, 0]


@pytest.mark.parametrize(
    "change", ["version", "implementation", "split", "grid", "candidate", "counts", "selection", "labels"]
)
def test_saved_development_report_rejects_inconsistent_working_points(change):
    module = load_script("replay_selective")
    rows = replay_rows()
    report = replay_development(rows)
    report.update(
        protocol_version=module.PROTOCOL_VERSION,
        implementation_sha256=module.implementation_hashes(),
        split_manifest=[
            {
                k: r[k]
                for k in (
                    "question_id",
                    "group_id",
                    "split",
                    "previously_exposed",
                    "group_previously_exposed",
                )
            }
            for r in rows
        ],
    )
    # Emulate a saved JSON document, removing shared object references.
    report = json.loads(json.dumps(report))
    module.validate_development_report(report)
    if change == "version":
        report["protocol_version"] = "old"
    elif change == "implementation":
        report["implementation_sha256"] = {}
    elif change == "split":
        report["split_manifest"][0]["split"] = "test"
    elif change == "grid":
        report["score_grid"][0] = -999
    elif change == "candidate":
        report["candidates"]["B"].pop()
    elif change == "counts":
        report["candidates"]["B"][0]["generation_call_n"] = 99
    elif change == "selection":
        report["selections"]["B"]["0.5"]["selected"]["score_threshold"] = 999
    elif change == "labels":
        report["labels_complete"] = False
    with pytest.raises(ValueError):
        module.validate_development_report(report)


def test_review_rubric_version_must_match(tmp_path):
    module = load_script("replay_selective")
    paths = make_cli_inputs(tmp_path, module, "dev")
    cache, reviews, split = (module.load_rows(paths[k]) for k in ("cache", "reviews", "split"))
    next(iter(reviews.values()))["rubric_version"] = "unrelated-version"
    with pytest.raises(ValueError, match="rubric version"):
        module.join_inputs(cache, reviews, split)
