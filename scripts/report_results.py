"""Render a committed run into a Markdown results table and the key figure.

Regenerates deterministically from `results/runs/<run-id>.{summary,config}.json`,
so the report can never drift from the run it describes.

    python scripts/report_results.py --run-id frozen-30-v1
"""

import argparse
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.evaluation.report import build_markdown_report, lexical_series  # noqa: E402

DEFAULT_RUNS_DIR = PROJECT_ROOT / "results" / "runs"
DEFAULT_DOCS_DIR = PROJECT_ROOT / "docs"
FIGURE_METRIC = "evidence_recall_at_5"
STRATUM_LABELS = {"low": "low\n(<0.25)", "medium": "medium\n(0.25-0.50)", "high": "high\n(>=0.50)"}


def _render_figure(summary: dict, output_path: Path, *, cohort: str) -> bool:
    import matplotlib

    matplotlib.use("Agg")
    matplotlib.rcParams["font.sans-serif"] = ["DejaVu Sans"]
    import matplotlib.pyplot as plt

    series = lexical_series(
        summary,
        question_class="answerable",
        cohort=cohort,
        metric=FIGURE_METRIC,
    )
    if not any(points for points in series.values()):
        return False

    figure, axes = plt.subplots(figsize=(7, 4.4))
    for method, points in sorted(series.items()):
        if not points:
            continue
        axes.plot(
            [STRATUM_LABELS[stratum] for stratum, _, _ in points],
            [value for _, _, value in points],
            marker="o",
            label=method,
        )
        for stratum, n, value in points:
            axes.annotate(
                f"{value:.2f}",
                (STRATUM_LABELS[stratum], value),
                textcoords="offset points",
                xytext=(0, 7),
                ha="center",
                fontsize=9,
            )

    counts = next(points for points in series.values() if points)
    axes.set_xlabel(
        "question-evidence lexical overlap stratum\n"
        + "  ".join(f"n={n}" for _, n, _ in counts)
    )
    axes.set_ylabel("Evidence Recall@5 (macro)")
    axes.set_title(
        f"Retrieval by lexical overlap - {summary['run_id']} ({cohort})",
        fontsize=11,
    )
    axes.set_ylim(0, 1.05)
    axes.grid(axis="y", alpha=0.3)
    axes.legend()
    figure.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=150)
    plt.close(figure)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)
    parser.add_argument("--docs-dir", type=Path, default=DEFAULT_DOCS_DIR)
    parser.add_argument(
        "--cohort",
        default="all_annotations",
        choices=("all_annotations", "confirmed_only"),
        help="cohort plotted in the figure; both appear in the table",
    )
    args = parser.parse_args()

    summary_path = args.runs_dir / f"{args.run_id}.summary.json"
    config_path = args.runs_dir / f"{args.run_id}.config.json"
    for path in (summary_path, config_path):
        if not path.exists():
            print(f"ERROR missing artifact: {path}")
            return 1

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    config = json.loads(config_path.read_text(encoding="utf-8"))

    report_path = args.docs_dir / f"results-{args.run_id}.md"
    figure_path = args.docs_dir / f"results-{args.run_id}-lexical.png"

    markdown = build_markdown_report(summary, config)
    if _render_figure(summary, figure_path, cohort=args.cohort):
        markdown += (
            f"\n## Figure\n\n"
            f"![Recall@5 by lexical overlap]({figure_path.name})\n"
        )
        print(f"Wrote {figure_path}")
    else:
        print("No lexical cells with data; figure skipped.")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(markdown, encoding="utf-8", newline="\n")
    print(f"Wrote {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
