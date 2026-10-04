import importlib.util
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("pilot", ROOT / "scripts/collect_selective_pilot.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_pilot_preflight_is_offline_and_binds_all_review_inputs(tmp_path):
    requests, checks, config, lock = MODULE.prepare()
    assert len(requests) == len(checks) == 30
    assert config["cost_limit"] == "1"
    for name in [str(MODULE.REVIEW / "LOCK.json"), *lock["sha256"]]:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    assert MODULE.prepare(tmp_path)[2] == config
    path = tmp_path / MODULE.REVIEW / "context-review.jsonl"
    rows = path.read_text(encoding="utf-8").splitlines()
    row = json.loads(rows[0])
    row["context_sufficient"] = not row["context_sufficient"]
    rows[0] = json.dumps(row)
    path.write_text("\n".join(rows), encoding="utf-8")
    with pytest.raises(ValueError, match="Locked input changed"):
        MODULE.prepare(tmp_path)
