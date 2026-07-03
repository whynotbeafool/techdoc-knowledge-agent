"""Embedding function provider.

Phase 1 uses Chroma's built-in lightweight embedding (onnxruntime MiniLM,
no API key, no heavy download). Swap this for bge-m3 or an API-based
embedding (OpenAI/Qwen) later by changing only this module.
"""

from chromadb.utils import embedding_functions


def get_embedding_function():
    return embedding_functions.DefaultEmbeddingFunction()
