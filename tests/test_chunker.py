from app.rag.chunker import chunk_pages, split_paragraphs
from app.rag.loader import RawPage


def test_split_paragraphs_falls_back_to_single_newline():
    """PDF text often has no blank lines (\\n\\n) between paragraphs — this is the
    exact bug found on Day 3-4. split_paragraphs should fall back to splitting on
    single newlines when no \\n\\n is present, instead of returning one giant blob.
    """
    text = "line one\nline two\nline three"
    result = split_paragraphs(text)
    assert result == ["line one", "line two", "line three"]


def test_chunk_pages_hard_splits_oversized_paragraph():
    """A single paragraph longer than max_chars (e.g. a PDF page with no natural
    breaks) must be hard-split into multiple chunks, none longer than max_chars.
    """
    long_text = "x" * 2000  # one giant "paragraph", no newlines at all
    page = RawPage(source="test.pdf", page=1, text=long_text)

    chunks = chunk_pages([page], max_chars=800)

    assert len(chunks) == 3  # 2000 chars -> 800 + 800 + 400
    assert all(len(c.text) <= 800 for c in chunks)


def test_chunk_id_format():
    """当 page=None 时，chunk_id 应显示为 'p0' 且索引从 0 开始。"""
    page = RawPage(source="doc.txt", page=None, text="short text")
    chunks = chunk_pages([page], max_chars=800)
    assert len(chunks) == 1
    assert chunks[0].chunk_id == "doc.txt_p0_0"


def test_chunk_pages_merges_short_paragraphs_into_one_chunk():
    """当段落之间有 \\n\\n、且每段都远小于 max_chars 时，多个段落应该被"装箱"
    合并进同一个 chunk，而不是一段一个 chunk（那样会切得太碎，参见之前
    讨论过的"语义碎片化"问题）。
    """
    text = "para one\n\npara two\n\npara three"
    page = RawPage(source="doc.md", page=None, text=text)

    chunks = chunk_pages([page], max_chars=800)

    assert len(chunks) == 1
    assert "para one" in chunks[0].text
    assert "para two" in chunks[0].text
    assert "para three" in chunks[0].text
