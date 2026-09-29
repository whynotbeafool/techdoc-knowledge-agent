# Offline replay input contract — v0.2-dev

This is an offline consumer of recorded responses and supplied reviews. It cannot collect answers or certify semantic accuracy. No synthetic examples belong in study results.

Three JSONL files must have the same unique `question_id` set:

- **Cache**: question_id, question, chunks (ordered, at most five objects with exactly text/score), response, execution_status (ok/system_error), full prompt, prompt_template, provider, model (returned identity), replicate_id, nonempty decoding/retrieval/corpus_hashes objects. retrieval must declare method=bm25 and top_k=5. The configuration must be identical across rows and between dev/test. Additional logs may retain packed canonical intervals, token counts, latency and cost; collection of these is still the generation adapter's responsibility.
- **Reviews**: question_id, labels (execution_status, behavior, corpus_supported, context_sufficient, correct, complete, supported), expected_behavior (answer/correct_premise/refuse), cache_sha256, context_sha256, response_sha256, reviewer_id, reviewer_type, reviewed_at, rubric_version, rationale. No target fields are passed to runtime gates. Review provenance fields must be nonempty; independence/blinding declarations still require separate review.
- **Split**: question_id, group_id, split, previously_exposed, group_previously_exposed. Group exposure is explicit, consistent, and must include any exposed descendant. The hash assignment is enforced for unexposed groups. Existing 30 questions and legacy-exposed-30 remain dev.

For cache/context hashes, use SHA-256 of UTF-8 JSON with ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False; context means the exact `chunks` array. response_sha256 hashes the exact UTF-8 response string. The cache hash includes the whole cache row, including any optional logged fields. These content hashes serve linked reviews; raw input-file hashes are separately recorded in the replay report. They do not replace frozen gold byte identities.

```sh
python scripts/replay_selective.py --cache <dev-cache.jsonl> --reviews <dev-reviews.jsonl> --split <dev-split.jsonl> --output <new-dev-report.json>
python scripts/replay_selective.py --mode test --cache <test-cache.jsonl> --reviews <test-reviews.jsonl> --split <test-split.jsonl> --working-points <dev-report.json> --output <new-test-report.json>
```

Development stores the exact finite score grid, lexical grid, A baseline, B/C candidate summaries, target strata, question-level gate events and primary .50 / secondary .25/.75 coverage selections. Missing required semantic labels withhold selection even if another policy would hide that sample by refusal. Empty retrieval has score grid [0.0], since all B/C gates reject regardless of threshold. If finite outer score boundaries cannot be represented, stop rather than emit infinity.

Heldout replay applies the .50 development working points unchanged, checking configuration and disjoint group/ID manifests. A strategy without a development working point stays unavailable. Paired bootstrap uses 2,000 common group draws, seed 20260928, six metrics and differences versus A; single-group inputs have no interval. Undefined draws are counted, never filled with zero. Intervals with at least half undefined draws, or missing original labels, are withheld. Even two groups do not establish statistical power.

A rejected gate creates an explicit policy_refusal event and a pure-refusal scored record, retaining corpus/context labels. An admitted gate reuses the baseline execution and labels, including failures. generation_call_n is the number of admitted requests under the simulated policy; remote_calls is always zero. This is not measured latency or billed savings. The CLI refuses to overwrite outputs.

The fixed policy refusal text is `I cannot provide an evidence-supported answer from the retrieved context.` It is recorded on every rejection event; admitted events reference their cached baseline instead.

Before heldout use, the runner requires the same protocol and implementation hashes, a valid dev-only manifest, the grid reconstructed from baseline scores, a complete candidate grid, consistent question/count records, and working points recomputed by the declared selection rule. It also requires the current rubric version. These are internal consistency checks, not signatures, proof of prior freezing, or proof that supplied summaries are truthful. Bootstrap missing-label checks apply per metric and contributing strategy pair; unrelated missing labels do not suppress an otherwise defined interval.
