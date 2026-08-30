# frozen-30-bm25-deepseek-v1 analysis

## Run status

- Retrieval input: `results/runs/frozen-30-v1.jsonl`, method `bm25`.
- Generator: `deepseek-v4-flash` through the configured DeepSeek OpenAI-compatible endpoint.
- Questions: 30 total, 29 confirmed and 1 needs_review.
- Generation system errors: 0.
- This is the first immutable real-model generation run for the frozen dataset.

## End-to-end refusal metrics

| Cohort | n | Refusal accuracy | Precision | Recall | False-positive rate | System-error rate |
|---|---:|---:|---:|---:|---:|---:|
| All annotations | 30 | 0.7000 | 0.4000 | 1.0000 | 0.3750 | 0.0000 |
| Confirmed only | 29 | 0.6897 | 0.4000 | 1.0000 | 0.3913 | 0.0000 |

All six expected-refusal questions were refused. The low precision comes from nine responses that began with the canonical refusal prefix even though the dataset expected an answer or premise correction.

## Error attribution

The raw behavior metric is end-to-end and must not be interpreted as a generator-only score. Joining the nine false positives back to the frozen retrieval run gives two distinct groups.

### Retrieval-limited conservative refusals: 6

`q006`, `q007`, `q011`, `q013`, `q017`, and `q019` did not have complete gold evidence in BM25 Top-5. The model's refusal is wrong relative to the dataset-level expected behavior, but is defensible given the incomplete retrieved context. These cases primarily diagnose retrieval coverage, not hallucination or refusal-policy failure.

### Full-evidence response-contract errors: 3

`q003`, `q027`, and `q029` had complete counter-evidence in BM25 Top-5. The generated responses correctly explained that the premise was false, but still began with `当前资料依据不足`. Under the explicit protocol this is a refusal false positive. These cases diagnose ambiguity in the prompt: premise correction needs its own positive instruction and must not reuse the refusal marker.

## Conclusions allowed

- The run completed without provider or infrastructure failures.
- The refusal policy achieved 1.0 recall on six expected-refusal questions in this dataset.
- Raw refusal precision was 0.4 because the system overused the refusal prefix.
- Six of nine false positives coincide with incomplete retrieval, while three are prompt/protocol errors despite complete counter-evidence.

## Conclusions not allowed

- Do not claim a general 100% refusal success rate; the refusal subset contains only six questions.
- Do not describe 0.700 accuracy as a generator-only quality score.
- Do not claim BM25 caused every refusal or that DeepSeek is intrinsically over-conservative.
- Do not compare this generation run with another model until the same retrieval rows, prompt contract, and QA revision are used.

## Next changes

1. Completed after this run: add an explicit `correct_premise` instruction without weakening out-of-scope refusal. The changed Prompt has a new hash and requires a new run ID for evaluation.
2. Report behavior metrics conditioned on retrieval completeness, while retaining the raw end-to-end metric.
3. Re-run under a new immutable run ID; never overwrite this baseline.
4. Keep q016/q017 in the delayed reannotation plan before using low-overlap strata for claims.
