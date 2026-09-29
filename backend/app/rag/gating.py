"""Gold-free candidate gates for the selective-answering development protocol."""

import math
import re
from dataclasses import dataclass

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+")
# Fixed stoplist; independent of questions, labels, and outcomes.
STOPWORDS = frozenset(
    "a an the is are was were be been being do does did how what which who when where why "
    "of to in on at for from by with and or as it its this that these those".split()
)


@dataclass(frozen=True)
class ContextChunk:
    text: str
    score: float


def runtime_features(question: str, chunks: list[ContextChunk]) -> dict:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("A nonempty question is required")
    if any(not isinstance(c, ContextChunk) for c in chunks):
        raise TypeError("Only ContextChunk text/score objects are accepted; no QA records")
    if any(
        not isinstance(c.text, str)
        or isinstance(c.score, bool)
        or not isinstance(c.score, (int, float))
        or not math.isfinite(c.score)
        for c in chunks
    ):
        raise ValueError("Context text and finite numeric scores are required")
    tokens = set(TOKEN_PATTERN.findall(question.lower())) - STOPWORDS
    context_tokens = set(TOKEN_PATTERN.findall(" ".join(c.text for c in chunks).lower()))
    return {
        "top_score": chunks[0].score if chunks else None,
        "question_token_n": len(tokens),
        "question_context_token_recall": len(tokens & context_tokens) / len(tokens) if tokens else None,
        "context_chunk_n": len(chunks),
    }


def gate(
    question: str,
    chunks: list[ContextChunk],
    *,
    strategy: str,
    score_threshold: float = 0.0,
    lexical_threshold: float = 0.0,
) -> dict:
    if strategy not in {"A", "B", "C"}:
        raise ValueError("Unknown strategy")
    if (
        isinstance(score_threshold, bool)
        or not isinstance(score_threshold, (int, float))
        or not math.isfinite(score_threshold)
    ):
        raise ValueError("Score threshold must be finite")
    if (
        isinstance(lexical_threshold, bool)
        or not isinstance(lexical_threshold, (int, float))
        or not math.isfinite(lexical_threshold)
        or not 0 <= lexical_threshold <= 1
    ):
        raise ValueError("Lexical threshold must be in [0,1]")
    features = runtime_features(question, chunks)
    if strategy == "A":
        accepted = True
    else:
        accepted = features["top_score"] is not None and features["top_score"] >= score_threshold
        if strategy == "C" and lexical_threshold > 0:
            recall = features["question_context_token_recall"]
            accepted = accepted and recall is not None and recall >= lexical_threshold
    return {
        "strategy": strategy,
        "allow_generation": bool(accepted),
        "features": features,
        "scope": "runtime proxy; not semantic sufficiency or observed answer coverage",
    }
