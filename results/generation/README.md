# Generation run artifacts

Each generation run is derived from one immutable retrieval JSONL file and one
frozen QA file. A run writes three files with the same ID:

- `<run-id>.jsonl`: per-question response, retrieved chunk provenance, and behavior metrics.
- `<run-id>.config.json`: input hashes, retrieval method, provider/model, prompt hash, and refusal contract.
- `<run-id>.summary.json`: refusal accuracy, precision, recall, false-positive rate, and generation-system-error rate for all and confirmed-only cohorts.

Summary schema v2 also separates non-refusal questions by whether Top-5 retrieval
contained complete gold evidence. This conditional view helps distinguish a
conservative refusal caused by missing context from a response-contract error
when the necessary evidence was already present.

The runner refuses to overwrite any existing artifact. API keys are read from
the environment but never written. A complete run invokes the configured model
once per question, so confirm the provider, model, and budget before execution.

Generation system errors are excluded from refusal accuracy and reported
separately. The refusal metrics evaluate whether the response follows the
explicit refusal contract; they do not yet establish citation correctness or
answer support.

## Runs

| Run | Status | Notes |
|---|---|---|
| `frozen-30-bm25-deepseek-v1` | current baseline | First real-model run over all 30 frozen questions; 0 system errors. Raw refusal accuracy is 0.7000 and must be read with the accompanying retrieval-conditioned analysis. |

See `frozen-30-bm25-deepseek-v1.analysis.md` before quoting any metric.
