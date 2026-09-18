import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "coverage_audit", Path(__file__).parents[1] / "scripts/audit_evidence_coverage.py"
)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


@pytest.mark.parametrize("intervals, expected", [
    ([], 0),
    ([(0, 100), (200, 300)], 0),
    ([(199, 220)], 1),
    ([(90, 150), (140, 210)], 100),
    ([(100, 150), (150, 200)], 100),
    ([(100, 149), (151, 200)], 98),
    ([(90, 210), (120, 130)], 100),
])
def test_clipped_union(intervals, expected):
    assert audit.covered_length(100, 200, intervals) == expected
