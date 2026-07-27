"""Corpus construction and canonical-text utilities."""

from .canonical import (
    CANONICAL_ENCODING,
    DEFAULT_PAGE_SEPARATOR,
    EXTRACTION_PIPELINE_VERSION,
    UNICODE_NORMALIZATION,
    LoadedCanonicalDocument,
    build_canonical_document,
    load_canonical_document,
)

__all__ = [
    "CANONICAL_ENCODING",
    "DEFAULT_PAGE_SEPARATOR",
    "EXTRACTION_PIPELINE_VERSION",
    "LoadedCanonicalDocument",
    "UNICODE_NORMALIZATION",
    "build_canonical_document",
    "load_canonical_document",
]
