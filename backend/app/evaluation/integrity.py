"""Explicit byte identities for frozen inputs; no permissive JSON equivalence."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def verify_frozen_qa(path: Path, expected: str | None = None) -> dict:
    manifest = json.loads((ROOT / "data/eval/frozen-inputs.json").read_text(encoding="utf-8"))
    qa = manifest["qa"]
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    accepted = {qa["original_sha256"], qa["legacy_git_lf_sha256"]}
    if actual not in accepted:
        raise ValueError("Frozen first-pass hash mismatch")
    if expected is not None and expected.removeprefix("sha256:") not in accepted:
        raise ValueError("Saved run does not reference this frozen QA")
    return {
        "actual_sha256": actual,
        "original_sha256": qa["original_sha256"],
        "legacy_lf_serialization": actual != qa["original_sha256"],
    }


def verify_auxiliary_inputs() -> None:
    manifest = json.loads((ROOT / "data/eval/frozen-inputs.json").read_text(encoding="utf-8"))
    for name, expected in manifest["lf_normalized_sha256"].items():
        actual = hashlib.sha256((ROOT / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        if actual != expected:
            raise ValueError(f"Frozen input mismatch: {name}")
