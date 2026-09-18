# Results

We report the saved three-method run `frozen-30-hybrid-rrf-v1`. Unless specified otherwise, results use confirmed annotations and the original any-positive-overlap hit rule. Recall refers to Evidence Recall, and Complete Hit means that every selected gold span is overlapped, not necessarily fully retrieved. The coverage analysis below is a post-hoc sensitivity check on the same ranked lists.

## Overall Retrieval and Annotation Sensitivity

On the 17 confirmed answerable questions, BM25 and Hybrid tie in Recall@5 at 0.6471, while Dense reaches 0.5588. Hybrid has the highest Complete Hit@5, reaching 9/17 questions compared with BM25's 8/17 and Dense's 7/17. This net gain comes with a ranking trade-off: Hybrid's Recall@3 is 0.5000 versus BM25's 0.6471, and its MRR@5 is 0.6147 versus 0.6667. Fusion therefore improves one aggregate measure at the larger cutoff without consistently improving earlier evidence retrieval.

| Cohort | Method | n | Recall@1 | Recall@3 | Recall@5 | Complete Hit@5 | MRR@5 |
|---|---|---:|---:|---:|---:|---:|---:|
| confirmed_only | BM25 | 17 | 0.4118 | 0.6471 | 0.6471 | 0.4706 | 0.6667 |
| confirmed_only | Dense | 17 | 0.3529 | 0.5294 | 0.5588 | 0.4118 | 0.5706 |
| confirmed_only | Hybrid | 17 | 0.4118 | 0.5000 | 0.6471 | 0.5294 | 0.6147 |
| all_annotations | BM25 | 18 | 0.4167 | 0.6667 | 0.6667 | 0.5000 | 0.6852 |
| all_annotations | Dense | 18 | 0.3333 | 0.5278 | 0.5556 | 0.3889 | 0.5667 |
| all_annotations | Hybrid | 18 | 0.4167 | 0.5278 | 0.6667 | 0.5556 | 0.6361 |

Including the unresolved question preserves the Top-5 Recall tie between BM25 and Hybrid and the Complete Hit and MRR orderings. It does alter the smaller-cutoff comparison: Dense and Hybrid tie in Recall@3 under all annotations, whereas Dense is slightly ahead under confirmed annotations. The second cohort exposes this sensitivity; it does not independently validate the annotations.

## Evidence Topology and Lexical Overlap

The marginal breakdowns reveal variation hidden by overall means. Dense has higher Recall@5 on confirmed multi-hop questions than BM25 or Hybrid (0.6000 versus 0.5000), but all three overlap every selected span for only one of five questions. Retrieving some evidence for a dependent question therefore remains distinct from hitting its entire annotated set.

| Axis | Stratum | n | BM25 Recall@5 | Dense Recall@5 | Hybrid Recall@5 |
|---|---|---:|---:|---:|---:|
| Evidence topology | Single evidence | 6 | 0.6667 | 0.3333 | 0.6667 |
| Evidence topology | Multiple parallel evidence | 6 | 0.7500 | 0.7500 | 0.7500 |
| Evidence topology | Multi-hop | 5 | 0.5000 | 0.6000 | 0.5000 |
| Lexical overlap | Low | 6 | 0.3333 | 0.5000 | 0.3333 |
| Lexical overlap | Medium | 5 | 0.7000 | 0.4000 | 0.6000 |
| Lexical overlap | High | 4 | 0.8750 | 0.6250 | 1.0000 |

Dense exceeds BM25 in the low-overlap group, whereas BM25 exceeds Dense in the medium- and high-overlap groups. Hybrid does not inherit Dense's low-overlap advantage at Top-5, despite combining both candidate lists. These observations motivate retaining stratified reports, but do not isolate a causal effect of lexical overlap: questions differ in document and evidence topology as well as wording. Cells contain only four to six questions. The lexical rows cover 15 confirmed answerable questions, excluding two legacy confirmed questions with no recorded lexical score; they must not be summed with topology rows or interpreted as a crossed design.

## Counter-Evidence Retrieval

On six false-premise questions, BM25 and Hybrid achieve Complete Hit@5 of 1.0000, while Dense reaches 0.6667. BM25 retrieves the first overlapping counter-evidence earlier on average than Hybrid, with MRR@5 of 0.9167 versus 0.8750. Both annotation cohorts contain the same six records.

| Method | n | Recall@1 | Recall@3 | Recall@5 | Complete Hit@5 | MRR@5 |
|---|---:|---:|---:|---:|---:|---:|
| BM25 | 6 | 0.8333 | 1.0000 | 1.0000 | 1.0000 | 0.9167 |
| Dense | 6 | 0.6667 | 0.6667 | 0.6667 | 0.6667 | 0.6667 |
| Hybrid | 6 | 0.8333 | 0.8333 | 1.0000 | 1.0000 | 0.8750 |

These scores concern locating counter-evidence. They do not show that a generated answer corrects the premise. The six out-of-scope questions have no gold spans and are excluded from these retrieval aggregates; refusal performance cannot be inferred from this run.

## Sensitivity to the Evidence-Hit Definition

A post-hoc audit merged retrieved intervals within each gold span and required every gold character to be covered. Under this stricter rule, confirmed-question Complete Hit@5 falls from 8/17 to 6/17 for BM25, from 7/17 to 5/17 for Dense, and from 9/17 to 8/17 for Hybrid. The ordering is preserved, while the BM25/Hybrid Recall@5 tie becomes a Hybrid lead. Both cohorts are shown below; no retrieval or annotation was rerun for this comparison.

| Cohort | Method | n | Strict Recall@5 | Strict Complete Hit@5 |
|---|---|---:|---:|---:|
| confirmed_only | BM25 | 17 | 0.5882 | 6/17 |
| confirmed_only | Dense | 17 | 0.5098 | 5/17 |
| confirmed_only | Hybrid | 17 | 0.6176 | 8/17 |
| all_annotations | BM25 | 18 | 0.5833 | 6/18 |
| all_annotations | Dense | 18 | 0.5093 | 5/18 |
| all_annotations | Hybrid | 18 | 0.6111 | 8/18 |

The strict rule also penalizes formatting gaps: BM25 and Hybrid omit only two newline characters from one q014 span at Top-5, and Dense similarly omits two newlines from a q017 span. Exempting these verified whitespace-only gaps yields confirmed Complete Hit counts of 7/17, 6/17, and 9/17 for BM25, Dense, and Hybrid respectively. Other gaps contain text, such as BM25's missing tail of a q012 quotation. Text loss itself does not establish loss of an essential answer component; conversely, any-overlap success cannot establish evidence sufficiency. Counter-evidence Top-5 scores are unchanged by strict coverage. The audit therefore bounds the interpretation of the original scores rather than replacing them with a retrospectively selected primary metric.

These are descriptive results from a small development corpus, without a held-out generalization test or statistical significance claim. They identify cutoff- and stratum-dependent retrieval trade-offs, while leaving generated-answer support and refusal behavior to separate evaluation.
