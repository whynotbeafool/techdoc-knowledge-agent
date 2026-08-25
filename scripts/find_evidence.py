"""Drafting aid for annotation: locate candidate evidence and score a draft question.

This does not decide anything. It reports offsets and the frozen lexical-overlap
metric so the annotator can hit a planned stratum deliberately instead of
discovering a mismatch when the validator rejects the record.

Search canonical text for candidate spans:

    python scripts/find_evidence.py search "world model" --document-id rag_paper

Score a draft question against spans you have chosen (repeat --span per evidence,
format DOCUMENT_ID:START:END):

    python scripts/find_evidence.py score \\
        --question "Which components does the pipeline optimise jointly?" \\
        --span rag_paper:1280:1331 --span rag_paper:4000:4120
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.corpus import load_active_revision_records, load_canonical_document  # noqa: E402
from app.evaluation.dataset import (  # noqa: E402
    _content_tokens,
    lexical_overlap_score,
    lexical_overlap_stratum,
)

DEFAULT_CORPUS_DIR = PROJECT_ROOT / "data" / "corpus"
SENTENCE_END = re.compile(r"(?<=[.!?])\s")


def _manifest(corpus_dir: Path) -> list[dict]:
    return load_active_revision_records(corpus_dir)


def _page_for_offset(document, offset: int):
    return next(
        (
            span["page"]
            for span in document.metadata["page_spans"]
            if span["start_char"] <= offset < span["end_char"]
        ),
        None,
    )


def _sentence_span(text: str, start: int, end: int) -> tuple[int, int]:
    """Widen a match to the enclosing sentence, per guideline 4.3."""
    left = 0
    for match in SENTENCE_END.finditer(text, 0, start):
        left = match.end()
    right_match = SENTENCE_END.search(text, end)
    right = right_match.start() + 1 if right_match else len(text)
    while left < right and text[left].isspace():
        left += 1
    while right > left and text[right - 1].isspace():
        right -= 1
    return left, right


def cmd_search(args) -> int:
    records = _manifest(args.corpus_dir)
    if args.document_id:
        records = [r for r in records if r["document_id"] == args.document_id]
        if not records:
            print(f"ERROR unknown document_id: {args.document_id}")
            return 1

    pattern = re.compile(args.query if args.regex else re.escape(args.query), re.IGNORECASE)
    total = 0
    for record in records:
        document = load_canonical_document(
            args.corpus_dir,
            document_id=record["document_id"],
            revision=record["revision"],
        )
        for match in pattern.finditer(document.text):
            if total >= args.limit:
                print(f"\n(stopped at --limit {args.limit}; narrow the query for more)")
                return 0
            start, end = _sentence_span(document.text, match.start(), match.end())
            quote = document.text[start:end]
            total += 1
            print(f"--- {record['document_id']}@{record['revision']} "
                  f"page={_page_for_offset(document, start)} [{start}:{end}) len={end - start}")
            print(f"    --span {record['document_id']}:{start}:{end}")
            print(f"    {quote}")
            print()
    if total == 0:
        print("No match. For an out_of_scope question, record the terms you tried "
              "in unanswerable_search.searched_terms (guideline 4.7).")
    else:
        print(f"{total} candidate span(s).")
    return 0


def cmd_score(args) -> int:
    evidence = []
    for raw in args.span:
        try:
            document_id, start_text, end_text = raw.rsplit(":", 2)
            start, end = int(start_text), int(end_text)
        except ValueError:
            print(f"ERROR malformed --span (expected DOCUMENT_ID:START:END): {raw}")
            return 1

        record = next(
            (r for r in _manifest(args.corpus_dir) if r["document_id"] == document_id),
            None,
        )
        if record is None:
            print(f"ERROR unknown document_id: {document_id}")
            return 1
        document = load_canonical_document(
            args.corpus_dir,
            document_id=document_id,
            revision=record["revision"],
        )
        if not 0 <= start < end <= len(document.text):
            print(f"ERROR span out of bounds for {document_id}: [{start}, {end})")
            return 1

        quote = document.text[start:end]
        evidence.append(
            {
                "evidence_id": f"e{len(evidence) + 1:03d}",
                "document_id": document_id,
                "revision": record["revision"],
                "page": _page_for_offset(document, start),
                "start_char": start,
                "end_char": end,
                "quote": quote,
            }
        )

    score = lexical_overlap_score(args.question, evidence)
    stratum = lexical_overlap_stratum(score)

    question_tokens = _content_tokens(args.question)
    evidence_tokens = _content_tokens(" ".join(item["quote"] for item in evidence))
    shared = sorted(question_tokens & evidence_tokens)
    missing = sorted(question_tokens - evidence_tokens)

    print(f"score={score}  stratum={stratum}")
    if args.target and args.target != stratum:
        print(f"MISMATCH target stratum is {args.target}; the validator will reject this.")
        if args.target == "high":
            print("  To raise the score, reuse more of the passage's own wording.")
        elif args.target == "low":
            print("  To lower it, paraphrase away from the passage's wording "
                  "(keep domain entities; do not resort to contrived circumlocution).")
    print(f"shared  ({len(shared)}/{len(question_tokens)}): {shared}")
    print(f"missing ({len(missing)}/{len(question_tokens)}): {missing}")
    for item in evidence:
        print(f"  quote len={len(item['quote'])}"
              f"{'  WARNING exceeds 300-char guidance' if len(item['quote']) > 300 else ''}")
    print()
    print("evidence block for qa.jsonl:")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    print()
    print(json.dumps(
        {"metric": "question_content_token_recall_in_evidence",
         "score": score, "stratum": stratum},
        ensure_ascii=False,
    ))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--corpus-dir", type=Path, default=DEFAULT_CORPUS_DIR)
    subparsers = parser.add_subparsers(dest="command", required=True)

    search = subparsers.add_parser("search", help="find candidate evidence spans")
    search.add_argument("query")
    search.add_argument("--document-id")
    search.add_argument("--regex", action="store_true")
    search.add_argument("--limit", type=int, default=20)
    search.set_defaults(func=cmd_search)

    score = subparsers.add_parser("score", help="score a draft question against chosen spans")
    score.add_argument("--question", required=True)
    score.add_argument("--span", action="append", required=True,
                       help="DOCUMENT_ID:START:END, repeatable")
    score.add_argument("--target", choices=("low", "medium", "high"))
    score.set_defaults(func=cmd_score)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
