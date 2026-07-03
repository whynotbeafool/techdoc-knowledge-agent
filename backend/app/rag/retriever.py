import chromadb

from .chunker import Chunk
from .embeddings import get_embedding_function

COLLECTION_NAME = "techdoc_chunks"


class ChromaRetriever:
    def __init__(self, persist_dir: str):
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            COLLECTION_NAME, embedding_function=get_embedding_function()
        )

    def index_chunks(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        self.collection.upsert(
            ids=[c.chunk_id for c in chunks],
            documents=[c.text for c in chunks],
            metadatas=[{"source": c.source, "page": c.page or 0} for c in chunks],
        )

    def query(self, question: str, top_k: int = 5) -> dict:
        return self.collection.query(query_texts=[question], n_results=top_k)
