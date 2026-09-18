---
bibliography: references.bib
---

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
