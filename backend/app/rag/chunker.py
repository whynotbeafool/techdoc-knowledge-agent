from dataclasses import asdict, dataclass
from typing import Optional

from app.corpus.canonical import (
    ExtractedPage,
    LoadedCanonicalDocument,
    assemble_canonical_text,
)

from .loader import RawPage

DEFAULT_MAX_CHARS = 800


@dataclass
class Chunk:
    chunk_id: str
    source: str
    page: Optional[int]
    text: str
    start_char: int
    end_char: int
    document_id: Optional[str] = None
    revision: Optional[str] = None


def split_paragraphs(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n")
    paragraphs = [p.strip() for p in normalized.split("\n\n") if p.strip()]
    # PDF text extraction often has no blank lines at all; fall back to single newlines.
    if len(paragraphs) <= 1:
        paragraphs = [p.strip() for p in normalized.split("\n") if p.strip()]
    return paragraphs


def chunk_pages(pages: list[RawPage], max_chars: int = DEFAULT_MAX_CHARS) -> list[Chunk]:
    """Compatibility entry point for uploaded documents outside the frozen corpus.

    Research evaluation must use :func:`chunk_canonical_document` with a
    hash-verified ``LoadedCanonicalDocument``. This wrapper assembles an
    ephemeral canonical coordinate system so the interactive MVP keeps working.
    """
    if not pages:
        return []
    source = pages[0].source
    if any(page.source != source for page in pages):
        raise ValueError("chunk_pages expects pages from exactly one source document")

    canonical = assemble_canonical_text(
        [ExtractedPage(page=page.page, text=page.text) for page in pages]
    )
    document = LoadedCanonicalDocument(
        text=canonical.text,
        metadata={
            "document_id": source,
            "revision": "runtime",
            "source_file": source,
            "page_spans": [asdict(span) for span in canonical.page_spans],
        },
    )
    return chunk_canonical_document(document, max_chars=max_chars)


def chunk_canonical_document(
    document: LoadedCanonicalDocument,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> list[Chunk]:
    """Chunk canonical text without crossing pages or changing its characters."""
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")

    metadata = document.metadata
    source = metadata["source_file"]
    document_id = metadata["document_id"]
    revision = metadata["revision"]
    chunks: list[Chunk] = []

    for page_span in metadata["page_spans"]:
        page = page_span["page"]
        for start_char, end_char in _chunk_page_spans(
            document.text,
            page_start=page_span["start_char"],
            page_end=page_span["end_char"],
            max_chars=max_chars,
        ):
            page_part = f"p{page}" if page is not None else "p0"
            chunks.append(
                Chunk(
                    chunk_id=f"{source}_{page_part}_{len(chunks)}",
                    source=source,
                    page=page,
                    text=document.text[start_char:end_char],
                    start_char=start_char,
                    end_char=end_char,
                    document_id=document_id,
                    revision=revision,
                )
            )

    return chunks


def _chunk_page_spans(
    text: str,
    *,
    page_start: int,
    page_end: int,
    max_chars: int,
) -> list[tuple[int, int]]:
    paragraphs = _paragraph_spans(text, page_start, page_end)
    chunks: list[tuple[int, int]] = []
    buffer_start = None
    buffer_end = None

    for paragraph_start, paragraph_end in paragraphs:
        if paragraph_end - paragraph_start > max_chars:
            if buffer_start is not None:
                chunks.append((buffer_start, buffer_end))
                buffer_start = None
                buffer_end = None
            for piece_start in range(paragraph_start, paragraph_end, max_chars):
                chunks.append((piece_start, min(piece_start + max_chars, paragraph_end)))
            continue

        if buffer_start is not None and paragraph_end - buffer_start > max_chars:
            chunks.append((buffer_start, buffer_end))
            buffer_start = paragraph_start
        elif buffer_start is None:
            buffer_start = paragraph_start
        buffer_end = paragraph_end

    if buffer_start is not None:
        chunks.append((buffer_start, buffer_end))
    return chunks


def _paragraph_spans(text: str, start: int, end: int) -> list[tuple[int, int]]:
    paragraphs = _non_blank_segment_spans(text, start, end, separator="\n\n")
    if len(paragraphs) <= 1:
        paragraphs = _non_blank_segment_spans(text, start, end, separator="\n")
    return paragraphs


def _non_blank_segment_spans(
    text: str,
    start: int,
    end: int,
    *,
    separator: str,
) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    cursor = start
    while cursor <= end:
        separator_at = text.find(separator, cursor, end)
        segment_end = end if separator_at == -1 else separator_at
        content_start, content_end = _trim_span(text, cursor, segment_end)
        if content_start < content_end:
            spans.append((content_start, content_end))
        if separator_at == -1:
            break
        cursor = separator_at + len(separator)
    return spans


def _trim_span(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end
