# Retrieval run validity

Run artifacts are immutable records of the corpus selection written in each
`*.config.json`. Check this table before comparing methods.

| Run | Status | Reason |
|---|---|---|
| `pilot-5-v0` | historical / invalid for method claims | Its corpus config selected `pep8@v1`, which was later found to be an HTTP 404 page. |
| `pilot-9-v1` | historical / invalid for method claims | Its corpus config selected `pep8@v1`, so the distractor corpus was not the intended five-document collection. |
| `pilot-12-v2` | historical / superseded | A 12-question snapshot taken before the dataset was frozen; superseded by `frozen-30-v1` on the same corpus. |
| `frozen-30-v1` | current | First run over the frozen 30-question dataset (`qa.jsonl` SHA-256 `21eb2747...`, recorded in the run config). Reproduced byte-identically across two independent executions. |

The older runs remain committed for auditability. Do not compare their numbers
directly with runs using the corrected corpus.
