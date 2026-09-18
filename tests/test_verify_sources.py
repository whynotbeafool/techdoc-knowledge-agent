import importlib.util
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = PROJECT_ROOT / "data" / "corpus"


def _load_script():
    spec = importlib.util.spec_from_file_location(
        "verify_sources", PROJECT_ROOT / "scripts" / "verify_sources.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


verify_sources = _load_script()


def _sources(*entries):
    return {"schema_version": "0.2", "documents": list(entries)}


def _entry(document_id="doc", revision="v1", url="https://example/x", kind="github_pinned_commit"):
    return {"document_id": document_id, "revision": revision, "url": url, "url_kind": kind}


def test_matching_bytes_are_reported_as_match():
    report = verify_sources.verify(
        _sources(_entry()),
        {("doc", "v1"): "sha256:abc"},
        document_id=None,
        fetch=lambda url: "sha256:abc",
    )

    assert report["counts"] == {"match": 1}


def test_drifted_url_reports_both_hashes_rather_than_just_failing():
    """A mismatch has to be actionable: the report must say what it got."""
    report = verify_sources.verify(
        _sources(_entry()),
        {("doc", "v1"): "sha256:frozen"},
        document_id=None,
        fetch=lambda url: "sha256:changed",
    )

    (result,) = report["results"]
    assert result["status"] == "mismatch"
    assert result["expected"] == "sha256:frozen"
    assert result["actual"] == "sha256:changed"


def test_network_failure_is_distinguished_from_drift():
    """A 404 or a dropped connection means "cannot verify", not "content changed"."""

    def _boom(url):
        raise OSError("connection reset")

    report = verify_sources.verify(
        _sources(_entry()),
        {("doc", "v1"): "sha256:frozen"},
        document_id=None,
        fetch=_boom,
    )

    (result,) = report["results"]
    assert result["status"] == "fetch_failed"
    assert "connection reset" in result["detail"]


def test_entry_for_a_revision_missing_from_the_manifest_is_flagged():
    report = verify_sources.verify(
        _sources(_entry(revision="v9")),
        {("doc", "v1"): "sha256:frozen"},
        document_id=None,
        fetch=lambda url: "sha256:frozen",
    )

    assert report["results"][0]["status"] == "no_such_revision_in_manifest"


def test_every_frozen_revision_has_a_recorded_source():
    """documents.jsonl and sources.json must not drift apart.

    A revision that exists in the corpus but has no provenance entry is exactly
    how pep8@v1 slipped in unexamined.
    """
    manifest = verify_sources.load_expected_hashes(CORPUS_DIR)
    sources = json.loads((CORPUS_DIR / "sources.json").read_text(encoding="utf-8"))
    recorded = {(e["document_id"], e["revision"]) for e in sources["documents"]}

    assert set(manifest) == recorded


def test_github_sources_are_pinned_to_a_commit_not_a_branch():
    """A branch URL silently stops reproducing the frozen bytes; the fastapi one already did."""
    sources = json.loads((CORPUS_DIR / "sources.json").read_text(encoding="utf-8"))
    branch_refs = [
        entry["document_id"]
        for entry in sources["documents"]
        if entry["url_kind"] == "github_moving_ref"
    ]

    assert branch_refs == []
