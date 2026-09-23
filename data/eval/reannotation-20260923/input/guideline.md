# Annotation rules v1 — normative-only transcription

This document contains field definitions and annotation rules only. It contains no historical examples, per-question labels, sampling quotas, experiment outcomes, or first-pass judgments. Apply these rules to each question independently.

## Independent judgments

A. Question quality: Is the wording clear, natural, bounded, and free of equally reasonable interpretations with materially different answers? Preserve the supplied question even if unclear, and record uncertainty.
B. Corpus support: Can the frozen canonical corpus support the requested answer? Distinguish ordinary support, an explicitly falsifiable premise, and information outside the corpus.
C. Evidence topology: Decide from the minimal sufficient evidence, independently of chunk boundaries or a search path.
D. Answer sufficiency: Every substantive component of the reference answer must be supported by the corpus; include every component required by the question and necessary qualifications.
E. Evidence sufficiency: Select minimal sufficient, precisely locatable evidence. For out-of-scope cases, perform and document a reproducible exclusion search.

Record all five separately before deriving expected_behavior, lexical_overlap and annotation_status. Never start from an overall quality score and adjust other judgments to match it. Any unresolved uncertainty makes annotation_status needs_review. Record hesitation reasons rather than forcing confirmed.

## Required JSONL schema

Each line is a JSON object with:
- schema_version: "0.3"; guideline_version: "1".
- question_id and question: exact supplied ID and English text; do not rewrite.
- answerability: "answerable" or "unanswerable".
- unanswerable_reason: null, "out_of_scope", or "false_premise".
- expected_behavior: derived mapping below.
- reasoning_type: "single_evidence", "multi_evidence", "multi_hop", or "not_applicable".
- reference_answer: concise English answer/correction, or null for out_of_scope.
- evidence: evidence objects, or [] for out_of_scope.
- unanswerable_search: null except for out_of_scope; see below.
- lexical_overlap: computed object for evidence-bearing records, otherwise null.
- annotation_status: "confirmed" or "needs_review".
- split: "dev".
- annotator: truthful AI main-assistant identity, not a claim of human annotation.
- created_at: actual YYYY-MM-DD of annotation.

Mapping:
- Ordinary supported answer: answerability=answerable; unanswerable_reason=null; expected_behavior=answer; nonempty reference_answer and evidence; unanswerable_search=null.
- Out of scope: answerability=unanswerable; unanswerable_reason=out_of_scope; expected_behavior=refuse; reasoning_type=not_applicable; reference_answer=null; evidence=[]; lexical_overlap=null; nonempty search audit.
- Falsifiable premise: answerability=unanswerable; unanswerable_reason=false_premise; expected_behavior=correct_premise; nonempty corrective reference_answer and counter-evidence; unanswerable_search=null; topology determined by evidence needed for correction. Do not merely refuse when the corpus directly contradicts the premise.

## Evidence selection

Use only canonical corpus text, not outside knowledge. A passage must directly state a necessary answer component or contradict a false premise; a topic mention, reference entry, contents entry, or unsupported extrapolation is insufficient. Exclude answers requiring images, complex table interpretation, or layout; record the difficulty.

Select the minimum sufficient evidence set, not all repeated or equivalent occurrences. Keep complete semantic units with necessary qualifications, usually complete sentences. About 300 characters is a suggested maximum per quotation; longer complete units are allowed with a documented reason. Do not join noncontiguous passages into an interval containing unrelated text. When identical quotes occur repeatedly, choose the occurrence deliberately; do not silently accept the first find() match.

Evidence objects have evidence_id (e001, e002, ... unique within each question), document_id, revision, page, start_char, end_char, quote. document_id/revision must match an active corpus document. page must match the page span containing start_char (null for plain text). Offsets are zero-based half-open Unicode-code-point positions in canonical text, equivalent to Python str indexing, not byte offsets. Require 0 <= start_char < end_char <= len(text) and text[start_char:end_char] == quote. Never use chunk_id as evidence anchor.

## Topology

- single_evidence: one passage directly supports the required answer.
- multi_evidence: multiple parallel passages support distinct answer components, with no necessary information dependency.
- multi_hop: an intermediate entity, attribute or value supplied by one passage is necessary to connect another passage when composing the answer. Several passages alone do not establish multi_hop. If the question already provides the bridge, or the passages simply fill parallel answer components, use multi_evidence. A possible multi-step search path is not proof of a necessary dependency. Topology is independent of chunk counts and retrieval performance.
- not_applicable: out-of-scope cases only.

## Out-of-scope audit

Search all active corpus documents using original terms, likely abbreviations/full forms, synonyms and broader concepts. Zero literal matches alone is insufficient. Browse semantically related material and inspect at least one relevant candidate. unanswerable_search contains searched_terms (nonempty string array) and candidate_checks (nonempty array). Each candidate has document_id, revision, start_char, end_char, quote and reason_not_answer. Candidate offsets/quotes must also be exact. These are exclusion-audit candidates, never gold evidence. State only that the documented search did not find sufficient support, not a logical proof of absence.

## Derived lexical overlap

Use lexical-rule.json: lowercase [A-Za-z0-9_]+ tokens, remove the fixed stopwords, use unique token sets. The numerator counts question content tokens appearing in any selected evidence quote; the denominator counts question content tokens. Empty denominator gives 0. Round to four decimals, then label low below 0.25, medium from 0.25 inclusive to 0.50 exclusive, high at least 0.50. Store metric="question_content_token_recall_in_evidence", score and stratum. Do not change a question or evidence to target a stratum.

## Completion discipline

Read only the allowed input package. Write separate five-dimension judgments and reasons, preserve unresolved issues, verify all mechanical conditions, then lock all records before any comparison with another annotation. Do not infer or optimize agreement with a hidden first pass. No consistency rate is computed during this phase.
