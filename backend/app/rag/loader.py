from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from pypdf import PdfReader

SUPPORTED_SUFFIXES = {".pdf", ".md", ".txt"}


@dataclass
class RawPage:
    source: str
    page: Optional[int]
    text: str


def load_document(path: Path) -> list[RawPage]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _load_pdf(path)
    if suffix in (".md", ".txt"):
        return _load_text(path)
    raise ValueError(f"Unsupported file type: {suffix}")


def _load_pdf(path: Path) -> list[RawPage]:
    reader = PdfReader(str(path))
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append(RawPage(source=path.name, page=i, text=text))
    return pages


def _load_text(path: Path) -> list[RawPage]:
    text = path.read_text(encoding="utf-8")
    return [RawPage(source=path.name, page=None, text=text)]
