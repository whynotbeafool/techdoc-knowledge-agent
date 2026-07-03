"""CLI to parse and chunk documents under data/raw_docs.

Usage:
    python scripts/parse_docs.py
    python scripts/parse_docs.py --dir data/raw_docs --json-out chunks.json
"""

import argparse
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.rag.chunker import chunk_pages  # noqa: E402
from app.rag.loader import SUPPORTED_SUFFIXES, load_document  # noqa: E402


def parse_directory(directory: Path):
    all_chunks = []
    for path in sorted(directory.iterdir()):
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        pages = load_document(path)
        chunks = chunk_pages(pages)
        all_chunks.extend(chunks)
        print(f"{path.name}: {len(pages)} page(s) -> {len(chunks)} chunk(s)")
    return all_chunks


def main():
    parser = argparse.ArgumentParser(description="Parse and chunk documents in data/raw_docs")
    parser.add_argument("--dir", default=str(PROJECT_ROOT / "data" / "raw_docs"))
    parser.add_argument("--json-out", default=None, help="Optional path to write chunks as JSON")
    args = parser.parse_args()

    directory = Path(args.dir)
    chunks = parse_directory(directory)

    print(f"\nTotal chunks: {len(chunks)}\n")
    for c in chunks[:10]:
        preview = c.text[:80].replace("\n", " ")
        print(f"[{c.chunk_id}] source={c.source} page={c.page} chars={len(c.text)} | {preview}...")

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump([c.__dict__ for c in chunks], f, ensure_ascii=False, indent=2)
        print(f"\nWrote {len(chunks)} chunks to {args.json_out}")


if __name__ == "__main__":
    main()
