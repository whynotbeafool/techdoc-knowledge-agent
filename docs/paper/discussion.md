# Discussion

## Retrieval Objectives Can Favor Different Methods

The cutoff and stratum differences in Results favor evaluating several retrieval objectives together. Fusion improves Top-5 complete hits without consistently improving earlier retrieval or preserving the q017-dependent difference in the six-question low-overlap group. Its value therefore depends on the objective and context budget of the downstream system.

Earlier retrieval could matter when a generator receives a short context; hitting additional spans could matter for multi-evidence answers. Neither consequence has been tested here. Hybrid's two retrievers and deeper candidate lists also require a separate cost comparison.

## Evidence Coordinates Enable Audit, Not Automatic Failure Attribution

Immutable evidence coordinates made it possible to audit the hit definition from saved rankings without relabeling questions or rerunning retrieval. The audit distinguishes location contact from character coverage, but neither establishes semantic sufficiency.

Missing whitespace explains some strict-coverage failures, while missing text can range from an incidental introduction to an answer-bearing fragment. The preserved Top-5 ordering supports the local comparison without validating a universal measure of usable evidence.

A stronger downstream analysis would distinguish three observations: which annotated locations were retrieved, which answer-bearing content was available in the assembled context, and whether the generated answer used that content correctly. The present study measures the first and audits textual coverage relevant to the second. Establishing the third requires answer-support judgments. The same distinction applies to false premises: retrieving counter-evidence does not show that a model will correct the premise, and an empty gold set does not demonstrate successful refusal.

# Limitations

## Sampling and Annotation

The dataset contains 30 development questions over five English documents, with no held-out evaluation. Multiple questions share source documents and sometimes evidence, so question count should not be interpreted as an equivalent number of independent domain samples. Equal construction-category quotas are useful for diagnosis but do not estimate deployment frequencies. Lexical strata contain only four to six confirmed answerable questions and differ in document content and evidence topology. Their results describe associations, not the causal effect of wording or proof that construction bias has been removed.

Annotations were produced under a single-annotator protocol, and five pilot records retain an earlier guideline version. A separate AI context completed and locked the planned 14-question second pass on 23 September 2026, after excluding exposed attempts. However, the historical `annotator: self` field does not identify a human or AI model version, so this comparison cannot establish the annotator continuity required for the planned intra-annotator temporal consistency interpretation. Input isolation across AI contexts also does not establish equivalence to a human memory interval. We therefore report AI reannotation consistency, not independent human agreement. The small stratified subset limits generalization; a question-quality agreement rate is unavailable because first-pass dimension labels were not stored. Two topology disagreements expose answer-granularity and alternative-evidence choices, and one second-pass question retains unresolved scope uncertainty. Confirmed status is a protocol judgment, not independently established correctness; repeated agreement can preserve shared bias.

Gold evidence includes selected minimal sufficient spans without exhaustively labeling equivalent occurrences. A system may retrieve an unannotated alternative and receive no credit. Source-text extraction can also omit or distort information even when hashes and offsets are internally consistent. Out-of-scope audits document the search terms and inspected candidates; they cannot prove that no answer exists anywhere in the corpus.

## Experimental and Measurement Scope

The comparison covers one chunking configuration, one dense embedding model, and one fixed fusion configuration. It does not establish the behavior of other dense retrievers, rerankers, or generation baselines. The stored Chroma version identifies the dependency used, but implicit collection settings and the absence of an embedding-artifact checksum limit exact reconstruction of the dense setup. No matched-cost comparison or held-out parameter selection is reported.

A local tokenizer audit on 18 September 2026 reproduced 379 chunks at the frozen 800-character setting. Of these, 59 (15.57%) exceed the ONNX all-MiniLM-L6-v2 input limit of 256 tokens; the longest contains 360 tokens. No annotated gold-evidence characters were found beyond the retained input window in overlapping chunks. This finding does not establish that truncation has no effect on ranking: truncated non-gold content also contributes to candidate representations. The audit uses the currently installed tokenizer and does not supply the missing checksum of the historical embedding artifact (reproduction: `python scripts/audit_embedding_truncation.py`).

A fresh local collection created through the repository retriever under Chroma 1.5.9 reports an `l2` distance space, whereas the ONNX embedder declares `cosine`; a probe embedding is unit-normalised. For unit vectors, squared Euclidean distance equals twice cosine distance, so their exact distance orderings coincide. This algebraic equivalence does not demonstrate identical approximate-nearest-neighbour results, prove that every historical vector was unit-normalised, or retrospectively recover the historical collection settings. Future runs should retain the live `ChromaRetriever.describe()` report alongside their configuration rather than infer the collection metric from the model name.


Any-overlap scoring can overstate textual coverage, while strict coverage can penalize harmless formatting gaps. The latter was examined after inspecting the original scoring rule and is reported as sensitivity analysis, not a retrospectively substituted primary metric. Neither analysis establishes answer correctness, citation support, refusal quality, or reliable end-to-end failure attribution. The method differences remain descriptive observations on this development set.

## Next Validation Steps

The next validation stage should resolve the answer-scope ambiguities and equivalent-evidence choices exposed by reannotation, improve annotator provenance, and obtain independent review without using baseline performance to reshape gold labels. Before evaluating a revised coverage rule, its treatment of whitespace, interval unions, and equivalent evidence should be specified explicitly and versioned. Further experiments should preserve the current artifacts, expand the evaluation beyond the development corpus, capture explicit dense-index and model settings, and assess generated-answer support and expected behavior separately from retrieval scores. These are outstanding validation steps rather than completed contributions.


The historical generation formatter rendered absent text-document pages as `None` (and legacy dense metadata used zero). Reconstructing inputs from saved retrieval rows identifies 23/30 generation cases with at least one unavailable page. Raw assembled prompts were not archived. The current formatter explicitly marks pages as not applicable, but historical generated responses have not been rerun; their citation quality remains unaudited. Refusal-prefix compliance cannot distinguish a generic refusal from a response that begins with that prefix and then corrects a false premise.

The frozen QA's original experimental bytes and the earlier Git blob differ only in seven CRLF-to-LF conversions. Both exact hashes and their provenance are now recorded; arbitrary reserialization is not accepted. Historical configs and locked inputs remain unchanged. Hash checks and later review manifests establish internal integrity, not independent attestation of annotation blindness. Direct dependencies are pinned to the locally tested versions, but transitive dependencies and cross-platform reconstruction are not fully locked. On 23 September 2026, the arXiv sources were pinned to 2005.11401v4 and 2306.16927v3 after their complete PDF hashes matched the frozen source hashes. Local corpus revision v1 must not be confused with arXiv version v1.
