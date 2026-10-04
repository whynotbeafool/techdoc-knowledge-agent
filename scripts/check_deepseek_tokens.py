"""Offline V4.1 preflight for exactly one system + one user text message.

The restricted rendering follows the official implementation at SOURCE_REVISION.
No general conversation, tools, multimodal or thinking-mode support is implied.
Provider-reported usage remains authoritative; this is a local template count.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.evaluation.collection import digest  # noqa: E402

SOURCE_REVISION = "8cadfede7063c896b944e7bae05daa3549ae97ea"
TOKENIZER_SHA256 = "81f64d1248a68ce3663e07ab3ee48b851e5df0e32d27cb98e4c9a268151e8d99"
TOKENIZER_ID = f"deepseek-recipe/{SOURCE_REVISION}/v41/{TOKENIZER_SHA256}"


def render_messages(messages):
    if not isinstance(messages, list) or len(messages) != 2:
        raise ValueError("Exactly two messages required")
    for message, role in zip(messages, ("system", "user"), strict=True):
        if (
            not isinstance(message, dict)
            or set(message) != {"role", "content"}
            or message["role"] != role
            or not isinstance(message["content"], str)
            or not message["content"].strip()
        ):
            raise ValueError("Only system then user plain text is supported")
    return (
        "<｜begin▁of▁sentence｜><｜System｜>"
        + messages[0]["content"]
        + "<｜User｜>"
        + messages[1]["content"]
        + "<｜Assistant｜></think>"
    )


def count_request(request, tokenizer):
    if json.loads(request["prompt"]) != request["messages"]:
        raise ValueError("Prompt/messages identity mismatch")
    rendered = render_messages(request["messages"])
    count = len(tokenizer.encode(rendered, add_special_tokens=False).ids)
    if not 0 < count <= 4096:
        raise ValueError("Request exceeds the authorized input token envelope")
    return {
        "question_id": request["question_id"],
        "request_sha256": digest(request),
        "tokenizer_id": TOKENIZER_ID,
        "includes_message_overhead": True,
        "input_tokens": count,
        "rendered_prompt_sha256": hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
        "requested_model": "deepseek-flash",
        "thinking": "disabled",
        "count_scope": "official_local_template_not_provider_measured_usage",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests", type=Path, required=True)
    parser.add_argument("--tokenizer", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if hashlib.sha256(args.tokenizer.read_bytes()).hexdigest() != TOKENIZER_SHA256:
        raise ValueError("Tokenizer differs from the verified official artifact")
    from tokenizers import Tokenizer

    tokenizer = Tokenizer.from_file(str(args.tokenizer))
    requests = [json.loads(line) for line in args.requests.read_text(encoding="utf-8").splitlines()]
    ids = [r["question_id"] for r in requests]
    if not requests or len(requests) > 30 or len(ids) != len(set(ids)):
        raise ValueError("Empty, duplicate or over-budget request batch")
    rows = [count_request(request, tokenizer) for request in requests]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    counts = [row["input_tokens"] for row in rows]
    print(json.dumps({"requests": len(rows), "min": min(counts), "max": max(counts), "sum": sum(counts)}))


if __name__ == "__main__":
    main()
