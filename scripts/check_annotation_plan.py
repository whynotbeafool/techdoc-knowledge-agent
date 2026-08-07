"""Check QA progress and conformance against the temporary annotation plan."""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.evaluation.plan import check_annotation_plan_files  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--qa",
        type=Path,
        default=PROJECT_ROOT / "data" / "eval" / "qa.jsonl",
    )
    parser.add_argument(
        "--plan",
        type=Path,
        default=PROJECT_ROOT / "data" / "eval" / "annotation-plan.json",
    )
    args = parser.parse_args()

    try:
        report = check_annotation_plan_files(args.qa, args.plan)
    except (OSError, ValueError) as exc:
        print(f"ERROR plan: {exc}")
        return 1

    progress = report.progress
    print(f"Progress: {progress.completed}/{progress.target} planned slot(s)")
    print("By category:")
    for item in progress.categories:
        print(f"  {item.label}: {item.completed}/{item.target}")
    print("By stratum:")
    for item in progress.strata:
        print(f"  {item.label}: {item.completed}/{item.target}")
    print(f"Next pending: {progress.next_pending or 'none'}")

    for issue in report.issues:
        print(f"{issue.severity.upper()} {issue.question_id}: {issue.message}")
    errors = sum(issue.severity == "error" for issue in report.issues)
    warnings = sum(issue.severity == "warning" for issue in report.issues)
    print(
        f"Validated {args.qa} against {args.plan}: "
        f"{errors} error(s), {warnings} warning(s)"
    )
    return int(errors > 0)


if __name__ == "__main__":
    raise SystemExit(main())
