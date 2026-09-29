# Coverage measurement specification v1

Date: 2026-09-28. Status: operational specification for offline measurement. Applying it to the already inspected 30-question development set is **post-hoc sensitivity analysis**, not preregistration or a new gold standard. The historical any-overlap metric remains unchanged. This document does not authorize runtime access to gold labels or instantiate a new A/B/C experiment.

## 1. Separate the objects being measured

| Name | Object | Existing data sufficient? |
|---|---|---|
| Selected-evidence location recall / complete hit | Contact with selected gold spans | Yes; historical primary result |
| Selected-evidence full-character coverage | Every code point of selected spans present in the union of retrieved intervals | Yes; strict sensitivity |
| Selected-evidence non-whitespace coverage | Same union, ignoring only whitespace in the gold text | Yes; explicitly post-hoc diagnostic |
| Necessary evidence-group satisfaction | Every required fact has a sufficient alternative evidence set | No; needs independent group/alternative annotations |
| Context sufficiency | Actual generator-visible context supports a valid full answer or correction | No; needs semantic judgments of that actual context |
| Answer coverage / selective risk | Whether the response answers substantively, and whether it is correct and supported | No; refusal-prefix labels cannot supply these judgments |

Neither the presence of one word from each span nor 100% selected-span coverage proves semantic sufficiency. Unannotated equivalent evidence can support an answer despite zero location recall. A fully covered gold set can also miss a question constraint if the annotation itself is incomplete.

## 2. Coordinates and ranked context

Evidence is identified by `(document_id, revision, start_char, end_char)`. Offsets are zero-based half-open Unicode **code-point** offsets into immutable canonical text, not bytes or tokens. The quote must equal the canonical slice. A chunk from a different revision never counts.

At K, use exactly the first K saved ranked chunks (K=1,3,5 for the current run). Clip matching intervals to each gold span, then form their union. Adjacent fragments may jointly cover a span; duplicate or overlapping fragments count their positions only once. Do not bridge missing characters merely because two chunks came from adjacent paragraphs. Do not rerank using gold. If fewer than K chunks exist, use those actually returned.

This audit evaluates the saved retrieved text, not any later prompt packing, truncation or model attention. A future context-budget experiment must log the actual retained canonical intervals separately. Embedding truncation and generator-context truncation are different phenomena.

## 3. Per-question scores

For question q with m>0 selected gold spans, let L_i be span length and U_i its covered code-point set.

- `recall_any = mean_i 1[|U_i| > 0]`; `complete_any = AND_i 1[|U_i| > 0]`.
- `recall_full_char = mean_i 1[|U_i| = L_i]`; `complete_full_char = AND_i 1[|U_i| = L_i]`.
- `mean_char_fraction = mean_i |U_i| / L_i`. This is a fraction, not complete-hit rate.
- Let W_i be offsets whose gold characters satisfy `not char.isspace()`. `recall_full_nonspace` and `complete_full_nonspace` use the predicate `W_i subset U_i`; `mean_nonspace_fraction = mean_i |W_i intersect U_i| / |W_i|`.

Whitespace is **exactly Python `str.isspace()`**, with Python version logged. This includes line breaks and Unicode non-breaking spaces. It does not strip punctuation, lowercase, normalize Unicode, remove introductions, or decide whether missing words matter semantically. If any selected span is whitespace-only, all non-whitespace question scores are NA, not perfect; report the reduced valid denominator. If m=0, all evidence-coverage scores are NA; do not let empty conjunctions become successful retrieval.

Example: gold `A\n B!`, with only `A` and `B!` retrieved, has full-character hit 0 and full-non-whitespace hit 1. If `!` is also missing, both full-hit rules return 0. A single-character contact still gives any-overlap hit 1, illustrating why the three rules must not share a label.

## 4. Aggregation and uncertainty

Report each method × expected behavior (`answer`, `correct_premise`) × cohort × K separately. `confirmed_only` uses the frozen first-pass status; `all_annotations` includes its needs_review item. Do not replace these statuses with post-lock review outcomes. Refusal targets have no gold spans and are excluded from evidence-coverage aggregates, with their records retained as NA.

Compute each question score first, then take a macro mean across eligible questions. Each metric records its sum, valid n and mean; `question_n` records the candidate cohort size. Do not micro-average characters, pool K values, or count lexical and topology rows as independent questions. No new significance or causal claim follows from this small shared-document sample.

The any-overlap and strict audits reproduce existing saved scores before adding non-whitespace results. All new output uses a new path and includes input/script hashes. No gold or historical run is rewritten.

## 5. Necessary evidence groups: future annotation contract

A future group corresponds to one necessary fact or constraint. All groups are required (AND). Each group may contain alternative sufficient evidence sets (OR). Within an alternative set, all component spans are required (AND). Thus two snippets from different incomplete alternatives must not be combined and counted as a sufficient alternative without a separate annotation authorizing that combination.

Record group IDs, necessary facts, alternatives, document revisions, coordinates and the semantic rationale before viewing target system outputs. Allow a single span to support more than one group if independently justified. This structure is absent from the current QA schema; it must not be inferred by simply declaring every old span a group. Geometry may verify the location of a selected alternative, but cannot create its semantic sufficiency label.

## 6. Future answer coverage and risk: denominator contract

This section fixes terminology for the next protocol; these metrics are **not computed from the existing prefix-only labels**. On a fixed scheduled question set, define N as all questions including API failures, A as responses making a substantive answer attempt, E as attempted responses with factual error, missing necessary answer content, or unsupported substantive claims, U as attempted responses with unsupported substantive claims, C as corpus-supported response targets (ordinary answers plus evidence-backed premise corrections), V as correct, sufficiently complete and context-supported responses among C, S as questions with independently judged sufficient actual context, and F as pure refusals among S.

| Metric | Numerator / denominator | Zero denominator |
|---|---|---|
| Answer coverage | A / N | NA |
| Selective risk | E / A | NA, including all-refusal systems |
| Unsupported-answer rate | U / N | NA |
| End-to-end valid response rate | V / C | NA |
| False-refusal rate | F / S | NA |
| API/service failure rate | failures / N | NA |

A refusal prefix followed by a substantive correction is an attempt, not a pure refusal. Partial answers count in A and, if necessary content is missing, in E; this prevents omission from artificially lowering risk. A factually correct but unsupported claim counts in U and E. A wrong answer supported only by a misread citation counts in E. A pure refusal has no substantive answer attempt. An API failure without a usable response is neither an answer nor a normal refusal; keep it in N and any applicable C/S denominators and report it separately. Pure refusal when context is insufficient may be locally justified but remains an end-to-end failure on C.

Unknown or contested semantic labels remain missing: report annotation completion and withhold a headline risk rate until labels are complete, or explicitly show best/worst-case bounds. Do not silently drop difficult responses. Show numerator and denominator alongside every rate. Choose thresholds on development data only, log threshold ties and the chosen rule, then apply unchanged on held-out groups. Do not retune to match held-out coverage. Gold coordinates, reference answers, semantic test labels and these offline scores are forbidden runtime gate inputs.

The exact semantic annotation rubric, independent assessment arrangements, grouping/splits, cost budget, A/B/C strategies and thresholds still require the next versioned experimental protocol. This is not a completed selective-answering study.

## 7. Implementation

- Pure span/set calculations: `backend/app/evaluation/coverage.py`.
- Saved-run audit: `python scripts/audit_text_coverage.py --run results/runs/frozen-30-hybrid-rrf-v1.jsonl --output results/audits/<new-path>/text-coverage.json`.
- The original `audit_evidence_coverage.py` and all earlier archived outputs remain available.
- Regression tests check Unicode offsets, overlapping/adjacent intervals, revision mismatch, missing evidence, punctuation, NA behavior, and the actual saved 17-question cohort.
