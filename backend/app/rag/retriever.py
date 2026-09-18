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

    def close(self) -> None:
        """Release persistent index files, required before cleanup on Windows."""
        self.client.close()

    def describe(self) -> dict:
        """Report the dense settings that actually govern this collection.

        Everything here is read back from the live collection and the embedder
        that really produces vectors, rather than typed in, so a run config
        records what ran, not what was assumed. Three facts are easy to get
        wrong from the model name alone: the collection distance space is
        Chroma's default (l2), not the cosine the ONNX model declares; that is
        harmless only because the vectors are unit-normalised, which is
        measured here rather than trusted; and inputs longer than ``max_tokens``
        are silently truncated. Flat keys only, so the report table can render
        them.
        """
        embedder = _resolve_embedder(self.collection._embedding_function)
        index = (self.collection.configuration_json or {}).get("hnsw") or {}
        probe = embedder(["probe"])[0]
        norm = sum(float(x) * float(x) for x in probe) ** 0.5
        return {
            "implementation": type(embedder).__name__,
            "model": getattr(embedder, "MODEL_NAME", None),
            "model_sha256": getattr(embedder, "_MODEL_SHA256", None),
            "max_tokens": embedder.max_tokens(),
            "embedding_dim": len(probe),
            "embeddings_unit_normalised": abs(norm - 1.0) < 1e-4,
            "model_declared_space": embedder.default_space(),
            "collection_space": index.get("space"),
            "hnsw_ef_construction": index.get("ef_construction"),
            "hnsw_ef_search": index.get("ef_search"),
            "hnsw_max_neighbors": index.get("max_neighbors"),
        }


def _resolve_embedder(function):
    """Unwrap Chroma's DefaultEmbeddingFunction to the class that embeds.

    The default is a shim that builds a fresh ONNXMiniLM_L6_V2 on every call
    and reports none of its attributes, so asking the shim gives null model
    identity and the base-class distance space instead of the real ones.
    """
    from chromadb.api.types import DefaultEmbeddingFunction

    if isinstance(function, DefaultEmbeddingFunction):
        from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import ONNXMiniLM_L6_V2

        return ONNXMiniLM_L6_V2()
    return function


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
