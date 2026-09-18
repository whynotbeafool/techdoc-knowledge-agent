# Introduction

In technical-document question answering, a useful retrieval result must supply information needed for the particular question. A passage may mention the right topic without stating the required fact, and one relevant passage may leave another required answer component missing. Evaluating retrieval therefore requires an explicit account of the evidence being sought and of the rule used to credit a retrieved passage.

We draw on domain benchmarks, RAG diagnostics, retrieval evaluation, and multidimensional factuality annotation to examine a fixed English technical-document corpus. Evidence is anchored to immutable character coordinates, allowing comparisons against the same selected spans when chunk boundaries change. Related Work develops these design connections.

The evaluation contains 30 development questions covering single-evidence, parallel multi-evidence, multi-hop, out-of-scope, and false-premise categories. It records supporting or contradicting spans, version-1 exclusion searches, lexical-overlap strata, and annotation uncertainty.

The current experiment addresses three questions: how BM25, Dense, and rank fusion compare at different retrieval cutoffs; how their results vary across evidence topology and lexical overlap; and how changing the evidence-hit definition affects interpretation. It evaluates retrieval of supporting and counter-evidence. The behavior labels additionally define future generation targets, but this experiment does not test whether a model answers faithfully, refuses appropriately, or corrects a false premise.

Fusion achieves more Top-5 complete hits than BM25 but lower Recall@3 and MRR@5; Dense performs better in the low-overlap stratum. A post-hoc audit further separates evidence-location hits from full character coverage. These observations motivate the study's three contributions: a traceable pilot protocol, a controlled retrieval comparison, and a coverage sensitivity analysis.
