"""Validate the frozen QA annotations against the canonical corpus."""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.evaluation.dataset import validate_qa_dataset  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--qa",
        type=Path,
        default=PROJECT_ROOT / "data" / "eval" / "qa.jsonl",
    )
    parser.add_argument(
        "--corpus-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "corpus",
    )
    args = parser.parse_args()

    try:
        issues = validate_qa_dataset(args.qa, args.corpus_dir)
    except (OSError, ValueError) as exc:
        print(f"ERROR dataset: {exc}")
        return 1

    for issue in issues:
        print(f"{issue.severity.upper()} {issue.question_id}: {issue.message}")
    errors = sum(issue.severity == "error" for issue in issues)
    warnings = sum(issue.severity == "warning" for issue in issues)
    print(f"Validated {args.qa}: {errors} error(s), {warnings} warning(s)")
    return int(errors > 0)


if __name__ == "__main__":
    raise SystemExit(main())
