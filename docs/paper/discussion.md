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
