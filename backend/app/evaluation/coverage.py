"""Textual coverage of selected canonical evidence, measurement spec coverage-v1.

These are offline location/text diagnostics, never semantic sufficiency labels.
"""


def span_coverage(quote: str, start: int, intervals: list[tuple[int, int]]) -> dict:
    if not isinstance(quote, str) or not quote:
        raise ValueError("Evidence quote must be nonempty")
    if type(start) is not int or start < 0:
        raise ValueError("Evidence offset must be a nonnegative integer")
    covered = [False] * len(quote)
    end = start + len(quote)
    for left, right in intervals:
        if type(left) is not int or type(right) is not int or left < 0 or right <= left:
            raise ValueError("Retrieved intervals must be positive-length canonical ranges")
        for offset in range(max(start, left), min(end, right)):
            covered[offset - start] = True
    nonspace = [i for i, char in enumerate(quote) if not char.isspace()]
    covered_n = sum(covered)
    nonspace_covered = sum(covered[i] for i in nonspace)
    return {
        "length": len(quote),
        "covered": covered_n,
        "any_overlap": covered_n > 0,
        "full_char": covered_n == len(quote),
        "char_fraction": covered_n / len(quote),
        "nonspace_length": len(nonspace),
        "nonspace_covered": nonspace_covered,
        "full_nonspace": nonspace_covered == len(nonspace) if nonspace else None,
        "nonspace_fraction": nonspace_covered / len(nonspace) if nonspace else None,
    }


def evidence_coverage(evidence: list[dict], retrieved: list[dict]) -> dict:
    spans = []
    for item in evidence:
        if item["end_char"] - item["start_char"] != len(item["quote"]):
            raise ValueError("Quote length differs from evidence coordinates")
        matching = [
            (c["start_char"], c["end_char"])
            for c in retrieved
            if (c["document_id"], c["revision"]) == (item["document_id"], item["revision"])
        ]
        spans.append(span_coverage(item["quote"], item["start_char"], matching))
    result = {"spans": spans, "evidence_n": len(spans)}
    for suffix, field in [
        ("any", "any_overlap"),
        ("full_char", "full_char"),
        ("full_nonspace", "full_nonspace"),
    ]:
        values = [s[field] for s in spans]
        valid = bool(values) and all(v is not None for v in values)
        result[f"recall_{suffix}"] = sum(values) / len(values) if valid else None
        result[f"complete_{suffix}"] = all(values) if valid else None
    for field in ("char_fraction", "nonspace_fraction"):
        values = [s[field] for s in spans]
        result[f"mean_{field}"] = (
            sum(values) / len(values) if values and all(v is not None for v in values) else None
        )
    return result
