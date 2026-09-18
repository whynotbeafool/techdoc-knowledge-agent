"""Pure helpers for auditing embedder input truncation.

Kept free of tokenizer and corpus dependencies so the boundary arithmetic can
be tested offline; the script supplies real encodings.
"""


def visible_character_count(encoding, text_length: int, max_tokens: int) -> int:
    """Characters the embedder actually sees before truncation kicks in.

    ``encoding`` is a tokenizers ``Encoding``: ``ids`` gives the token count and
    ``offsets`` maps each token back to a ``(start, end)`` character span. When
    the text fits, everything is visible; otherwise the window ends where the
    last surviving token ends.
    """
    if max_tokens <= 0:
        raise ValueError("max_tokens must be positive")
    if len(encoding.ids) <= max_tokens:
        return text_length
    return encoding.offsets[max_tokens - 1][1]


def evidence_beyond_visible_window(
    *,
    evidence_start: int,
    evidence_end: int,
    chunk_start: int,
    chunk_end: int,
    visible_chars: int,
) -> int:
    """Characters of this evidence span that fall past the truncation point.

    Offsets are canonical-text coordinates for the evidence and the chunk, and
    a chunk-relative count for ``visible_chars``. Returns 0 when the whole
    overlap is visible, so a caller can treat any positive value as "the
    embedder never saw this part of the gold evidence".
    """
    overlap_start = max(evidence_start, chunk_start) - chunk_start
    overlap_end = min(evidence_end, chunk_end) - chunk_start
    if overlap_end <= overlap_start:
        return 0
    if overlap_end <= visible_chars:
        return 0
    return overlap_end - max(overlap_start, visible_chars)
