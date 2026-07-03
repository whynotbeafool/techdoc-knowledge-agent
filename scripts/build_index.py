"""Parse, chunk, and index all documents in data/raw_docs into Chroma.

Usage:
    python scripts/build_index.py
"""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.rag.chunker import chunk_pages  # noqa: E402
from app.rag.loader import SUPPORTED_SUFFIXES, load_document  # noqa: E402
from app.rag.retriever import ChromaRetriever  # noqa: E402

RAW_DOCS_DIR = PROJECT_ROOT / "data" / "raw_docs"
VECTOR_STORE_DIR = PROJECT_ROOT / "data" / "vector_store"


def main():
    all_chunks = []
    for path in sorted(RAW_DOCS_DIR.iterdir()):
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        pages = load_document(path)
        chunks = chunk_pages(pages)
        all_chunks.extend(chunks)
        print(f"{path.name}: {len(chunks)} chunk(s)")

    retriever = ChromaRetriever(str(VECTOR_STORE_DIR))
    retriever.index_chunks(all_chunks)
    print(f"\nIndexed {len(all_chunks)} chunks into {VECTOR_STORE_DIR}")


if __name__ == "__main__":
    main()
