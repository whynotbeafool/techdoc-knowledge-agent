# Selective answering protocol — v0.1-dev

Date: 2026-09-28. Status: **development protocol, not a frozen confirmatory experiment**. Implementation may be exercised offline now. A final evaluation freeze requires a new dataset/group manifest, complete semantic annotation arrangements, exact provider/model/prompt configuration and an explicit paid-call budget. No current result supports a claim that C improves risk.

## Question and hypotheses

On the same retrieved context and generator, does an inexpensive query/context lexical proxy added to a retrieval-score threshold improve the observed answer-coverage / selective-risk trade-off? C may fail on paraphrases, misleading shared words, partial evidence or false premises. These are planned analyses, not reasons to relabel samples or choose a new test set after failure.

The current fixed corpus has five active English documents and 30 exposed dev questions. It supports development and historical diagnostics only. The target generalization for a future grouped holdout is **new question/evidence groups within that frozen corpus**, not unseen documents, domains, languages or deployed traffic.

## Fixed settings and runtime input boundary

- First experiment: existing BM25 (k1=1.5, b=.75; repository tokenizer), chunk size 800 code points, top_k=5, same active corpus and canonical hashes for A/B/C.
- Pass exactly the same ranked context to every admitted generation. No per-strategy prompt changes, truncation, model changes or retrieval retuning.
- The gate accepts only question text and `ContextChunk(text, score)` objects. It imports no QA, reference answer, evidence gold, expected behavior, split truth or semantic labels. Retrieval scores are BM25 scores, not calibrated probabilities; do not transfer these thresholds to Dense/RRF.
- Orchestration may project old dev QA to `(question_id, question)` before retrieval. Private labels and output scoring remain separate. Typed interfaces and tests reduce accidental leakage; they are not an OS security boundary.
- `prepare_selective_dev.py` performs this projection and real BM25 feature extraction. Its output includes no generated response, semantic risk, selected threshold or claimed strategy gain.

## Strategies and ablation

| Strategy | Gate before generation | Rejection |
|---|---|---|
| A | Always admit; retain the generator's own possible refusal | None added by the gate |
| B | Admit iff nonempty retrieval and first-ranked BM25 score >= t | Fixed refusal, with a separate policy-rejection event |
| C | B condition AND question/context content-token recall >= u | Same fixed refusal and event |

Content-token recall uses distinct lowercased ASCII alphanumeric/underscore tokens from the question, minus the fixed stoplist in `gating.py`, divided by the count of remaining question tokens. The numerator is their intersection with the union of Top-5 context tokens. This is **not** the old question/gold lexical stratum, an entity/fact matcher, a probability, or a semantic-sufficiency label. An empty content-token set fails positive u; u=0 explicitly disables the lexical condition. Non-English extension requires a new version.

Required ablation: C with u=0 and the *same t* must equal B, verified by tests. Report this mechanistic ablation separately from independently tuned B. A admits even an empty context; B/C reject an empty retrieval list. Gate admission is not actual answering, since an admitted generator may refuse.

## Threshold development and selection

Do not select thresholds until development generations and semantic labels exist. Define the score grid from distinct first-ranked **development** BM25 scores, plus finite values just below the minimum and above the maximum; store the actual numeric grid. Lexical grid: {0, .25, .5, .75, 1}. Use inclusive >= for ties and never randomly split tied questions. The current chosen t/u remain null.

Evaluate B's score grid and C's Cartesian grid on paired cached baseline outputs and fixed gate-refusal outputs. Main development working point: among candidates with observed substantive answer coverage >= .50 and complete labels, minimize selective risk; ties prefer higher answer coverage, then lower expected generation-call count, then lexicographically smaller (t,u). If no candidate meets .50, record the working point as infeasible; do not silently lower the target. Also report the whole dev curve and .25/.75 coverage constraints as secondary diagnostics. This is threshold development, not an unbiased effect estimate.

Apply selected numeric thresholds unchanged to a future heldout set and report its actual coverage, even if different. Do not tune a heldout threshold for a more favorable matched-coverage comparison. Unresolved labels make a candidate unevaluable, not better-performing. The pure development selector and tie rules are implemented in `selective.py`; it rejects test selection and blocks selection when a candidate depends on missing semantic labels. An end-to-end candidate-grid/replay runner remains to be connected to real judged generations before the evaluation freeze.

## Dataset grouping, exclusions and splitting

- Existing q001–q030 stay dev permanently. The preflight conservatively places all 30 in one `legacy-exposed-30` group; this is bookkeeping, not a claim that there are 30 independent samples.
- Before seeing new system outputs, group paraphrases, descendants of the same original question, and questions sharing necessary evidence facts. Take transitive closure. A group connected to any exposed question goes to dev; superficial disjoint offsets cannot establish independence.
- For otherwise eligible, new, unexposed groups, assign test when `int(SHA256('selective-v0.1|' + group_id),16) % 5 == 0`, dev otherwise. Freeze stable group IDs and the complete manifest before model/threshold development; do not rename groups to change their allocation. Report actual group counts and type distributions without outcome-driven rebalancing. Same-document sharing remains a limitation.
- Validate no group crosses dev/test and all test entries explicitly declare no previous exposure. The current validator also rejects the legacy IDs even if their exposure flag is false. Renaming a leaked question does not make it unexposed; this still needs provenance review.
- Exclude text-extraction/layout failures and genuinely unresolved question scope before outcome inspection, with reason and count. Do not exclude hard failures after seeing outputs. Existing q005/q010/q021 remain in historical diagnostics; unresolved semantics must be labeled unknown rather than guessed.
- No new test set or evidence groups have been constructed in this turn. Do not retroactively split the existing 30 questions.

## Semantic judgments and blinding

See `SEMANTIC_RUBRIC.md`. Corpus support and required facts are judged on the corpus before generating answers. Context sufficiency is judged from the exact packed context, not the system's response. Response correctness, completeness and support are separate labels. Present judgments without strategy name, score, threshold, predicted gate decision or system-comparison result; randomize review order and record reviewer type/identity and disagreements.

An AI reviewer is permissible for exploratory development but must be labeled as AI and exposed where applicable. There is currently no independent human review arrangement. The user's restriction that they do not annotate the original 14-question batch remains intact. This protocol does not request those questions be relabeled. Formal validation cannot be claimed from self-evaluation alone.

## Metrics and inference

Use the explicit denominators in coverage-v1 §6. Report numerator, denominator, missing-label count and value for every metric, overall and by ordinary answer / premise correction / refusal target. Count substantive corrections and partial answers as attempts. A missing necessary answer component counts as error; a correct but unsupported claim counts as error and unsupported. All-refusal selective risk is NA. API errors remain in the scheduled-question denominator and are separate from refusals.

Primary analysis: answer coverage together with selective risk, not one headline accuracy. Secondary: unsupported-answer rate, valid response rate on corpus-supported targets, false-refusal rate on sufficient contexts, service failures and costs. Keep the old prefix-contract metrics under their old names. Any-overlap and text coverage are offline diagnostics, not gating inputs.

For a heldout comparison, pair the same groups across methods. Report effect sizes and group-resampled uncertainty if enough independent groups exist, with 2,000 resamples and seed 20260928; a resample with no answered cases has undefined risk, not zero. Disclose the undefined fraction and do not issue a conventional interval if it becomes dominated by undefined samples. Shared-document dependence and small group counts still limit inference; this procedure alone does not establish statistical power. No CI is computed on the one-group current preflight.

## Generation, reuse, cost and logging

Development first uses one new baseline generation per question/configuration, then replays deterministic B/C gates over those identical outputs. Rejected cases get the same fixed refusal event. Cached replay estimates policy behavior under shared outputs; it does not measure real online latency or actual bills saved. Later live tests must separately measure wall-clock time and paid tokens. Do not reuse old responses as if they used the updated prompt formatter.

Cache keys must include corpus/context hash, question, retrieval config, full prompt text/hash, provider, exact returned model identity/version, decoding parameters and replicate ID. Log actual packed context and canonical retained intervals, response, execution failure, gate features/decision, thresholds, request count, tokens, cost currency and latency. Keep secrets out. On API failure, retain the scheduled row; retries consume the same budget and are logged, never silently substituted.

Current authorized remote-call budget for this protocol: **0**. Offline preparation needs no model calls. Proposed 30-question pilot envelope, to be approved before execution: one shared baseline call per question, maximum 4,096 input tokens and 512 output tokens, at most 30 calls (no automatic retries). This bounds tokens at 122,880 input / 15,360 output; it is not a measured tokenizer count or a dollar quote. Estimated cost is `(122880 * input_price_per_million + 15360 * output_price_per_million) / 1e6`, using the selected provider's verified prices at execution time. If packing exceeds the envelope, stop and version the packing policy rather than silently changing only one strategy. No extra LLM calls are used by the proposed C gate.

Provider/model selection, prompt snapshot, real token preflight, budget approval, label completion, new group manifest, candidate-grid/replay integration and heldout runner are required before the evaluation freeze. Model versions cannot be inferred from historical run names. Until these are resolved, the status remains dev-ready, not preregistered/confirmed.

## Executable pieces

- `backend/app/rag/gating.py`: A/B/C decision functions using runtime text/scores only.
- `backend/app/evaluation/selective.py`: missing-aware semantic metric aggregation and group/split validation; it consumes judgments and does not create them.
- `python scripts/prepare_selective_dev.py --output-dir <new-directory>`: 30-question gold-free projection plus actual BM25 features, no generation.
- `tests/test_selective.py`: input boundary, ablation, ties, missing labels, all-refusal, failures, group leakage and legacy-test contamination.

The current stage is an executable offline prototype plus a reviewable protocol. A/B/C end-to-end generation comparison, effectiveness, independent annotation and a heldout result are not yet delivered.
