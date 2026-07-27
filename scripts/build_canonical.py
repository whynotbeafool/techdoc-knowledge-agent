"""Freeze one source document into the versioned canonical corpus.

Usage:
    python scripts/build_canonical.py data/raw_docs/pep8.txt \
        --document-id pep8 --document-version v1
"""

import argparse
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.corpus.canonical import (  # noqa: E402
    DEFAULT_PAGE_SEPARATOR,
    build_canonical_document,
)


def main():
    parser = argparse.ArgumentParser(
        description="Create an immutable canonical-text document revision"
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("--document-id", required=True)
    parser.add_argument("--document-version", required=True)
    parser.add_argument(
        "--corpus-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "corpus",
    )
    parser.add_argument(
        "--page-separator",
        default=DEFAULT_PAGE_SEPARATOR,
        help=r"Literal page separator; defaults to '\n\n'",
    )
    args = parser.parse_args()

    record = build_canonical_document(
        args.source,
        document_id=args.document_id,
        document_version=args.document_version,
        corpus_dir=args.corpus_dir,
        page_separator=args.page_separator,
    )
    print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
