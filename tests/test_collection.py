import importlib.util
import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest
from app.evaluation.collection import ResponseCollector, digest
from app.evaluation.deepseek_transport import DeepSeekTransport

ROOT = Path(__file__).resolve().parents[1]


def test_deepseek_adapter_disables_sdk_retries_and_preserves_observed_metadata():
    calls = []
    constructor = {}
    result = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="answer"), finish_reason="length")],
        model="returned-model",
        usage=SimpleNamespace(prompt_tokens=123, completion_tokens=512),
    )

    def factory(**kwargs):
        constructor.update(kwargs)
        return SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=lambda **kw: calls.append(kw) or result)
            ),
            close=lambda: calls.append("closed"),
        )

    transport = DeepSeekTransport("synthetic-test-key", client_factory=factory)
    assert constructor["max_retries"] == 0
    assert constructor["base_url"] == "https://api.deepseek.com"
    assert not calls
    observed = transport({"model": "requested-alias"})
    assert calls == [{"model": "requested-alias"}]
    assert observed["model"] == "returned-model"
    assert observed["usage"] == {"input_tokens": 123, "output_tokens": 512}
    assert observed["finish_reason"] == "length"
    transport.close()
    assert calls[-1] == "closed"


def config(**updates):
    return {
        "provider": "synthetic",
        "requested_model": "alias",
        "endpoint": "https://example.invalid",
        "approval_reference": "synthetic-unit-test-only",
        "tokenizer_id": "fixture",
        "max_calls": 2,
        "max_input_tokens": 4096,
        "max_output_tokens": 512,
        "temperature": 0.2,
        "thinking": "disabled",
        "currency": "CNY",
        "input_price_per_million": "2",
        "output_price_per_million": "8",
        "cost_limit": "1",
        "price_reference": "synthetic-price-fixture",
        **updates,
    }


def request(qid="new-1"):
    row = json.loads(
        (ROOT / "results/selective/request-draft-20260930/requests.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    row["question_id"] = qid
    return row


def check(row):
    return dict(
        request_sha256=digest(row), tokenizer_id="fixture", includes_message_overhead=True, input_tokens=100
    )


def response(**updates):
    return {
        "response": "Synthetic answer",
        "model": "actual-version",
        "usage": {"input_tokens": 100, "output_tokens": 10},
        "finish_reason": "stop",
        **updates,
    }


def test_resume_returns_same_cache_without_second_transport_call(tmp_path):
    calls = []
    collector = ResponseCollector(
        tmp_path / "run.sqlite", config(), lambda payload: calls.append(payload) or response()
    )
    row = request()
    first = collector.collect(row, check(row))
    second = ResponseCollector(
        tmp_path / "run.sqlite", config(), lambda _: pytest.fail("repeated call")
    ).collect(row, check(row))
    assert first == second and len(calls) == 1
    assert first["model"] == "actual-version" and first["requested_model"] == "alias"
    assert first["cost_estimate"] == "0.00028"
    assert calls[0]["extra_body"] == {"thinking": {"type": "disabled"}}
    path = tmp_path / "cache.jsonl"
    collector.export_cache(path)
    assert json.loads(path.read_text(encoding="utf-8")) == first
    with pytest.raises(FileExistsError):
        collector.export_cache(path)


def test_pending_attempt_is_committed_before_call_and_never_retried(tmp_path):
    path = tmp_path / "run.sqlite"

    def interrupted(_):
        with sqlite3.connect(path) as db:
            assert db.execute("SELECT COUNT(*) FROM attempts WHERE result_json IS NULL").fetchone()[0] == 1
        raise KeyboardInterrupt()

    collector = ResponseCollector(path, config(), interrupted)
    row = request()
    with pytest.raises(KeyboardInterrupt):
        collector.collect(row, check(row))
    collector = ResponseCollector(path, config(), lambda _: pytest.fail("must not retry unknown outcome"))
    with pytest.raises(RuntimeError, match="Unresolved"):
        collector.collect(row, check(row))
    with pytest.raises(ValueError, match="unresolved"):
        collector.export_cache(tmp_path / "cache")


def test_failures_are_not_refusals_and_messages_never_persist(tmp_path):
    def fail(_):
        raise TimeoutError("secret-header=do-not-log")

    collector = ResponseCollector(tmp_path / "run.sqlite", config(max_calls=1), fail)
    row = request()
    result = collector.collect(row, check(row))
    assert result["execution_status"] == "system_error" and result["response"] == ""
    assert result["model"] is None and result["usage"] is None and result["cost_estimate"] is None
    assert result["error_type"] == "TimeoutError" and "do-not-log" not in json.dumps(result)
    another = request("new-2")
    with pytest.raises(ValueError, match="budget exhausted"):
        collector.collect(another, check(another))


@pytest.mark.parametrize(
    "updates",
    [
        {"cost_limit": "0.001"},
        {"max_calls": 0},
        {"temperature": float("nan")},
        {"thinking": "enabled"},
        {"api_key": "must-not-store"},
    ],
)
def test_invalid_or_exhausted_budget_never_calls_transport(tmp_path, updates):
    with pytest.raises(ValueError):
        collector = ResponseCollector(
            tmp_path / "run.sqlite", config(**updates), lambda _: pytest.fail("unfunded call")
        )
        row = request()
        collector.collect(row, check(row))


@pytest.mark.parametrize("change", ["request", "tokenizer", "overhead", "limit"])
def test_token_check_binds_request_and_envelope(tmp_path, change):
    collector = ResponseCollector(tmp_path / "run.sqlite", config(), lambda _: pytest.fail("unverified call"))
    row = request()
    verified = check(row)
    if change == "request":
        verified["request_sha256"] = "bad"
    elif change == "tokenizer":
        verified["tokenizer_id"] = "wrong"
    elif change == "overhead":
        verified["includes_message_overhead"] = False
    else:
        verified["input_tokens"] = 5000
    with pytest.raises(ValueError):
        collector.collect(row, verified)


@pytest.mark.parametrize(
    "observation",
    [
        response(usage=None),
        response(model=None),
        response(usage={"input_tokens": 10000, "output_tokens": 10}),
    ],
)
def test_invalid_provider_metadata_preserved_but_halts_future_calls(tmp_path, observation):
    collector = ResponseCollector(tmp_path / "run.sqlite", config(), lambda _: observation)
    row = request()
    result = collector.collect(row, check(row))
    assert result["response"] == "Synthetic answer"
    another = request("new-2")
    with pytest.raises(RuntimeError, match="halted"):
        collector.collect(another, check(another))


def test_changed_identity_cannot_resume(tmp_path):
    path = tmp_path / "run.sqlite"
    collector = ResponseCollector(path, config(), lambda _: response())
    row = request()
    collector.collect(row, check(row))
    row["replicate_id"] = "changed"
    with pytest.raises(ValueError, match="identity changed"):
        collector.collect(row, check(row))
    with pytest.raises(ValueError, match="configuration cannot change"):
        ResponseCollector(path, config(max_calls=10), lambda _: response())


def test_collection_cache_joins_replay_and_keeps_failure_model_unknown(tmp_path):
    spec = importlib.util.spec_from_file_location("replay_collection", ROOT / "scripts/replay_selective.py")
    replay = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(replay)

    def transport(_):
        if transport.n:
            raise TimeoutError("not logged")
        transport.n += 1
        return response()

    transport.n = 0
    collector = ResponseCollector(tmp_path / "run.sqlite", config(), transport)
    cache, reviews, split = {}, {}, {}
    for qid in ("new-1", "new-2"):
        row = request(qid)
        result = collector.collect(row, check(row))
        cache[qid] = result
        reviews[qid] = dict(
            question_id=qid,
            cache_sha256=replay.digest(result),
            context_sha256=replay.digest(result["chunks"]),
            response_sha256=replay.hashlib.sha256(result["response"].encode()).hexdigest(),
            reviewer_id="synthetic",
            reviewer_type="fixture",
            reviewed_at="2026-10-04",
            rubric_version=replay.PROTOCOL_VERSION,
            rationale="Test only",
            expected_behavior="answer",
            labels={"execution_status": result["execution_status"]},
        )
        split[qid] = dict(
            question_id=qid,
            group_id="legacy-exposed-30",
            split="dev",
            previously_exposed=True,
            group_previously_exposed=True,
        )
    assert len(replay.join_inputs(cache, reviews, split)) == 2
    identity = replay.generation_config(cache)
    assert identity["request"]["model"] == "alias" and identity["returned_model"] == "actual-version"
    errors = {"new-2": cache["new-2"]}
    replay.check_generation_config(
        {"generation_config": identity, "generation_config_sha256": replay.digest(identity)},
        replay.generation_config(errors),
    )
    cache["new-2"].update(execution_status="ok", model="changed-version")
    with pytest.raises(ValueError, match="model identity changed"):
        replay.generation_config(cache)
