---
title: "Evidence-Anchored Retrieval Evaluation for Technical Documents: A Pilot Study"
bibliography: references.bib
---

<!-- Generated reading copy, 2026-09-11. Edit the section files and regenerate this copy. -->

# Abstract

Retrieval evaluation for technical-document question answering depends on both which evidence is annotated and what counts as retrieving it. We present a pilot evaluation over five frozen English documents and 30 development questions, with character-offset evidence, separate answer/refusal/correction targets, lexical-overlap strata, and explicit annotation uncertainty. BM25, dense retrieval, and reciprocal-rank fusion share 379 chunks. On 17 confirmed answerable questions, BM25 and fusion tie in Evidence Recall@5 at 0.6471; fusion overlaps every selected gold span for 9 questions versus BM25's 8, but has lower Recall@3 and MRR@5. Dense retrieval performs better in the small low-overlap stratum. A post-hoc audit shows that requiring full character coverage lowers complete-hit counts to 6, 5, and 8 for BM25, Dense, and fusion, respectively, partly because chunking omits whitespace. These results expose cutoff-dependent retrieval trade-offs and the distinction between evidence-location hits and textual coverage. The study provides an auditable development evaluation, while single-annotator data, incomplete labeling of equivalent evidence, and absent answer-support evaluation limit generalization and downstream failure attribution.

# Introduction

In technical-document question answering, a useful retrieval result must supply information needed for the particular question. A passage may mention the right topic without stating the required fact, and one relevant passage may leave another required answer component missing. Evaluating retrieval therefore requires an explicit account of the evidence being sought and of the rule used to credit a retrieved passage.

We draw on domain benchmarks, RAG diagnostics, retrieval evaluation, and multidimensional factuality annotation to examine a fixed English technical-document corpus. Evidence is anchored to immutable character coordinates, allowing comparisons against the same selected spans when chunk boundaries change. Related Work develops these design connections.

The evaluation contains 30 development questions covering single-evidence, parallel multi-evidence, multi-hop, out-of-scope, and false-premise categories. It records supporting or contradicting spans, version-1 exclusion searches, lexical-overlap strata, and annotation uncertainty.

The current experiment addresses three questions: how BM25, Dense, and rank fusion compare at different retrieval cutoffs; how their results vary across evidence topology and lexical overlap; and how changing the evidence-hit definition affects interpretation. It evaluates retrieval of supporting and counter-evidence. The behavior labels additionally define future generation targets, but this experiment does not test whether a model answers faithfully, refuses appropriately, or corrects a false premise.

Fusion achieves more Top-5 complete hits than BM25 but lower Recall@3 and MRR@5; Dense performs better in the low-overlap stratum. A post-hoc audit further separates evidence-location hits from full character coverage. These observations motivate the study's three contributions: a traceable pilot protocol, a controlled retrieval comparison, and a coverage sensitivity analysis.

# Related Work

## Vertical-Domain LLM Capability Benchmarks

Vertical-domain LLM benchmarks decompose domain competence into structured task suites. FinBen spans 42 datasets, 24 tasks, and eight aspects of finance [@xie2024finben]. In Chinese college admissions, DomainRAG defines six capability types and compares closed-book, gold-reference, and retrieved-reference settings, with BM25-based retrieval generally yielding stronger downstream results than BGE-base-zh-v1.5 [@wang2024domainrag]. These benchmarks characterize system-level capabilities; FinBen's Regulations evaluation, for example, reports answer-level metrics [@xie2024finben]. The present setting instead calls for controlled retriever comparison using independently annotated evidence spans anchored to character offsets. DomainRAG provides a close reference for domain-specific evaluation, while addressing a broader set of end-to-end capabilities.

## Reference-Free and Generation-Integrated RAG Diagnostics

RAG diagnostics distinguish context quality, answer faithfulness, and retrieval decisions. RAGAS uses reference-free metrics for faithfulness, answer relevance, and context relevance [@es2024ragas]. Self-RAG trains the generator to emit reflection tokens indicating whether retrieval is needed, whether retrieved evidence is relevant, whether the output is supported, and its overall utility [@asai2024selfrag]. Both explicitly assess retrieved context, although Self-RAG is a training-and-generation framework rather than an evaluation metric. These judgments offer useful diagnostics but do not themselves supply an independently annotated required evidence set. In the present protocol, character-offset gold evidence enables measurement of whether retrieved chunks overlap annotated evidence locations. This supplies a retrieval diagnostic, but the current any-overlap hit rule does not establish complete content coverage or correct downstream evidence use.

## Retrieval Benchmarks and Annotation Bias

On the retrieval side, BEIR provides a methodological reference through 18 heterogeneous datasets and a common corpus/query/qrels format. Its comparison of lexical, sparse, dense, late-interaction, and reranking methods finds BM25 to be a robust baseline, with dense retrieval not consistently superior [@thakur2021beir]. Its focus is cross-domain zero-shot retrieval; the present task configuration additionally distinguishes refusal and false-premise correction. BEIR studies annotation selection bias and supplements TREC-COVID judgments with 980 query-document annotations, showing how incomplete pools can disadvantage other retrieval systems [@thakur2021beir, sec. 6]. Our protocol annotates evidence independently of baseline outputs and separately uses lexical-overlap quotas to address wording-based advantages for BM25. These measures address pooling bias and query-construction bias respectively, without establishing that annotation is bias-free.

## Multidimensional Human Factuality Annotation

Factuality evaluation can decompose holistic judgments into observable dimensions. TreatFact comprises 170 summaries generated from 85 clinical-study abstracts, annotated by four evidence-based medicine experts for PICO elements, conclusion direction, claim strength, and other inconsistencies, alongside a 0–3 overall score [@luo2024factual]. On the 78 double-annotated summaries, dimension-level agreement was 0.73–0.94, compared with 0.55 for overall factual-consistency agreement [@luo2024factual, appendix C.1]. This contrast motivates recording inspectable annotation decisions separately, although it does not establish that decomposition universally improves reliability. TreatFact compares summaries with supplied sources and contains no retrieval step. It therefore informs our annotation design: evidence topology, expected behavior, and character-offset evidence sets are recorded separately, while lexical-overlap strata serve the distinct purpose of controlling retrieval-comparison bias.

## Synthesis

Together, these studies motivate a focused evaluation protocol for a fixed technical-document corpus. The protocol combines capability decomposition, independently annotated character-offset evidence, and controlled retrieval comparison. It records complete evidence sets where answers or counter-evidence exist, alongside explicit search audits for out-of-scope questions. Expected behaviors distinguish answering, refusal, and false-premise correction; retrieval results are separately stratified by evidence topology and lexical overlap. Current evaluation measures retrieval against this evidence standard, providing a basis for later generation-side diagnosis. The contribution is the combination of these controls in the specified setting; broader generalization remains to be evaluated.

# Methods

## Frozen Corpus and Evidence Coordinates

We use a fixed corpus of five English technical documents: two research papers, the FastAPI first-steps guide, the Kubernetes overview, and PEP 8. Questions and reference answers are also in English. This small corpus supports controlled comparisons but is not a representative sample of technical documentation. An explicit active-revision list selects one immutable canonical-text artifact per document; historical revisions remain available but are excluded from the active corpus.

Source documents are converted to NFC-normalized canonical text stored in UTF-8. The manifest records SHA-256 hashes of the source and canonical text, extraction-tool versions, normalization rules, and page spans. PDF extraction used pypdf 6.14.2. Each evidence span is identified by `(document_id, revision, start, end)`, where `[start, end)` is a zero-based, half-open interval measured in Unicode code points. Its stored quotation must exactly match the corresponding text slice; PDF page numbers provide an additional inspection aid.

Gold evidence is thus independent of chunk identifiers: changing chunk boundaries preserves the reference coordinates within the same canonical revision. Changes to canonical text require a new revision and revalidation of evidence coordinates. Evaluation chunks are exact contiguous slices that do not cross PDF page boundaries. They need not cover every character, since trimmed whitespace and page separators may be omitted. These checks preserve coordinate integrity without guaranteeing that text extraction retains all source semantics.

## Question Construction and Annotation

The frozen development set contains 30 questions, with six in each construction category: single-evidence answering, multi-evidence answering, multi-hop answering, out-of-scope refusal, and false-premise correction. All questions are development examples; there is no held-out test set. The five pilot questions retain their original guideline version, while the subsequent 25 follow version 1. This provenance is retained rather than presenting all records as newly annotated under a uniform protocol.

Answerability is judged relative to the frozen corpus. Ordinary answerable questions require supporting evidence and a reference answer. False-premise questions require counter-evidence and a corrective reference answer: they cannot be answered as phrased, but should elicit correction rather than generic refusal. Out-of-scope questions have no gold evidence or reference answer and are assigned refusal as the expected behavior.

For questions with evidence, the protocol selects a minimal sufficient set of spans supporting the required answer components or contradicting the premise. Multi-evidence questions combine parallel answer components without a necessary dependency. A multi-hop question instead requires an intermediate entity, attribute, or value established by one span to connect to another. If the question already supplies that bridge, the dependency does not qualify. These labels describe evidence relationships, independently of chunk counts or a retriever's search path. Repeated or equivalent supporting passages are not exhaustively annotated; consequently, missing the selected gold spans does not by itself establish that retrieved text cannot support the answer.

For new out-of-scope questions, version 1 requires a search audit containing query terms and plausible synonyms, abbreviations, or broader terms, together with at least one inspected candidate and an explanation of why it does not answer the question. Candidate passages are exclusion checks, not gold evidence. This audit documents an unsuccessful search within the corpus rather than proving that an answer cannot exist.

Version 1 separates judgments of question quality, corpus support, evidence topology, reference-answer sufficiency, and evidence sufficiency. Expected behavior is derived from the support category; lexical overlap is computed after the question and evidence are finalized. Unresolved annotation uncertainty is recorded as `needs_review`, with its reason logged separately. Automatic checks validate field combinations, interval bounds, and exact quotation matches, while semantic sufficiency remains a judgment requiring review.

## Lexical Stratification and Quality Control

To reduce wording-based advantages for lexical retrieval, question construction uses predefined lexical-overlap quotas. Let Q be the set of distinct content tokens in a question and E the corresponding set across its gold quotations. Both are obtained by lowercasing, matching `[A-Za-z0-9_]+`, and removing the fixed stopword list in the released validator. Overlap is |Q ∩ E| / |Q|, rounded to four decimal places; an empty Q receives 0. The resulting score defines low (<0.25), medium (0.25–<0.50), and high (≥0.50) strata. The score measures token overlap, not semantic difficulty.

The quotas apply to the 20 evidence-bearing questions among the 25 version-1 additions, including false-premise questions, and yield 7 low-, 7 medium-, and 6 high-overlap examples. The five new refusal questions have no gold evidence and receive no overlap score. The five legacy pilot records also lack this field. Thus, lexical strata do not partition the full dataset: even legacy evidence-bearing questions remain outside lexical cells. Within each applicable question class and annotation cohort, retrieval results are broken down separately by evidence topology and lexical overlap, with sample counts reported for every cell. We do not cross the two axes at this sample size.

Primary results use `confirmed_only`; sensitivity results use `all_annotations`, retaining unresolved records. The frozen dataset contains 29 confirmed questions and one `needs_review` question, but these totals are not the denominators of every metric: each report additionally filters by question class and stratum. Evidence annotation is kept separate from baseline outputs, and baseline performance must not be used to revise gold labels. Lexical quotas mitigate one construction risk without establishing that the comparison is free of annotation bias.

The dataset uses a single-annotator protocol. A deterministic, stratified subset of 14 questions was selected for delayed self-reannotation, covering all five construction categories and corpus documents. The planned second pass provides only questions and frozen source text, hiding initial answers, evidence coordinates, labels, quality-control status, and baseline outputs. It begins no earlier than 14 days after the latest initial annotations. Subsequent agreement will be assessed by annotation dimension and reported as intra-annotator temporal consistency, not inter-annotator agreement. As of 11 September 2026, the designated record file contains only two earlier adjudications, excluded from the formal subset; the planned 14-question pass has no recorded results.

## Retrieval Systems and Experimental Controls

The three-method comparison uses run `frozen-30-hybrid-rrf-v1`, which contains 30 question-level records for each of BM25, Dense, and Hybrid-RRF. All methods operate on the same 379 chunks from the five active canonical revisions. Chunking groups adjacent paragraphs within a page up to 800 Unicode code points, splits overlong paragraphs at that limit, and adds no overlap. Where double-newline splitting yields at most one paragraph, the implementation falls back to single-newline segmentation. The 800-character limit is not a token budget.

Our BM25 baseline follows the probabilistic relevance framework [@robertson2009bm25], with k1 = 1.5 and b = 0.75. Its tokenizer lowercases text and extracts `[A-Za-z0-9_]+` matches, retaining stopwords and repeated query terms. This differs from the set-based, stopword-filtered calculation used only for lexical stratification. BM25 score ties are resolved by chunk identifier.

Dense retrieval uses Chroma's `DefaultEmbeddingFunction`, recorded as `all-MiniLM-L6-v2`, with Chroma 1.5.9 and Python 3.13.5. The named sentence encoder is documented in the Sentence Transformers model card [@sentenceTransformersModelCard]; its MiniLM backbone derives from self-attention distillation [@wang2020minilm]. These references describe the model lineage and do not identify the exact downloaded Chroma artifact. Each run builds a fresh temporary Chroma store from the common chunks to avoid stale index entries. The implementation leaves collection distance and index settings at their Chroma defaults; these settings and the embedding artifact checksum are not explicitly captured in the run configuration, limiting the completeness of the reproducibility record.

Hybrid-RRF uses reciprocal rank fusion [@cormack2009rrf]. Our implementation requests the top 20 candidates from each component and assigns a chunk the sum of 1 / (60 + r) over the lists containing it, where r starts at 1. Both components have equal weight; absence from a candidate list contributes zero. Candidates are merged by chunk identifier, ordered by the fused score, and truncated to five; ties use chunk identifiers. Fusion combines ranks rather than the components' differently scaled raw scores. The candidate depth and rank constant are fixed for this run, without a reported parameter sweep.

All three methods return a ranked top-five list, evaluated at cutoffs 1, 3, and 5. The run records the question-file hash, active-revision-list hash, canonical text hashes, software versions, and retrieval parameters; annotation validation and active-revision compatibility checks precede evaluation. These controls align inputs but do not equalize computational cost: Hybrid consults both retrievers at a larger candidate depth. This comparison includes neither reranking nor long-context or no-retrieval generation baselines, and does not establish their relative performance.

## Metrics and Reporting

For a question q with a nonempty gold set G(q), let h(e, c) indicate that evidence span e and retrieved chunk c belong to the same document and canonical revision and have positive-length interval overlap. Specifically, h = 1 when max(e.start, c.start) < min(e.end, c.end); touching boundaries do not count. This is an any-overlap criterion: even one overlapping code point is sufficient. It requires neither containment of the full evidence span nor a minimum coverage fraction, and does not calculate the union of coverage across chunks.

Let H_K(e) be 1 if any of the first K retrieved chunks hits e, and 0 otherwise. Per-question Evidence Recall@K is the sum of H_K(e) over G(q), divided by |G(q)|. Each gold span contributes at most once, regardless of how many chunks hit it; one chunk may hit multiple spans. Complete Evidence Hit@K is 1 if every gold span is hit and 0 otherwise. Under this definition, “complete” refers to hitting all annotated spans, not retrieving their complete textual content. For example, a chunk covering [199, 220) hits gold [100, 200), despite covering only its last character. The metric therefore measures contact with annotated evidence locations and cannot establish that the retrieved context is sufficient to answer.

Reciprocal Rank@5 is 1/r for the first chunk at rank r ≤ 5 that hits any gold span, or 0 when none does. MRR@5 is its question-level macro-average. Evidence Recall and Complete Evidence Hit are likewise macro-averaged across eligible questions; they are not pooled over all evidence spans. We report cutoffs 1, 3, and 5 for the latter two metrics. nDCG is not computed in the selected run.

Ordinary answerable questions and false-premise questions are summarized separately, with the latter measuring retrieval of counter-evidence. In the selected run, their overall denominators are respectively 17 and 6 under `confirmed_only`, and 18 and 6 under `all_annotations`. The six out-of-scope questions have empty gold sets and receive null retrieval metrics, rather than zeros or vacuous complete hits. Their ranked lists alone do not measure refusal accuracy; that requires generated responses and a separate behavior evaluation.

Every method/class/cohort/stratum cell reports its sample count. Non-null question-level values are averaged and rounded to four decimal places; empty cells have null metrics. Rankings and differences are interpreted within this small development set, with both annotation cohorts retained to expose sensitivity to unresolved labels. Two limitations constrain downstream conclusions: equivalent evidence occurrences are not exhaustively annotated, and partial overlap counts as a hit. Thus, neither a missed gold span nor a complete-hit score alone establishes whether an answer can be supported. Stronger content-coverage measures and answer-support judgments are needed for that diagnosis.

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

# Discussion

## Retrieval Objectives Can Favor Different Methods

The cutoff and stratum differences in Results favor evaluating several retrieval objectives together. Fusion improves Top-5 complete hits without consistently improving earlier retrieval or preserving Dense's low-overlap advantage. Its value therefore depends on the objective and context budget of the downstream system.

Earlier retrieval could matter when a generator receives a short context; hitting additional spans could matter for multi-evidence answers. Neither consequence has been tested here. Hybrid's two retrievers and deeper candidate lists also require a separate cost comparison.

## Evidence Coordinates Enable Audit, Not Automatic Failure Attribution

Immutable evidence coordinates made it possible to audit the hit definition from saved rankings without relabeling questions or rerunning retrieval. The audit distinguishes location contact from character coverage, but neither establishes semantic sufficiency.

Missing whitespace explains some strict-coverage failures, while missing text can range from an incidental introduction to an answer-bearing fragment. The preserved Top-5 ordering supports the local comparison without validating a universal measure of usable evidence.

A stronger downstream analysis would distinguish three observations: which annotated locations were retrieved, which answer-bearing content was available in the assembled context, and whether the generated answer used that content correctly. The present study measures the first and audits textual coverage relevant to the second. Establishing the third requires answer-support judgments. The same distinction applies to false premises: retrieving counter-evidence does not show that a model will correct the premise, and an empty gold set does not demonstrate successful refusal.

# Limitations

## Sampling and Annotation

The dataset contains 30 development questions over five English documents, with no held-out evaluation. Multiple questions share source documents and sometimes evidence, so question count should not be interpreted as an equivalent number of independent domain samples. Equal construction-category quotas are useful for diagnosis but do not estimate deployment frequencies. Lexical strata contain only four to six confirmed answerable questions and differ in document content and evidence topology. Their results describe associations, not the causal effect of wording or proof that construction bias has been removed.

Annotations were produced under a single-annotator protocol, and five pilot records retain an earlier guideline version. The planned 14-question delayed reannotation has no recorded results as of 11 September 2026. Even after completion, it would measure temporal consistency within an annotator, not agreement between independent annotators. Confirmed status represents a resolved protocol judgment, not independently established correctness. Reporting both annotation cohorts exposes sensitivity to the unresolved record but cannot measure unrecognized errors in confirmed records.

Gold evidence includes selected minimal sufficient spans without exhaustively labeling equivalent occurrences. A system may retrieve an unannotated alternative and receive no credit. Source-text extraction can also omit or distort information even when hashes and offsets are internally consistent. Out-of-scope audits document the search terms and inspected candidates; they cannot prove that no answer exists anywhere in the corpus.

## Experimental and Measurement Scope

The comparison covers one chunking configuration, one dense embedding model, and one fixed fusion configuration. It does not establish the behavior of other dense retrievers, rerankers, or generation baselines. The stored Chroma version identifies the dependency used, but implicit collection settings and the absence of an embedding-artifact checksum limit exact reconstruction of the dense setup. No matched-cost comparison or held-out parameter selection is reported.

Any-overlap scoring can overstate textual coverage, while strict coverage can penalize harmless formatting gaps. The latter was examined after inspecting the original scoring rule and is reported as sensitivity analysis, not a retrospectively substituted primary metric. Neither analysis establishes answer correctness, citation support, refusal quality, or reliable end-to-end failure attribution. The method differences remain descriptive observations on this development set.

## Next Validation Steps

The next validation stage should complete the predefined delayed reannotation, report dimension-level disagreements, and document any adjudication without using baseline performance to reshape gold labels. Before evaluating a revised coverage rule, its treatment of whitespace, interval unions, and equivalent evidence should be specified explicitly and versioned. Further experiments should preserve the current artifacts, expand the evaluation beyond the development corpus, capture explicit dense-index and model settings, and assess generated-answer support and expected behavior separately from retrieval scores. These are outstanding validation steps rather than completed contributions.

# Conclusion

This pilot study combines frozen technical documents, character-offset evidence, explicit question categories, and stratified reporting to compare BM25, Dense, and rank fusion on a common development set. The results reveal a trade-off between earlier evidence retrieval and Top-5 complete hits, with method differences also varying across lexical strata. Auditing the saved intervals further shows that contact with all gold spans, complete character coverage, and semantic sufficiency are distinct properties. The evaluation supports local retrieval comparisons and inspection of scoring assumptions; it does not establish a universally preferable retriever or successful downstream answering. Further validation requires completing the planned annotation review, specifying richer coverage rules prospectively, and evaluating answer support and expected behavior beyond the current development setting.
