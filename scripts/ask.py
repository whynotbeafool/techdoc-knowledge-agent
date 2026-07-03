"""End-to-end RAG question answering: retrieve top-k chunks, call the LLM, print answer + citations.

Usage:
    python scripts/ask.py "What are the main challenges in end-to-end autonomous driving?"
"""

import argparse
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.rag.generator import generate_answer  # noqa: E402
from app.rag.retriever import ChromaRetriever  # noqa: E402

VECTOR_STORE_DIR = PROJECT_ROOT / "data" / "vector_store"


def main():
    parser = argparse.ArgumentParser(description="Ask a question against the indexed documents")
    parser.add_argument("question")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    retriever = ChromaRetriever(str(VECTOR_STORE_DIR))
    chunks = retriever.query_chunks(args.question, top_k=args.top_k)

    if not chunks:
        print("检索不到任何相关资料，请先运行 scripts/build_index.py 建立索引。")
        return

    answer = generate_answer(args.question, chunks)

    print(f"问题: {args.question}\n")
    print(f"回答:\n{answer}\n")
    print("引用来源:")
    for c in chunks:
        print(f"  - {c['source']} 第{c['page']}页 (chunk_id={c['chunk_id']})")


if __name__ == "__main__":
    main()
