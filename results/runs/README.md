# Retrieval run validity

Run artifacts are immutable records of the corpus selection written in each
`*.config.json`. Check this table before comparing methods.

| Run | Status | Reason |
|---|---|---|
| `pilot-5-v0` | historical / invalid for method claims | Its corpus config selected `pep8@v1`, which was later found to be an HTTP 404 page. |
| `pilot-9-v1` | historical / invalid for method claims | Its corpus config selected `pep8@v1`, so the distractor corpus was not the intended five-document collection. |
| `pilot-12-v2` | historical / superseded | A 12-question snapshot taken before the dataset was frozen; superseded by `frozen-30-v1` on the same corpus. |
| `frozen-30-v1` | current | First run over the frozen 30-question dataset (`qa.jsonl` SHA-256 `21eb2747...`, recorded in the run config). Reproduced byte-identically across two independent executions. |
| `frozen-30-hybrid-rrf-v1` | current controlled extension | Uses the same QA hash, active revisions, 800-character chunks, BM25 settings, and Dense model as `frozen-30-v1`; its BM25/Dense rows match the earlier run, and it adds equal-weight RRF with component depth 20 and rank constant 60. |

The older runs remain committed for auditability. Do not compare their numbers
directly with runs using the corrected corpus.

The Hybrid run is a fixed-parameter diagnostic, not a tuned leaderboard result. On the
confirmed answerable cohort, Hybrid ties BM25 on Evidence Recall@5 (0.6471), improves
Complete Evidence Hit@5 from 0.4706 to 0.5294, but reduces Recall@3 from 0.6471 to
0.5000 and MRR@5 from 0.6667 to 0.6147. These mixed results do not support claiming
that Hybrid is generally better.
