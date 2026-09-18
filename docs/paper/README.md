# Paper working files

- `stage-review-2026-09-11.md`: Milestone review, high-impact source corrections, and ordered validation gaps. Read this before using older outline claims in an application or manuscript.

- `manuscript.md`: Generated reading copy of all sections, dated 2026-09-11. Edit the section files as the source of truth; regenerate the reading copy after edits. Working title: Evidence-Anchored Retrieval Evaluation for Technical Documents: A Pilot Study.
- `abstract.md`, `introduction.md`, `conclusion.md`: Opening and closing drafts aligned with the saved retrieval results and coverage audit. These complete the structural first draft, not a submission-ready paper.

- `discussion.md`: Discussion and Limitations draft, covering cutoff trade-offs, the distinction between interval coverage and semantic support, sampling/annotation limits, and outstanding validation.

- `results.md`: Results draft based on `frozen-30-hybrid-rrf-v1.summary.json`, with both annotation cohorts, marginal strata, counter-evidence results, and post-hoc coverage sensitivity.
- `coverage-audit.md`: Detailed saved-interval audit and reproduction command; the original run and gold annotations are unchanged.

- `methods.md`: All five Methods sections are drafted for review. The reannotation status in §3 is explicitly dated 2026-09-11 and must be updated from actual records before submission. Sections 4–5 describe `frozen-30-hybrid-rrf-v1`, including its configuration limits and any-positive-overlap hit rule. Complete Evidence Hit measures contact with all gold spans, not complete textual coverage.
- `methods-outline.md`: source-grounded Methods outline and evidence checklist.

- `related-work.md`: edited version of the user's five-paragraph draft in `D:/111求职准备/note/note.md`, with local citation keys.
- `references.bib`: ten entries: six core papers plus BM25, RRF, MiniLM, and the Sentence Transformers model card. Method sources added 2026-09-11; verification limits are recorded in the stage review. DomainRAG uses arXiv v2; Self-RAG uses its ICLR 2024 publication year; TreatFact uses the ESWA article rather than its arXiv revision year.
- `related-work-outline.md`: original planning scaffold; its historical progress statements are not the current experiment status.

The draft uses Pandoc citation syntax (`[@key]`). This is independent of the eventual venue's citation style. A plain Markdown preview may display citation keys literally. For a Pandoc rendering, run from this directory:

```sh
pandoc related-work.md --citeproc --bibliography=references.bib -s -o related-work.html
```

No venue template or CSL style has been selected. The command above is a rendering recipe, not a claim that a publication template has been compiled or checked.

Editorial scope: preserve the user's thematic organization, shorten repetition, separate pooling bias from lexical query-construction bias, and avoid presenting generation-side evaluation as completed. Citation metadata verification does not replace checking detailed numerical claims against the paper tables before submission.
