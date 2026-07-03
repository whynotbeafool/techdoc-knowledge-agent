"""Query the Chroma index and print the top-k retrieved chunks.

Usage:
    python scripts/query.py "What is end-to-end autonomous driving?"
    python scripts/query.py "How does FastAPI handle path parameters?" --top-k 5
"""

import argparse
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.rag.retriever import ChromaRetriever  # noqa: E402

VECTOR_STORE_DIR = PROJECT_ROOT / "data" / "vector_store"


def main():
    parser = argparse.ArgumentParser(description="Query the Chroma index for top-k chunks")
    parser.add_argument("question")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    retriever = ChromaRetriever(str(VECTOR_STORE_DIR))
    results = retriever.query(args.question, top_k=args.top_k)

    ids = results["ids"][0]
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    print(f"Question: {args.question}\n")
    for rank, (chunk_id, doc, meta, dist) in enumerate(zip(ids, documents, metadatas, distances), start=1):
        preview = doc[:150].replace("\n", " ")
        print(f"#{rank} [{chunk_id}] source={meta['source']} page={meta['page']} distance={dist:.4f}")
        print(f"    {preview}...\n")


if __name__ == "__main__":
    main()
