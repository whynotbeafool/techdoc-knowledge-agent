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
            metadatas=[_chunk_metadata(c) for c in chunks],
        )

    def query(self, question: str, top_k: int = 5) -> dict:
        return self.collection.query(query_texts=[question], n_results=top_k)

    def query_chunks(self, question: str, top_k: int = 5) -> list[dict]:
        """Same as query(), but flattened into a list of {chunk_id, source, page, text, distance}."""
        results = self.query(question, top_k=top_k)
        ids = results["ids"][0]
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]
        return [
            {
                "chunk_id": chunk_id,
                "source": meta["source"],
                "page": meta["page"],
                "text": doc,
                "distance": dist,
                "start_char": meta.get("start_char"),
                "end_char": meta.get("end_char"),
                "document_id": meta.get("document_id"),
                "revision": meta.get("revision"),
            }
            for chunk_id, doc, meta, dist in zip(ids, documents, metadatas, distances)
        ]


def _chunk_metadata(chunk: Chunk) -> dict:
    metadata = {"source": chunk.source, "page": chunk.page or 0}
    for field in (
        "start_char",
        "end_char",
        "document_id",
        "revision",
    ):
        value = getattr(chunk, field)
        if value is not None:
            metadata[field] = value
    return metadata
