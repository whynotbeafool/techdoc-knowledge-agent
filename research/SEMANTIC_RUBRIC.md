# Semantic judgment rubric — v0.1-dev

Date: 2026-09-28. Applies prospectively to the selective-answering protocol; no original gold labels or locked reannotations are changed. Machine aggregation is implemented, but it does not produce semantic judgments.

## Review order and inputs

1. Corpus pass: read the question and complete frozen corpus, define the scope of a valid answer/correction, necessary facts and allowed alternative evidence sets. Record `corpus_supported` (bool or null). A false premise with sufficient counter-evidence is a supported response target, not automatically a refusal.
2. Context pass: inspect only the question, scope checklist and actual generator-visible context. Record `context_sufficient` (bool or null). Selected-gold overlap is insufficient to assign this label; alternative evidence may suffice. If necessary scope is disputed, use null and record the competing readings.
3. Response pass: inspect question, context, response and evaluation checklist; hide method/threshold/score. Assign behavior and three answer-quality fields below, with rationale and exact supporting or contradicting spans. Evidence can support a claim even if the model omitted a citation; citation correctness is a separate annotation, not inferred by the present scorer.
4. Record reviewer identity/type, review date, rubric version, question/context/response hashes, original judgment and any later adjudication separately. AI-only review stays exploratory. Disagreement does not authorize changing the frozen question to improve agreement.

## Record consumed by the scorer

Required fields: question_id, execution_status (`ok` or `system_error`), behavior, corpus_supported, context_sufficient, correct, complete, supported. All five quality/support labels are boolean or null; use null for unknown, not a guessed false. Score one strategy/cohort at a time with distinct question IDs. The storage record should additionally include strategy, group_id, split, expected_behavior, response hash, reviewer metadata and rationale; these must be validated and linked by a future end-to-end runner.

- `answer`: a substantive attempt at an ordinary answer.
- `correction`: explicitly disputes a false premise and supplies a substantive evidence-based correction. It is an attempt even if it begins with a disclaimer or the historical refusal prefix.
- `partial`: substantive but missing part of the required answer. It counts as attempted; complete=false. A disclaimer plus substantive answer belongs here or answer/correction, not refusal.
- `refusal`: no substantive attempt. Asking for clarification without an answer is a refusal for this protocol, with optional reason metadata.
- `behavior=null`: not yet judged. Never interpret it as refusal.
- `system_error`: no usable generated response due to service/runtime failure. behavior and answer-quality labels must be null; corpus/context labels may still be available.

`correct` evaluates factual accuracy of the substantive response against the defined task/corpus. `complete` requires every necessary answer component, including relevant conditions and counter-premise correction. `supported` requires that all substantive factual claims are warranted by the actual context; general plausibility or a reference number is insufficient. Any unsupported substantive claim makes supported=false. Pure refusals have null answer-quality labels, not true correctness by default.

## Worked decision examples

| Situation | Behavior / quality | Consequence |
|---|---|---|
| Refusal marker followed by a complete grounded premise correction | correction; true/true/true | Attempt and valid response; no prefix-based penalty |
| Correct response to only one of two required parts | partial; true/false/true | Attempt with selective error due to incompleteness |
| Factually correct claim absent from current context | answer; true/true/false | Selective error and unsupported-answer event |
| Wrong value accompanied by an existing citation | answer; false/(judge separately)/false if citation does not entail value | Citation presence does not rescue it |
| Pure refusal despite sufficient context | refusal; null/null/null | False-refusal event and end-to-end failure |
| Pure refusal because retrieval missed evidence present in corpus | refusal; null/null/null; corpus=true/context=false | Locally defensible, still end-to-end failure |
| API timeout on a corpus-supported question | system_error; behavior=null | Service failure; remains in scheduled and corpus denominators |
| Reviewer cannot resolve intended scope | applicable labels=null | Preserve row; affected metrics withheld |

The scorer withholds a rate if its numerator/denominator depends on missing labels. It may still report an independently determined metric: for example, a known factual error is an error even if completeness is unknown. Every rate includes its known denominator and missing-label count; a zero denominator yields null. No synthetic unit-test judgments may be copied into study outputs.

Current q010's unspecified exception scope and q021's unspecified latency setup remain documented unresolved cases. Neither is silently adjudicated by the new scoring code.
