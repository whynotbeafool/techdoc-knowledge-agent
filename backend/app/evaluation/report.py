"""Render a committed run's summary as a human-readable Markdown report.

Pure derivation: everything here comes from the run's own ``*.summary.json``
and ``*.config.json``, so a report can always be regenerated from committed
artifacts and never becomes an independent source of numbers.
"""

METRIC_COLUMNS = (
    ("evidence_recall_at_1", "R@1"),
    ("evidence_recall_at_3", "R@3"),
    ("evidence_recall_at_5", "R@5"),
    ("reciprocal_rank_at_5", "MRR@5"),
    ("complete_evidence_hit_at_5", "CompleteHit@5"),
)
AXIS_ORDER = (
    ("overall", ("overall",)),
    ("reasoning_type", ("single_evidence", "multi_evidence", "multi_hop")),
    ("lexical_overlap", ("low", "medium", "high")),
)


def find_cell(cells: list[dict], **dimensions) -> dict | None:
    return next(
        (
            cell
            for cell in cells
            if all(cell[key] == value for key, value in dimensions.items())
        ),
        None,
    )


def _format(value) -> str:
    if value is None:
        return "--"
    return f"{float(value):.4f}"


def _metric_table(cells: list[dict], question_class: str, methods: list[str]) -> list[str]:
    header = ["axis", "stratum", "cohort", "n"]
    for method in methods:
        header.extend(f"{method} {label}" for _, label in METRIC_COLUMNS)
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]

    for axis, strata in AXIS_ORDER:
        for stratum in strata:
            for cohort in ("all_annotations", "confirmed_only"):
                row_cells = {
                    method: find_cell(
                        cells,
                        method=method,
                        question_class=question_class,
                        cohort=cohort,
                        stratum_kind=axis,
                        stratum=stratum,
                    )
                    for method in methods
                }
                reference = row_cells[methods[0]]
                if reference is None or reference["n"] == 0:
                    continue
                row = [axis, stratum, cohort, str(reference["n"])]
                for method in methods:
                    metrics = (row_cells[method] or {}).get("metrics") or {}
                    row.extend(_format(metrics.get(name)) for name, _ in METRIC_COLUMNS)
                lines.append("| " + " | ".join(row) + " |")
    return lines


def _corpus_line(config: dict) -> str:
    return ", ".join(
        f"{document['document_id']}@{document['revision']}"
        for document in config["corpus"]
    )

def build_markdown_report(summary: dict, config: dict) -> str:
    """Return the full Markdown report for one run."""
    cells = summary["cells"]
    methods = sorted({cell["method"] for cell in cells})

    lines = [
        f"# Retrieval results: `{summary['run_id']}`",
        "",
        "Generated from committed run artifacts by `scripts/report_results.py`. "
        "Do not edit by hand: regenerate instead, so the numbers here can never "
        "drift from the run they claim to describe.",
        "",
        "## Provenance",
        "",
        "| field | value |",
        "|---|---|",
        f"| run_id | `{config['run_id']}` |",
        f"| created_at | {config['created_at']} |",
        f"| questions | {config['question_count']} |",
        f"| qa.jsonl | `{config['qa_hash']}` |",
        f"| active revisions | `{config['active_revisions_hash']}` |",
        f"| corpus | {_corpus_line(config)} |",
        f"| chunk_size / chunks | {config['chunk_size']} / {config['chunk_count']} |",
        f"| top_ks | {config['top_ks']} |",
        f"| python | {config['python_version']} |",
    ]
    for method in methods:
        settings = config["methods"].get(method, {})
        rendered = ", ".join(f"{k}={v}" for k, v in sorted(settings.items()))
        lines.append(f"| {method} | {rendered} |")

    lines += [
        "",
        "## Answerable questions",
        "",
        *_metric_table(cells, "answerable", methods),
        "",
        "## False-premise questions (counter-evidence retrieval)",
        "",
        "Reported separately: these questions restate the premise they refute, so "
        "they are lexically close to their counter-evidence by construction and "
        "must not be pooled with ordinary answerable questions.",
        "",
        *_metric_table(cells, "counter_evidence", methods),
        "",
        "## How to read this",
        "",
        "- Only `reasoning_type` cells partition the cohort. `lexical_overlap` cells "
        "omit questions with no recorded overlap, so their counts need not sum to "
        "`overall`.",
        "- `all_annotations` includes `needs_review` records; `confirmed_only` does not. "
        "A ranking that flips between the two cohorts is unstable and must be reported "
        "as such.",
        "- Evidence Recall@1 is capped by how many gold evidence items a question has, "
        "so it is not comparable across question types with different evidence counts.",
    ]
    return "\n".join(lines) + "\n"


def lexical_series(summary: dict, *, question_class: str, cohort: str, metric: str):
    """Return {method: [(stratum, value), ...]} along the lexical-overlap axis."""
    cells = summary["cells"]
    series = {}
    for method in sorted({cell["method"] for cell in cells}):
        points = []
        for stratum in ("low", "medium", "high"):
            cell = find_cell(
                cells,
                method=method,
                question_class=question_class,
                cohort=cohort,
                stratum_kind="lexical_overlap",
                stratum=stratum,
            )
            if cell and cell["n"] and (cell.get("metrics") or {}).get(metric) is not None:
                points.append((stratum, cell["n"], float(cell["metrics"][metric])))
        series[method] = points
    return series
