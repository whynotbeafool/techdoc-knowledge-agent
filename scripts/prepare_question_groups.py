"""Build a provisional group manifest from reviewed provenance; no API calls."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
from app.evaluation.grouping import build_groups  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = args.input.read_bytes()
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    if not rows:
        raise ValueError("Empty provenance input")
    result = {
        "status": "provisional_not_evaluation_frozen",
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "limitation": "Declared links only; semantic completeness and exposure require review. "
                      "Do not rename questions or change membership to obtain a preferred split.",
        "records": build_groups(rows),
    }
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


if __name__ == "__main__":
    main()
