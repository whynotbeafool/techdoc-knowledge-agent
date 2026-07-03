from dataclasses import dataclass
from typing import Optional

from .loader import RawPage

DEFAULT_MAX_CHARS = 800


@dataclass
class Chunk:
    chunk_id: str
    source: str
    page: Optional[int]
    text: str


def split_paragraphs(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n")
    paragraphs = [p.strip() for p in normalized.split("\n\n") if p.strip()]
    # PDF text extraction often has no blank lines at all; fall back to single newlines.
    if len(paragraphs) <= 1:
        paragraphs = [p.strip() for p in normalized.split("\n") if p.strip()]
    return paragraphs


def _split_long(text: str, max_chars: int) -> list[str]:
    """Hard-split text with no natural break points into max_chars slices."""
    return [text[i : i + max_chars] for i in range(0, len(text), max_chars)]


def chunk_pages(pages: list[RawPage], max_chars: int = DEFAULT_MAX_CHARS) -> list[Chunk]:
    """Group paragraphs into chunks up to max_chars, without splitting a paragraph across chunks."""
    chunks: list[Chunk] = []
    counter = 0
    for raw_page in pages:
        buffer = ""
        for para in split_paragraphs(raw_page.text):
            if len(para) > max_chars:
                if buffer:
                    chunks.append(_make_chunk(raw_page, buffer, counter))
                    counter += 1
                    buffer = ""
                for piece in _split_long(para, max_chars):
                    chunks.append(_make_chunk(raw_page, piece, counter))
                    counter += 1
                continue
            if buffer and len(buffer) + len(para) + 2 > max_chars:
                chunks.append(_make_chunk(raw_page, buffer, counter))
                counter += 1
                buffer = para
            else:
                buffer = f"{buffer}\n\n{para}" if buffer else para
        if buffer:
            chunks.append(_make_chunk(raw_page, buffer, counter))
            counter += 1
    return chunks


def _make_chunk(raw_page: RawPage, text: str, index: int) -> Chunk:
    page_part = f"p{raw_page.page}" if raw_page.page is not None else "p0"
    chunk_id = f"{raw_page.source}_{page_part}_{index}"
    return Chunk(chunk_id=chunk_id, source=raw_page.source, page=raw_page.page, text=text)
