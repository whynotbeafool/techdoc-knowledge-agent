import pytest
from app.rag.loader import load_document

# Note: PDF loading isn't unit tested here — it needs a real PDF binary fixture,
# which is disproportionate effort for this task. It's already verified against
# real documents in data/raw_docs/ via scripts/parse_docs.py and scripts/ask.py.


def test_load_txt_returns_single_page_with_no_page_number(tmp_path):
    """txt/md files have no page concept, so page should be None (later
    displayed as 'p0' by chunker.py's _make_chunk).
    """
    file_path = tmp_path / "notes.txt"
    file_path.write_text("hello world", encoding="utf-8")

    pages = load_document(file_path)

    assert len(pages) == 1
    assert pages[0].source == "notes.txt"
    assert pages[0].page is None
    assert pages[0].text == "hello world"


def test_load_md_uses_same_path_as_txt(tmp_path):
    """.md and .txt share the same loading logic (both just read as plain text)."""
    file_path = tmp_path / "readme.md"
    file_path.write_text("# Title\n\nSome content", encoding="utf-8")

    pages = load_document(file_path)

    assert len(pages) == 1
    assert pages[0].source == "readme.md"
    assert "# Title" in pages[0].text


def test_load_document_rejects_unsupported_extension(tmp_path):
    """Unsupported file types (e.g. .docx) should fail loudly with a clear
    error, not silently return nothing — this is what lets build_index.py's
    per-file try/except catch it and skip just that one file.
    """
    file_path = tmp_path / "document.docx"
    file_path.write_text("irrelevant", encoding="utf-8")

    with pytest.raises(ValueError, match=".docx"):
        load_document(file_path)
