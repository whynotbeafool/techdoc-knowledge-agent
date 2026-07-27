import hashlib
import json
import os
import re
import tempfile
import unicodedata
from dataclasses import asdict, dataclass
from importlib.metadata import version
from pathlib import Path
from typing import Optional

from pypdf import PdfReader

from app.rag.loader import SUPPORTED_SUFFIXES

CANONICAL_ENCODING = "utf-8"
DEFAULT_PAGE_SEPARATOR = "\n\n"
UNICODE_NORMALIZATION = "NFC"
EXTRACTION_PIPELINE_VERSION = "canonical-text-v1"

_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


@dataclass(frozen=True)
class ExtractedPage:
    page: Optional[int]
    text: str


@dataclass(frozen=True)
class PageSpan:
    page: Optional[int]
    start_char: int
    end_char: int


@dataclass(frozen=True)
class CanonicalText:
    text: str
    page_spans: list[PageSpan]
    skipped_pages: list[int]


@dataclass(frozen=True)
class LoadedCanonicalDocument:
    text: str
    metadata: dict


def build_canonical_document(
    source_path: Path,
    *,
    document_id: str,
    document_version: str,
    corpus_dir: Path,
    page_separator: str = DEFAULT_PAGE_SEPARATOR,
) -> dict:
    """Freeze one source document as canonical text and register its metadata.

    The canonical artifact is immutable for a given ``document_id`` and
    ``document_version``. Re-running with identical content is idempotent;
    attempting to reuse the revision for different content raises an error.
    """
    source_path = source_path.resolve()
    corpus_dir = corpus_dir.resolve()
    _validate_revision_component(document_id, name="document_id")
    _validate_revision_component(document_version, name="document_version")
    _validate_page_separator(page_separator)

    pages, tool, tool_version = extract_pages(source_path)
    canonical = assemble_canonical_text(pages, page_separator=page_separator)
    if not canonical.text:
        raise ValueError(f"Document has no non-blank canonical text: {source_path}")

    source_hash = _sha256_bytes(source_path.read_bytes())
    canonical_bytes = canonical.text.encode(CANONICAL_ENCODING)
    text_hash = _sha256_bytes(canonical_bytes)

    relative_text_path = Path("canonical") / document_id / f"{document_version}.txt"
    canonical_path = corpus_dir / relative_text_path
    manifest_path = corpus_dir / "documents.jsonl"

    record = {
        "schema_version": "0.1",
        "document_id": document_id,
        "document_version": document_version,
        "source_file": source_path.name,
        "source_hash": f"sha256:{source_hash}",
        "canonical_text_file": relative_text_path.as_posix(),
        "text_hash": f"sha256:{text_hash}",
        "page_spans": [asdict(span) for span in canonical.page_spans],
        "skipped_pages": canonical.skipped_pages,
        "extraction": {
            "pipeline_version": EXTRACTION_PIPELINE_VERSION,
            "tool": tool,
            "tool_version": tool_version,
            "encoding": CANONICAL_ENCODING,
            "unicode_normalization": UNICODE_NORMALIZATION,
            "newline_normalization": (
                "universal_to_lf"
                if source_path.suffix.lower() in {".md", ".txt"}
                else "extractor_output_unchanged"
            ),
            "page_separator": page_separator,
            "blank_pages": "omit_without_separator",
            "offset_convention": "zero_based_half_open",
            "offset_unit": "unicode_codepoint",
        },
    }

    existing_record = _find_revision(manifest_path, document_id, document_version)
    if existing_record is not None and existing_record != record:
        raise ValueError(
            f"Revision {document_id}@{document_version} already exists with different metadata; "
            "use a new document_version"
        )
    if canonical_path.exists() and canonical_path.read_bytes() != canonical_bytes:
        raise ValueError(
            f"Canonical artifact already exists with different content: {canonical_path}; "
            "use a new document_version"
        )

    canonical_path.parent.mkdir(parents=True, exist_ok=True)
    if not canonical_path.exists():
        canonical_path.write_bytes(canonical_bytes)

    if existing_record is None:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        _append_jsonl_atomically(manifest_path, record)

    return record


def load_canonical_document(
    corpus_dir: Path,
    *,
    document_id: str,
    document_version: str,
) -> LoadedCanonicalDocument:
    """Load a frozen revision only after verifying its canonical-text hash."""
    corpus_dir = corpus_dir.resolve()
    _validate_revision_component(document_id, name="document_id")
    _validate_revision_component(document_version, name="document_version")

    manifest_path = corpus_dir / "documents.jsonl"
    record = _find_revision(manifest_path, document_id, document_version)
    if record is None:
        raise KeyError(f"Canonical revision not found: {document_id}@{document_version}")

    relative_text_path = Path(record["canonical_text_file"])
    canonical_path = (corpus_dir / relative_text_path).resolve()
    if relative_text_path.is_absolute() or not canonical_path.is_relative_to(corpus_dir):
        raise ValueError(
            f"Canonical text path escapes corpus directory: {relative_text_path}"
        )

    canonical_bytes = canonical_path.read_bytes()
    actual_hash = f"sha256:{_sha256_bytes(canonical_bytes)}"
    expected_hash = record.get("text_hash")
    if actual_hash != expected_hash:
        raise ValueError(
            f"Canonical text hash mismatch for {document_id}@{document_version}: "
            f"expected {expected_hash}, got {actual_hash}"
        )

    text = canonical_bytes.decode(CANONICAL_ENCODING)
    extraction = record.get("extraction", {})
    if extraction.get("offset_convention") != "zero_based_half_open":
        raise ValueError("Canonical metadata has unsupported offset convention")
    if extraction.get("offset_unit") != "unicode_codepoint":
        raise ValueError("Canonical metadata has unsupported offset unit")
    _validate_loaded_page_spans(text, record)
    return LoadedCanonicalDocument(text=text, metadata=record)


def extract_pages(source_path: Path) -> tuple[list[ExtractedPage], str, str]:
    """Extract every physical page, retaining blank PDF pages for bookkeeping."""
    suffix = source_path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError(f"Unsupported file type: {suffix}")

    if suffix == ".pdf":
        reader = PdfReader(str(source_path))
        pages = [
            ExtractedPage(page=index, text=page.extract_text() or "")
            for index, page in enumerate(reader.pages, start=1)
        ]
        return pages, "pypdf", version("pypdf")

    text = source_path.read_text(encoding=CANONICAL_ENCODING)
    return [ExtractedPage(page=None, text=text)], "python-text-reader", "1"


def assemble_canonical_text(
    pages: list[ExtractedPage],
    *,
    page_separator: str = DEFAULT_PAGE_SEPARATOR,
) -> CanonicalText:
    """Normalize and join pages while preserving exact page-to-text spans."""
    _validate_page_separator(page_separator)

    kept_pages: list[ExtractedPage] = []
    skipped_pages: list[int] = []
    for page in pages:
        normalized = unicodedata.normalize(UNICODE_NORMALIZATION, page.text)
        if not normalized.strip():
            if page.page is not None:
                skipped_pages.append(page.page)
            continue
        kept_pages.append(ExtractedPage(page=page.page, text=normalized))

    parts: list[str] = []
    page_spans: list[PageSpan] = []
    cursor = 0
    for index, page in enumerate(kept_pages):
        if index:
            parts.append(page_separator)
            cursor += len(page_separator)
        start_char = cursor
        parts.append(page.text)
        cursor += len(page.text)
        page_spans.append(
            PageSpan(page=page.page, start_char=start_char, end_char=cursor)
        )

    return CanonicalText(
        text="".join(parts),
        page_spans=page_spans,
        skipped_pages=skipped_pages,
    )


def _find_revision(
    manifest_path: Path, document_id: str, document_version: str
) -> Optional[dict]:
    if not manifest_path.exists():
        return None

    found = None
    with manifest_path.open(encoding=CANONICAL_ENCODING) as manifest:
        for line_number, line in enumerate(manifest, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON in {manifest_path} at line {line_number}"
                ) from exc
            if (
                record.get("document_id") == document_id
                and record.get("document_version") == document_version
            ):
                if found is not None:
                    raise ValueError(
                        f"Duplicate revision {document_id}@{document_version} in {manifest_path}"
                    )
                found = record
    return found


def _validate_revision_component(value: str, *, name: str) -> None:
    if not _SAFE_ID.fullmatch(value):
        raise ValueError(
            f"{name} must match {_SAFE_ID.pattern!r}; received {value!r}"
        )


def _validate_page_separator(page_separator: str) -> None:
    if not page_separator:
        raise ValueError("page_separator must not be empty")
    if unicodedata.normalize(UNICODE_NORMALIZATION, page_separator) != page_separator:
        raise ValueError(f"page_separator must already be {UNICODE_NORMALIZATION}-normalized")


def _validate_loaded_page_spans(text: str, record: dict) -> None:
    spans = record.get("page_spans")
    if not isinstance(spans, list) or not spans:
        raise ValueError("Canonical metadata must contain at least one page span")

    page_separator = record.get("extraction", {}).get("page_separator")
    if not isinstance(page_separator, str) or not page_separator:
        raise ValueError("Canonical metadata has no valid page separator")

    previous_end = None
    for index, span in enumerate(spans):
        try:
            start = span["start_char"]
            end = span["end_char"]
        except (KeyError, TypeError) as exc:
            raise ValueError(f"Invalid page span at index {index}") from exc
        if (
            not isinstance(start, int)
            or isinstance(start, bool)
            or not isinstance(end, int)
            or isinstance(end, bool)
            or start < 0
            or start >= end
            or end > len(text)
        ):
            raise ValueError(f"Invalid page span bounds at index {index}: {span}")
        if previous_end is None:
            if start != 0:
                raise ValueError("First page span must start at character 0")
        else:
            if start <= previous_end:
                raise ValueError("Page spans must be strictly increasing and non-overlapping")
            if text[previous_end:start] != page_separator:
                raise ValueError(
                    f"Page span gap at index {index} does not match page_separator"
                )
        previous_end = end

    if previous_end != len(text):
        raise ValueError(
            f"Last page span must end at text length {len(text)}, got {previous_end}"
        )


def _append_jsonl_atomically(path: Path, record: dict) -> None:
    existing = path.read_bytes() if path.exists() else b""
    if existing and not existing.endswith(b"\n"):
        existing += b"\n"
    new_line = (
        json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
    ).encode(CANONICAL_ENCODING)

    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(existing)
            temporary.write(new_line)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
