from dataclasses import dataclass

import pytest
from app.evaluation.truncation import (
    evidence_beyond_visible_window,
    visible_character_count,
)


@dataclass
class _Encoding:
    """Minimal stand-in for a tokenizers Encoding."""

    ids: list
    offsets: list


def test_short_text_is_fully_visible():
    encoding = _Encoding(ids=[1, 2, 3], offsets=[(0, 3), (4, 8), (9, 12)])

    assert visible_character_count(encoding, text_length=12, max_tokens=256) == 12


def test_visible_window_ends_where_the_last_surviving_token_ends():
    """Truncation keeps max_tokens tokens, so the window ends at token max_tokens-1."""
    encoding = _Encoding(
        ids=[1, 2, 3, 4],
        offsets=[(0, 3), (4, 8), (9, 14), (15, 20)],
    )

    assert visible_character_count(encoding, text_length=20, max_tokens=2) == 8


def test_visible_character_count_rejects_nonpositive_limit():
    encoding = _Encoding(ids=[1], offsets=[(0, 1)])

    with pytest.raises(ValueError):
        visible_character_count(encoding, text_length=1, max_tokens=0)


@pytest.mark.parametrize(
    ("evidence", "visible", "expected", "case"),
    [
        ((100, 150), 500, 0, "evidence well inside the window"),
        ((100, 150), 50, 50, "evidence starts after the cut: entirely unseen"),
        ((100, 150), 120, 30, "evidence straddles the cut: tail unseen"),
        ((100, 150), 150, 0, "evidence ends exactly at the cut"),
        ((900, 950), 500, 0, "evidence lies outside the chunk entirely"),
    ],
)
def test_evidence_beyond_visible_window(evidence, visible, expected, case):
    assert (
        evidence_beyond_visible_window(
            evidence_start=evidence[0],
            evidence_end=evidence[1],
            chunk_start=0,
            chunk_end=800,
            visible_chars=visible,
        )
        == expected
    ), case


def test_chunk_offsets_are_translated_to_chunk_relative_coordinates():
    """visible_chars is chunk-relative while evidence offsets are canonical-text.

    Mixing the two frames would silently mis-measure every chunk that does not
    start at offset 0, which is all of them after the first.
    """
    # Chunk covers canonical [1000, 1800); evidence at [1700, 1750) is 700-750 inside it.
    assert (
        evidence_beyond_visible_window(
            evidence_start=1700,
            evidence_end=1750,
            chunk_start=1000,
            chunk_end=1800,
            visible_chars=720,
        )
        == 30
    )
