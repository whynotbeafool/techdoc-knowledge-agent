def evidence_span_hits_chunk(
    evidence_start: int,
    evidence_end: int,
    chunk_start: int,
    chunk_end: int,
) -> bool:
    """Return whether a chunk has any positive-length overlap with evidence.

    All coordinates are zero-based, half-open character offsets ``[start, end)``
    into the same immutable canonical-text revision. Merely touching at a
    boundary is not an overlap.

    Raises:
        ValueError: If either span is empty, reversed, or starts before zero.
    """
    _validate_span(evidence_start, evidence_end, name="evidence")
    _validate_span(chunk_start, chunk_end, name="chunk")
    return max(evidence_start, chunk_start) < min(evidence_end, chunk_end)


def _validate_span(start: int, end: int, *, name: str) -> None:
    if start < 0:
        raise ValueError(f"{name} span start must be non-negative")
    if start >= end:
        raise ValueError(f"{name} span must satisfy start < end")
