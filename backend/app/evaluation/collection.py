"""Durable, budgeted response collection with an injected one-call transport.

No network client or credentials are created here. Token counts, prices and
human authorization must be established by the caller before live collection.
"""

import hashlib
import json
import math
import sqlite3
import time
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def validate_config(config):
    required = {
        "provider",
        "requested_model",
        "endpoint",
        "approval_reference",
        "tokenizer_id",
        "max_calls",
        "max_input_tokens",
        "max_output_tokens",
        "temperature",
        "currency",
        "input_price_per_million",
        "output_price_per_million",
        "cost_limit",
        "price_reference",
        "thinking",
    }
    if set(config) != required:
        raise ValueError(
            "Unexpected/missing collection config fields; credentials must stay outside the journal"
        )
    for key in (
        "provider",
        "requested_model",
        "endpoint",
        "approval_reference",
        "tokenizer_id",
        "currency",
        "price_reference",
    ):
        if not isinstance(config[key], str) or not config[key].strip():
            raise ValueError(f"Nonempty {key} required")
    for key in ("max_calls", "max_input_tokens", "max_output_tokens"):
        if type(config[key]) is not int or config[key] <= 0:
            raise ValueError(f"Positive integer {key} required")
    if config["thinking"] != "disabled":
        raise ValueError("This pilot requires explicit non-thinking mode")
    value = config["temperature"]
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 2:
        raise ValueError("Invalid temperature")
    for key in ("input_price_per_million", "output_price_per_million", "cost_limit"):
        if not isinstance(config[key], str):
            raise ValueError("Prices and monetary limits require decimal strings")
        number = Decimal(config[key])
        if not number.is_finite() or number < 0:
            raise ValueError("Invalid price/limit")
    if Decimal(config["cost_limit"]) <= 0:
        raise ValueError("Positive cost limit required")


class ResponseCollector:
    """One journal per fixed configuration; pending attempts never auto-retry."""

    def __init__(self, path: Path, config: dict, transport, *, clock=time.perf_counter):
        validate_config(config)
        self.path, self.config, self.transport, self.clock = (
            Path(path),
            json.loads(canonical(config)),
            transport,
            clock,
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            db.execute(
                "CREATE TABLE IF NOT EXISTS attempts (question_id TEXT PRIMARY KEY, "
                "request_key TEXT UNIQUE NOT NULL, request_json TEXT NOT NULL, result_json TEXT)"
            )
            db.execute("INSERT OR IGNORE INTO metadata VALUES ('config', ?)", (canonical(self.config),))
            saved = db.execute("SELECT value FROM metadata WHERE key='config'").fetchone()[0]
            if saved != canonical(self.config):
                raise ValueError("Journal configuration cannot change on resume")

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        try:
            connection.execute("PRAGMA synchronous=FULL")
            with connection:
                yield connection
        finally:
            connection.close()

    def estimated_cost(self, input_tokens, output_tokens):
        c = self.config
        return (
            Decimal(input_tokens) * Decimal(c["input_price_per_million"])
            + Decimal(output_tokens) * Decimal(c["output_price_per_million"])
        ) / Decimal(1000000)

    def collect(self, request: dict, token_check: dict) -> dict:
        # Snapshot mutable caller input; the persisted payload is exactly what is sent.
        request = json.loads(canonical(request))
        qid = request["question_id"]
        if not isinstance(qid, str) or not qid:
            raise ValueError("Nonempty question ID required")
        if (
            json.loads(request["prompt"]) != request["messages"]
            or digest(request["chunks"]) != request["context_sha256"]
        ):
            raise ValueError("Request prompt/context identity mismatch")
        if (
            token_check.get("request_sha256") != digest(request)
            or token_check.get("tokenizer_id") != self.config["tokenizer_id"]
            or token_check.get("includes_message_overhead") is not True
        ):
            raise ValueError("Token preflight must bind this request and include message overhead")
        n = token_check.get("input_tokens")
        if type(n) is not int or not 0 < n <= self.config["max_input_tokens"]:
            raise ValueError("Input token budget exceeded or unverified")
        payload = {
            "model": self.config["requested_model"],
            "messages": request["messages"],
            "temperature": self.config["temperature"],
            "max_tokens": self.config["max_output_tokens"],
            "extra_body": {"thinking": {"type": self.config["thinking"]}},
        }
        request_key = digest({"request": request, "config": self.config, "token_check": token_check})
        worst = self.estimated_cost(self.config["max_input_tokens"], self.config["max_output_tokens"])
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute(
                "SELECT request_key,result_json FROM attempts WHERE question_id=?", (qid,)
            ).fetchone()
            if previous:
                if previous[0] != request_key:
                    raise ValueError("Question/request identity changed on resume")
                if previous[1] is None:
                    raise RuntimeError("Unresolved attempt: provider outcome unknown; no automatic retry")
                return json.loads(previous[1])
            if db.execute("SELECT value FROM metadata WHERE key='halt_reason'").fetchone():
                raise RuntimeError("Collection halted; inspect journal before any further calls")
            count = db.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]
            if count >= self.config["max_calls"] or worst * (count + 1) > Decimal(self.config["cost_limit"]):
                raise ValueError("Call or reserved cost budget exhausted")
            db.execute(
                "INSERT INTO attempts VALUES (?, ?, ?, NULL)",
                (
                    qid,
                    request_key,
                    canonical(
                        {
                            "request": request,
                            "payload": payload,
                            "token_check": token_check,
                            "reserved_cost": str(worst),
                        }
                    ),
                ),
            )
        # Reservation commits before the network boundary. BaseException leaves a pending record.
        start = self.clock()
        try:
            observation = self.transport(json.loads(canonical(payload)))
            result, halt = self.normalize(request, observation)
        except Exception as exc:
            # Never persist exception messages, HTTP headers or credentials.
            result, halt = self.base_row(request), None
            result.update(
                execution_status="system_error",
                response="",
                model=None,
                usage=None,
                finish_reason=None,
                cost_estimate=None,
                error_type=type(exc).__name__,
            )
        result.update(
            request_key=request_key,
            latency_seconds=max(0.0, self.clock() - start),
            request_count=1,
            reserved_cost=str(worst),
            currency=self.config["currency"],
            cost_scope="token-price estimate, not an invoice; unknown usage retains full reservation",
            endpoint=self.config["endpoint"],
            approval_reference=self.config["approval_reference"],
        )
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "UPDATE attempts SET result_json=? WHERE question_id=? "
                "AND request_key=? AND result_json IS NULL",
                (canonical(result), qid, request_key),
            )
            if halt:
                db.execute("INSERT OR REPLACE INTO metadata VALUES ('halt_reason', ?)", (halt,))
        return result

    def base_row(self, request):
        row = {
            key: request[key]
            for key in (
                "question_id",
                "question",
                "chunks",
                "prompt",
                "prompt_template",
                "replicate_id",
                "retrieval",
                "corpus_hashes",
                "retained_intervals",
            )
        }
        row.update(
            provider=self.config["provider"],
            requested_model=self.config["requested_model"],
            decoding={
                "temperature": self.config["temperature"],
                "max_tokens": self.config["max_output_tokens"],
                "thinking": self.config["thinking"],
            },
            draft_request_sha256=digest(request),
        )
        return row

    def normalize(self, request, observation):
        if not isinstance(observation, dict):
            raise ValueError("Transport must return a normalized response object")
        response = observation.get("response")
        model = observation.get("model")
        if not isinstance(response, str) or not response.strip():
            raise ValueError("Empty or invalid response")
        row = self.base_row(request)
        halt = None
        if not isinstance(model, str) or not model.strip():
            model, halt = None, "Returned model identity missing"
        usage = observation.get("usage")
        valid_usage = isinstance(usage, dict) and all(
            type(usage.get(k)) is int and usage[k] >= 0 for k in ("input_tokens", "output_tokens")
        )
        cost = None
        if valid_usage:
            usage = {k: usage[k] for k in ("input_tokens", "output_tokens")}
            cost = str(self.estimated_cost(usage["input_tokens"], usage["output_tokens"]))
            if (
                usage["input_tokens"] > self.config["max_input_tokens"]
                or usage["output_tokens"] > self.config["max_output_tokens"]
            ):
                halt = "Provider usage exceeds reserved envelope"
        else:
            usage = None
            halt = halt or "Provider usage missing or invalid"
        row.update(
            execution_status="ok",
            response=response,
            model=model,
            usage=usage,
            finish_reason=observation.get("finish_reason"),
            cost_estimate=cost,
            error_type=None,
        )
        return row, halt

    def export_cache(self, path: Path):
        """Export only when no provider outcome is unresolved; never overwrite."""
        with self.connect() as db:
            rows = db.execute("SELECT result_json FROM attempts ORDER BY question_id").fetchall()
        if not rows or any(row[0] is None for row in rows):
            raise ValueError("No completed cache or unresolved provider outcome")
        with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
            for row in rows:
                stream.write(row[0] + "\n")
