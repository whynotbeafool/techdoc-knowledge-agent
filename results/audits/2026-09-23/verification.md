# Local verification — 2026-09-23

Base commit: 48dc9cf1bd4942ab34ba5dcd783aa540227c1800, with the pre-existing documentation changes described in research/STATUS.md.

- `python scripts/validate_eval.py`: 0 errors, 0 warnings.
- `python scripts/check_annotation_plan.py`: 25/25, 0 errors, 0 warnings.
- Initial `python -m pytest tests/ -q`: 114 passed, 42 setup errors from temporary-directory permissions; 2 cache permission warnings.
- `python -m pytest tests/ -q -p no:cacheprovider --basetemp tmp/pytest-audit-20260923-0927 --tb=short`: 156 passed in 9.84s. This temporary fixture directory was removed after completion; no test sources were changed.
- `python -m ruff check .`: All checks passed.
- `python scripts/evaluate_retrieval.py --run-id audit-2026-09-23 --results-dir results/audits/2026-09-23`: success, 90 records and 379 chunks. Comparison after removing run_id matched every historical row exactly; see reproduction-comparison.json.
- Historical retrieval summary reproduced exactly via build_run_summary. Historical generation row metrics and main summary cells reproduced exactly. Current generation schema adds retrieval_conditioned_cells; the historical schema 1 file is preserved.

No paid generation call was made. Stored generation responses were rescored; model outputs were not regenerated. No old run or frozen QA was overwritten.


## Post-lock reannotation intake

- 14 locked records appended after verifying original questions, all input and artifact hashes, corpus coordinates and field combinations; historical two records retained. Frozen QA digest unchanged.
- `python scripts/validate_eval.py --qa data/eval/reannotation.jsonl`: 0 errors, 1 warning (q013 full semantic unit is 305 characters).
- `python scripts/check_locked_reannotation.py --packet data/eval/reannotation-20260923/input --output-dir data/eval/reannotation-20260923`: reproducible mechanical comparisons; see reannotation-mechanical-comparison.json.
- Negative check: an unlocked package is rejected, and a copied annotations file with one appended newline is rejected for lock hash mismatch. No locked artifacts modified.
- Manual semantic comparison is separate from the machine checks and is performed by an AI reviewer exposed to both passes; see research/REANNOTATION_REPORT.md. No human-review claim.
