"""Integrity checks for the committed canonical corpus.

These run against the real ``data/corpus/`` artifacts rather than fixtures,
because the failure mode they guard against only appears once the files have
made a round trip through git.
"""

import json
from pathlib import Path

import pytest
from app.corpus import load_active_revision_records, load_canonical_document

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = PROJECT_ROOT / "data" / "corpus"
MANIFEST_PATH = CORPUS_DIR / "documents.jsonl"


def _manifest_records() -> list[dict]:
    if not MANIFEST_PATH.exists():
        return []
    return [
        json.loads(line)
        for line in MANIFEST_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


RECORDS = _manifest_records()
RECORD_IDS = [f"{r['document_id']}@{r['revision']}" for r in RECORDS]
ACTIVE_RECORDS = load_active_revision_records(CORPUS_DIR)


@pytest.mark.skipif(not RECORDS, reason="no canonical corpus committed")
@pytest.mark.parametrize("record", RECORDS, ids=RECORD_IDS)
def test_canonical_artifact_has_no_crlf(record):
    """Canonical text must stay byte-exact through git.

    ``core.autocrlf=true`` (the Windows default) rewrites LF to CRLF on
    checkout, which changes the file's bytes, breaks its recorded ``text_hash``
    and shifts every character offset recorded against it. ``.gitattributes``
    marks these files ``-text`` to prevent that; this test fails if that
    protection is ever removed. CI runs on Linux, where the conversion does not
    happen, so nothing else in the suite would catch it.
    """
    raw = (CORPUS_DIR / record["canonical_text_file"]).read_bytes()
    assert b"\r\n" not in raw


@pytest.mark.skipif(not RECORDS, reason="no canonical corpus committed")
@pytest.mark.parametrize("record", RECORDS, ids=RECORD_IDS)
def test_canonical_artifact_matches_recorded_hash(record):
    """Every committed revision must still load and pass hash verification."""
    document = load_canonical_document(
        CORPUS_DIR,
        document_id=record["document_id"],
        revision=record["revision"],
    )
    assert document.metadata == record


@pytest.mark.skipif(not RECORDS, reason="no canonical corpus committed")
@pytest.mark.parametrize("record", RECORDS, ids=RECORD_IDS)
def test_page_spans_tile_the_canonical_text(record):
    """Page spans must stay inside the text, be ordered, and reach its end.

    ``text_hash`` covers the text but not the manifest, so a hand-edited
    ``page_spans`` entry would otherwise pass verification unnoticed.
    """
    document = load_canonical_document(
        CORPUS_DIR,
        document_id=record["document_id"],
        revision=record["revision"],
    )
    spans = document.metadata["page_spans"]

    assert spans, "a canonical revision must record at least one page span"
    assert spans[0]["start_char"] == 0
    assert spans[-1]["end_char"] == len(document.text)
    for previous, current in zip(spans, spans[1:]):
        assert previous["end_char"] <= current["start_char"]
    for span in spans:
        assert span["start_char"] < span["end_char"] <= len(document.text)


def test_active_corpus_selects_real_pep8_revision():
    pep8_record = next(
        record for record in ACTIVE_RECORDS if record["document_id"] == "pep8"
    )
    document = load_canonical_document(
        CORPUS_DIR,
        document_id=pep8_record["document_id"],
        revision=pep8_record["revision"],
    )

    assert pep8_record["revision"] == "v2"
    assert document.text.startswith("PEP: 8\nTitle: Style Guide for Python Code")
    assert "<title>Page not found" not in document.text
