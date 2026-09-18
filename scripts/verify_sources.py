"""Check that each recorded source URL still serves the frozen source bytes.

Joins data/corpus/sources.json (where a document came from) against
data/corpus/documents.jsonl (the authoritative source_hash) and re-downloads
each URL. A mismatch does not invalidate any run -- canonical text is
committed and hash-verified independently -- but it does mean the URL alone no
longer reconstructs the corpus, which is what a reader of the dataset would
try first.

Network access required. Writes nothing; prints JSON.

    python scripts/verify_sources.py
    python scripts/verify_sources.py --document-id fastapi_first_steps
"""

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CORPUS_DIR = PROJECT_ROOT / "data" / "corpus"
USER_AGENT = "techdoc-knowledge-agent source verifier"
TIMEOUT_SECONDS = 120


def load_expected_hashes(corpus_dir: Path) -> dict[tuple[str, str], str]:
    expected = {}
    for line in (corpus_dir / "documents.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        expected[(record["document_id"], record["revision"])] = record["source_hash"]
    return expected


def fetch_sha256(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return f"sha256:{hashlib.sha256(response.read()).hexdigest()}"


def verify(sources: dict, expected: dict, *, document_id: str | None, fetch=fetch_sha256) -> dict:
    results = []
    for entry in sources["documents"]:
        if document_id and entry["document_id"] != document_id:
            continue
        key = (entry["document_id"], entry["revision"])
        want = expected.get(key)
        result = {
            "document_id": entry["document_id"],
            "revision": entry["revision"],
            "url": entry["url"],
            "url_kind": entry["url_kind"],
        }
        if want is None:
            result["status"] = "no_such_revision_in_manifest"
            results.append(result)
            continue
        try:
            got = fetch(entry["url"])
        except Exception as exc:  # network, 404, TLS -- all are "cannot verify now"
            result["status"] = "fetch_failed"
            result["detail"] = f"{type(exc).__name__}: {exc}"
            results.append(result)
            continue
        result["status"] = "match" if got == want else "mismatch"
        if got != want:
            result["expected"] = want
            result["actual"] = got
        results.append(result)

    counts: dict[str, int] = {}
    for item in results:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    return {"results": results, "counts": counts}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-dir", type=Path, default=DEFAULT_CORPUS_DIR)
    parser.add_argument("--document-id")
    args = parser.parse_args()

    sources = json.loads((args.corpus_dir / "sources.json").read_text(encoding="utf-8"))
    expected = load_expected_hashes(args.corpus_dir)
    report = verify(sources, expected, document_id=args.document_id)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    # A mismatch is a finding to record, not a build failure; only a malformed
    # manifest is an error.
    return 1 if report["counts"].get("no_such_revision_in_manifest") else 0


if __name__ == "__main__":
    raise SystemExit(main())
