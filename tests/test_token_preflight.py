import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("token_preflight", ROOT / "scripts/check_deepseek_tokens.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


@pytest.mark.parametrize(
    "messages",
    [
        [],
        [{"role": "user", "content": "hello"}],
        [{"role": "system", "content": "s"}, {"role": "assistant", "content": "a"}],
        [{"role": "system", "content": "s"}, {"role": "user", "content": []}],
        [{"role": "system", "content": "s", "name": "x"}, {"role": "user", "content": "u"}],
    ],
)
def test_unsupported_message_shapes_are_rejected(messages):
    with pytest.raises(ValueError):
        MODULE.render_messages(messages)


def test_count_includes_framing_binds_request_and_rejects_over_budget():
    messages = [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}]
    request = {"question_id": "fixture", "messages": messages, "prompt": json.dumps(messages)}
    captured = []

    def encode(text, *, add_special_tokens):
        captured.append((text, add_special_tokens))
        return SimpleNamespace(ids=list(range(100)))

    row = MODULE.count_request(request, SimpleNamespace(encode=encode))
    assert captured == [("<｜begin▁of▁sentence｜><｜System｜>s<｜User｜>u<｜Assistant｜></think>", False)]
    assert row["includes_message_overhead"] is True
    assert row["request_sha256"] == MODULE.digest(request)
    assert row["input_tokens"] == 100
    with pytest.raises(ValueError, match="envelope"):
        MODULE.count_request(
            request, SimpleNamespace(encode=lambda *a, **kw: SimpleNamespace(ids=[0] * 4097))
        )
    with pytest.raises(ValueError, match="identity"):
        MODULE.count_request({**request, "prompt": "[]"}, SimpleNamespace(encode=encode))
