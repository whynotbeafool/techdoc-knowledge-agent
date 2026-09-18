# Evidence coverage sensitivity audit

Date: 2026-09-11. Post-hoc audit of `frozen-30-hybrid-rrf-v1`; no retrieval rerun or gold edits.

QA SHA-256: `21eb2747289309cb5c17fe0ea5b85744220b246a80f7b0314d430d72f847b975`.
Saved row-file SHA-256: `f2300d926a60215ad9161d63d93afd43a8ef5e6f6bb596eb856002a24536f64d`.

## Procedure

For each gold span, clip the matching document/revision's Top-K chunk intervals to it,
merge overlapping intervals, and count unique covered code points. Strict full coverage
requires the resulting length to equal the gold length. This combines coverage across
chunks and counts overlapping chunks only once. The script verifies the QA hash and
reproduces saved any-overlap Recall and Complete Hit values before reporting sensitivity.
This audit does not recompute MRR or assert semantic answer sufficiency.

Run from the repository root:

```sh
python scripts/audit_evidence_coverage.py --run results/runs/frozen-30-hybrid-rrf-v1.jsonl
```

The JSON output contains both cohorts, both evidence-bearing classes, K=1/3/5, and
each partial-hit case with missing text and non-whitespace character counts.

## Top-5 answerable results

Each cell is any-overlap → strict full-union coverage. Recall is macro-averaged per question.

| Cohort | Method | n | Evidence Recall@5 | Complete Hit@5 |
|---|---|---:|---:|---:|
| confirmed_only | BM25 | 17 | .6471 → .5882 | 8/17 → 6/17 |
| confirmed_only | Dense | 17 | .5588 → .5098 | 7/17 → 5/17 |
| confirmed_only | Hybrid | 17 | .6471 → .6176 | 9/17 → 8/17 |
| all_annotations | BM25 | 18 | .6667 → .5833 | 9/18 → 6/18 |
| all_annotations | Dense | 18 | .5556 → .5093 | 7/18 → 5/18 |
| all_annotations | Hybrid | 18 | .6667 → .6111 | 10/18 → 8/18 |

Top-5 Complete Hit ordering remains Hybrid > BM25 > Dense. The BM25/Hybrid Recall
tie becomes a Hybrid lead under strict coverage. This is specific to this cutoff:
at K=3 in confirmed_only, Dense > Hybrid in any-overlap Recall (.5294 vs .5000)
and remains slightly ahead in strict Recall (.4510 vs .4412); their Complete Hit
advantage becomes a tie (.2353 each). The audit does not support universal Hybrid superiority.

For counter-evidence, Top-5 scores do not change: BM25 and Hybrid fully cover 6/6,
Dense 4/6, in both cohorts. Lower cutoffs do change, as exposed by the script.

## What the missing characters are

| Question/span | Method at K=5 | Covered / gold characters | Missing content |
|---|---|---:|---|
| q005/e001, needs_review | BM25, Hybrid | 107/167 | Sentence opening identifying causal confusion; 50 non-whitespace characters |
| q012/e002 | BM25 | 243/274 | `ts in your stack configuration.`; 27 non-whitespace characters |
| q014/e001 | BM25, Hybrid | 290/292 | Two newline characters only |
| q014/e001 | Dense | 261/292 | `Kubernetes provides you with:` plus whitespace |
| q017/e002 | Dense | 252/254 | Two newline characters only |

Strict character coverage therefore also penalizes whitespace omitted by chunking.
If only these verified whitespace-only gaps are exempted, confirmed-only Top-5
Complete Hit is BM25 7/17, Dense 6/17, Hybrid 9/17. This diagnostic preserves the
ordering but must not be presented as a preregistered replacement metric.
Even non-whitespace absence is not synonymous with missing answer information:
q014's missing introduction illustrates why textual coverage and semantic sufficiency differ.

## Consequences for the paper

Keep the historical any-overlap results explicitly labeled and report this analysis
as post-hoc sensitivity. Do not call every strict-coverage drop a substantive retrieval failure.
Do not change evidence spans to improve a method's results. A future coverage metric
should specify whitespace handling and union coverage before a new run is reported.
The present evidence supports a local Top-5 ordering, not reliable end-to-end failure attribution.
