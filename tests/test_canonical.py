import hashlib
import json
import unicodedata

import pytest
from app.corpus.canonical import (
    CANONICAL_ENCODING,
    DEFAULT_PAGE_SEPARATOR,
    UNICODE_NORMALIZATION,
    ExtractedPage,
    assemble_canonical_text,
    build_canonical_document,
    load_active_revision_records,
    load_canonical_document,
)


def test_assemble_canonical_text_preserves_page_substring_invariant():
    pages = [
        ExtractedPage(page=1, text="first page\n"),
        ExtractedPage(page=2, text="second page"),
    ]

    canonical = assemble_canonical_text(pages)

    assert canonical.text == f"first page\n{DEFAULT_PAGE_SEPARATOR}second page"
    for source_page, span in zip(pages, canonical.page_spans):
        expected = unicodedata.normalize(UNICODE_NORMALIZATION, source_page.text)
        assert canonical.text[span.start_char : span.end_char] == expected


def test_assemble_canonical_text_omits_blank_pages_without_separator():
    pages = [
        ExtractedPage(page=1, text="alpha"),
        ExtractedPage(page=2, text=" \n\t"),
        ExtractedPage(page=3, text="gamma"),
    ]

    canonical = assemble_canonical_text(pages)

    assert canonical.text == f"alpha{DEFAULT_PAGE_SEPARATOR}gamma"
    assert canonical.skipped_pages == [2]
    assert [span.page for span in canonical.page_spans] == [1, 3]
    assert canonical.page_spans[1].start_char == len("alpha") + len(DEFAULT_PAGE_SEPARATOR)


def test_assemble_canonical_text_normalizes_unicode_once():
    decomposed = "Cafe\u0301"

    canonical = assemble_canonical_text([ExtractedPage(page=1, text=decomposed)])

    assert canonical.text == "Café"
    assert unicodedata.is_normalized(UNICODE_NORMALIZATION, canonical.text)
    assert canonical.page_spans[0].end_char == len(canonical.text)


def test_build_canonical_document_writes_hashes_mapping_and_manifest(tmp_path):
    source = tmp_path / "notes.txt"
    source.write_text("Cafe\u0301\nnotes", encoding=CANONICAL_ENCODING)
    corpus_dir = tmp_path / "corpus"

    record = build_canonical_document(
        source,
        document_id="notes",
        revision="v1",
        corpus_dir=corpus_dir,
    )

    canonical_path = corpus_dir / record["canonical_text_file"]
    canonical_bytes = canonical_path.read_bytes()
    source_bytes = source.read_bytes()
    manifest_records = [
        json.loads(line)
        for line in (corpus_dir / "documents.jsonl").read_text(
            encoding=CANONICAL_ENCODING
        ).splitlines()
    ]

    assert canonical_bytes.decode(CANONICAL_ENCODING) == "Café\nnotes"
    assert record["source_hash"] == f"sha256:{hashlib.sha256(source_bytes).hexdigest()}"
    assert record["text_hash"] == f"sha256:{hashlib.sha256(canonical_bytes).hexdigest()}"
    assert record["page_spans"] == [
        {"page": None, "start_char": 0, "end_char": len("Café\nnotes")}
    ]
    assert record["extraction"]["page_separator"] == DEFAULT_PAGE_SEPARATOR
    assert record["extraction"]["unicode_normalization"] == UNICODE_NORMALIZATION
    assert record["extraction"]["newline_normalization"] == "universal_to_lf"
    assert record["extraction"]["offset_unit"] == "unicode_codepoint"
    assert manifest_records == [record]


def test_active_revision_selection_excludes_superseded_revision(tmp_path):
    corpus_dir = tmp_path / "corpus"
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    other = tmp_path / "other.txt"
    first.write_text("obsolete", encoding=CANONICAL_ENCODING)
    second.write_text("current", encoding=CANONICAL_ENCODING)
    other.write_text("other", encoding=CANONICAL_ENCODING)
    build_canonical_document(
        first, document_id="notes", revision="v1", corpus_dir=corpus_dir
    )
    build_canonical_document(
        second, document_id="notes", revision="v2", corpus_dir=corpus_dir
    )
    build_canonical_document(
        other, document_id="other", revision="v1", corpus_dir=corpus_dir
    )
    (corpus_dir / "active-revisions.json").write_text(
        json.dumps(
            {
                "schema_version": "0.1",
                "documents": [
                    {"document_id": "notes", "revision": "v2"},
                    {"document_id": "other", "revision": "v1"},
                ],
            }
        ),
        encoding=CANONICAL_ENCODING,
    )

    active = load_active_revision_records(corpus_dir)

    assert [(record["document_id"], record["revision"]) for record in active] == [
        ("notes", "v2"),
        ("other", "v1"),
    ]


def test_active_revision_selection_requires_every_manifest_document(tmp_path):
    corpus_dir = tmp_path / "corpus"
    source = tmp_path / "notes.txt"
    other = tmp_path / "other.txt"
    source.write_text("notes", encoding=CANONICAL_ENCODING)
    other.write_text("other", encoding=CANONICAL_ENCODING)
    build_canonical_document(
        source, document_id="notes", revision="v1", corpus_dir=corpus_dir
    )
    build_canonical_document(
        other, document_id="other", revision="v1", corpus_dir=corpus_dir
    )
    (corpus_dir / "active-revisions.json").write_text(
        json.dumps(
            {
                "schema_version": "0.1",
                "documents": [{"document_id": "notes", "revision": "v1"}],
            }
        ),
        encoding=CANONICAL_ENCODING,
    )

    with pytest.raises(ValueError, match="does not match manifest documents"):
        load_active_revision_records(corpus_dir)


def test_build_canonical_document_is_idempotent_for_same_revision(tmp_path):
    source = tmp_path / "notes.txt"
    source.write_text("same content", encoding=CANONICAL_ENCODING)
    corpus_dir = tmp_path / "corpus"

    first = build_canonical_document(
        source,
        document_id="notes",
        revision="v1",
        corpus_dir=corpus_dir,
    )
    second = build_canonical_document(
        source,
        document_id="notes",
        revision="v1",
        corpus_dir=corpus_dir,
    )

    manifest_lines = (corpus_dir / "documents.jsonl").read_text(
        encoding=CANONICAL_ENCODING
    ).splitlines()
    assert first == second
    assert len(manifest_lines) == 1


def test_build_canonical_document_rejects_changed_existing_revision(tmp_path):
    source = tmp_path / "notes.txt"
    source.write_text("first content", encoding=CANONICAL_ENCODING)
    corpus_dir = tmp_path / "corpus"
    build_canonical_document(
        source,
        document_id="notes",
        revision="v1",
        corpus_dir=corpus_dir,
    )
    source.write_text("changed content", encoding=CANONICAL_ENCODING)

    with pytest.raises(ValueError, match="use a new revision"):
        build_canonical_document(
            source,
            document_id="notes",
            revision="v1",
            corpus_dir=corpus_dir,
        )


def test_load_canonical_document_verifies_and_returns_revision(tmp_path):
    source = tmp_path / "notes.txt"
    source.write_text("trusted content", encoding=CANONICAL_ENCODING)
    corpus_dir = tmp_path / "corpus"
    record = build_canonical_document(
        source,
        document_id="notes",
        revision="v1",
        corpus_dir=corpus_dir,
    )

    loaded = load_canonical_document(
        corpus_dir,
        document_id="notes",
        revision="v1",
    )

    assert loaded.text == "trusted content"
    assert loaded.metadata == record


def test_load_canonical_document_rejects_tampered_text(tmp_path):
    source = tmp_path / "notes.txt"
    source.write_text("trusted content", encoding=CANONICAL_ENCODING)
    corpus_dir = tmp_path / "corpus"
    record = build_canonical_document(
        source,
        document_id="notes",
        revision="v1",
        corpus_dir=corpus_dir,
    )
    (corpus_dir / record["canonical_text_file"]).write_text(
        "tampered content",
        encoding=CANONICAL_ENCODING,
    )

    with pytest.raises(ValueError, match="hash mismatch"):
        load_canonical_document(
            corpus_dir,
            document_id="notes",
            revision="v1",
        )


def test_load_canonical_document_rejects_path_outside_corpus(tmp_path):
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding=CANONICAL_ENCODING)
    record = {
        "document_id": "notes",
        "revision": "v1",
        "canonical_text_file": "../outside.txt",
        "text_hash": f"sha256:{hashlib.sha256(outside.read_bytes()).hexdigest()}",
    }
    (corpus_dir / "documents.jsonl").write_text(
        json.dumps(record) + "\n",
        encoding=CANONICAL_ENCODING,
    )

    with pytest.raises(ValueError, match="escapes corpus"):
        load_canonical_document(
            corpus_dir,
            document_id="notes",
            revision="v1",
        )


def test_load_canonical_document_rejects_absolute_canonical_path(tmp_path):
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding=CANONICAL_ENCODING)
    record = {
        "document_id": "notes",
        "revision": "v1",
        "canonical_text_file": str(outside.resolve()),
        "text_hash": f"sha256:{hashlib.sha256(outside.read_bytes()).hexdigest()}",
    }
    (corpus_dir / "documents.jsonl").write_text(
        json.dumps(record) + "\n",
        encoding=CANONICAL_ENCODING,
    )

    with pytest.raises(ValueError, match="escapes corpus"):
        load_canonical_document(
            corpus_dir,
            document_id="notes",
            revision="v1",
        )


def test_load_canonical_document_rejects_missing_revision(tmp_path):
    corpus_dir = tmp_path / "corpus"

    with pytest.raises(KeyError, match="missing@v1"):
        load_canonical_document(
            corpus_dir,
            document_id="missing",
            revision="v1",
        )


def test_load_canonical_document_rejects_ambiguous_offset_unit(tmp_path):
    source = tmp_path / "notes.txt"
    source.write_text("abcde", encoding=CANONICAL_ENCODING)
    corpus_dir = tmp_path / "corpus"
    build_canonical_document(
        source,
        document_id="notes",
        revision="v1",
        corpus_dir=corpus_dir,
    )
    manifest_path = corpus_dir / "documents.jsonl"
    record = json.loads(manifest_path.read_text(encoding=CANONICAL_ENCODING))
    record["extraction"].pop("offset_unit")
    manifest_path.write_text(
        json.dumps(record) + "\n",
        encoding=CANONICAL_ENCODING,
    )

    with pytest.raises(ValueError, match="offset unit"):
        load_canonical_document(
            corpus_dir,
            document_id="notes",
            revision="v1",
        )


@pytest.mark.parametrize(
    "page_spans",
    [
        [{"page": 1, "start_char": 1, "end_char": 5}],
        [{"page": 1, "start_char": 0, "end_char": 4}],
        [
            {"page": 1, "start_char": 0, "end_char": 2},
            {"page": 2, "start_char": 2, "end_char": 5},
        ],
        [
            {"page": 1, "start_char": 0, "end_char": 2},
            {"page": 2, "start_char": 3, "end_char": 5},
        ],
    ],
)
def test_load_canonical_document_rejects_invalid_page_spans(tmp_path, page_spans):
    source = tmp_path / "notes.txt"
    source.write_text("abcde", encoding=CANONICAL_ENCODING)
    corpus_dir = tmp_path / "corpus"
    build_canonical_document(
        source,
        document_id="notes",
        revision="v1",
        corpus_dir=corpus_dir,
    )
    manifest_path = corpus_dir / "documents.jsonl"
    record = json.loads(manifest_path.read_text(encoding=CANONICAL_ENCODING))
    record["page_spans"] = page_spans
    manifest_path.write_text(
        json.dumps(record) + "\n",
        encoding=CANONICAL_ENCODING,
    )

    with pytest.raises(ValueError, match="page span|Page span|First page|Last page"):
        load_canonical_document(
            corpus_dir,
            document_id="notes",
            revision="v1",
        )
