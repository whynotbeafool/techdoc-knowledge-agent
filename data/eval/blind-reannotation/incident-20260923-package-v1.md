# Incident: annotation stopped after baseline exposure

Status: STOPPED / NOT A BLIND ANNOTATION / NOT FOR FORMAL REANNOTATION.
Recorded at: 2026-09-23T02:31:50.993912+10:00
Executor: codex_main_assistant, the main AI assistant in this task. No subagents or human annotators participated. First-round executor identity continuity was not established.

## Exposure
The required reading of guideline.md exposed a historical baseline aggregate in section 6.1: BM25 Recall@5 had reached 1.000. This violates the requirement that all historical baseline results remain hidden, even though it appeared inside a mandatory input. Section 5.1 also disclosed a historical aggregate observation about high lexical overlap among the initial five questions. START.md supplied the first-round frozen hash and planned earliest start date. No question-level first-round labels, answers, evidence offsets, predictions, sampling strata, or baseline files were accessed. No other task histories, parent/sibling workspaces, original repository, or external sources were read.

The aggregate exposure was noticed and disclosed to the user during this task. Before the stop instruction arrived, the assistant continued and serialized its judgments with an exposure disclosure. This continuation does not restore blinding. The user then explicitly instructed immediate termination and replacement by a new task without historical information. The assistant stopped substantive annotation work on receipt of that instruction.

## Actual progress at termination
- First read only AGENTS.md and START.md in the authorized input directory, then read the requested questions, guideline, lexical rule, manifest, and frozen corpus.
- Verified all 12 manifest-listed file SHA-256 values and all 5 canonical document text_hash values.
- Inspected relevant frozen-corpus passages and searched all five documents for the three proposed out-of-scope questions; performed semantic candidate checks.
- Authored and wrote annotations.jsonl with 14 records, dimensions.jsonl with 14 records, and hesitations.md into output/ before the stop instruction arrived.
- Performed only limited in-memory checks before writing: 14-record counts, question-ID set coverage, and evidence/candidate text slice equality. Some selected span page assignments were checked during span extraction.
- Did NOT complete the planned independent re-read validation of the saved files, full schema/field-combination checks, independent lexical-overlap recomputation, or final output-hash verification.
- Did NOT create LOCK.json. The three outputs remain unlocked and are not approved for formal reannotation use.
- Did NOT read first-round annotations or compute any agreement statistics.

## Disposition
The existing unlocked outputs are retained without further edits or deletion solely as interrupted-task artifacts. They must not be represented as blind results or used as the formal second annotation. Per the user's instruction, after writing this incident report no further annotation, validation, locking, or comparison work is performed. Inputs were not modified. This incident report is the only file written after the stop instruction.
