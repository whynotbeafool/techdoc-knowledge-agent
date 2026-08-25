# Retrieval run validity

Run artifacts are immutable records of the corpus selection written in each
`*.config.json`. Check this table before comparing methods.

| Run | Status | Reason |
|---|---|---|
| `pilot-5-v0` | historical / invalid for method claims | Its corpus config selected `pep8@v1`, which was later found to be an HTTP 404 page. |
| `pilot-9-v1` | historical / invalid for method claims | Its corpus config selected `pep8@v1`, so the distractor corpus was not the intended five-document collection. |
| `pilot-12-v2` | current pilot | Uses `pep8@v2`, records the active-revision hash, and emits summary schema 2 with separate reasoning and lexical-overlap cells. |

The older runs remain committed for auditability. Do not compare their numbers
directly with runs using the corrected corpus.
