import math
import re
from collections import Counter

from app.rag.chunker import Chunk

from .evidence import evidence_span_hits_chunk

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+")


class BM25Retriever:
    def __init__(
        self,
        chunks: list[Chunk],
        *,
        k1: float = 1.5,
        b: float = 0.75,
    ):
        self.chunks = chunks
        self.k1 = k1
        self.b = b
        self.term_frequencies = [Counter(_tokenize(chunk.text)) for chunk in chunks]
        self.document_lengths = [
            sum(term_frequency.values()) for term_frequency in self.term_frequencies
        ]
        self.average_document_length = (
            sum(self.document_lengths) / len(self.document_lengths) if chunks else 0.0
        )
        self.document_frequencies = Counter()
        for term_frequency in self.term_frequencies:
            self.document_frequencies.update(term_frequency.keys())

    def query_chunks(self, question: str, top_k: int = 5) -> list[dict]:
        query_terms = _tokenize(question)
        ranked = []
        for chunk, term_frequency, document_length in zip(
            self.chunks,
            self.term_frequencies,
            self.document_lengths,
        ):
            score = sum(
                self._term_score(term, term_frequency, document_length)
                for term in query_terms
            )
            ranked.append((score, chunk.chunk_id, chunk))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        return [
            _chunk_to_result(chunk, score=score)
            for score, _, chunk in ranked[:top_k]
        ]

    def _term_score(
        self,
        term: str,
        term_frequency: Counter,
        document_length: int,
    ) -> float:
        frequency = term_frequency.get(term, 0)
        if frequency == 0 or not self.chunks:
            return 0.0
        document_frequency = self.document_frequencies[term]
        inverse_document_frequency = math.log(
            1 + (len(self.chunks) - document_frequency + 0.5) / (document_frequency + 0.5)
        )
        length_ratio = (
            document_length / self.average_document_length
            if self.average_document_length
            else 0.0
        )
        denominator = frequency + self.k1 * (1 - self.b + self.b * length_ratio)
        return inverse_document_frequency * frequency * (self.k1 + 1) / denominator


class ReciprocalRankFusionRetriever:
    """Fuse ranked lists without comparing their incompatible raw scores."""

    def __init__(
        self,
        retrievers: dict[str, object],
        *,
        rank_constant: int = 60,
        candidate_depth: int = 20,
    ):
        if len(retrievers) < 2:
            raise ValueError("RRF requires at least two retrievers")
        if rank_constant < 0:
            raise ValueError("rank_constant must be non-negative")
        if candidate_depth < 1:
            raise ValueError("candidate_depth must be positive")
        self.retrievers = retrievers
        self.rank_constant = rank_constant
        self.candidate_depth = candidate_depth

    def query_chunks(self, question: str, top_k: int = 5) -> list[dict]:
        if top_k < 1:
            return []

        candidates: dict[str, dict] = {}
        depth = max(top_k, self.candidate_depth)
        for method, retriever in self.retrievers.items():
            ranked = retriever.query_chunks(question, top_k=depth)
            seen = set()
            for rank, chunk in enumerate(ranked, start=1):
                chunk_id = chunk["chunk_id"]
                if chunk_id in seen:
                    continue
                seen.add(chunk_id)
                candidate = candidates.setdefault(
                    chunk_id,
                    {
                        "chunk": chunk,
                        "rrf_score": 0.0,
                        "component_ranks": {},
                    },
                )
                candidate["rrf_score"] += 1 / (self.rank_constant + rank)
                candidate["component_ranks"][method] = rank

        ordered = sorted(
            candidates.items(),
            key=lambda item: (-item[1]["rrf_score"], item[0]),
        )
        results = []
        for _, candidate in ordered[:top_k]:
            result = dict(candidate["chunk"])
            result.pop("score", None)
            result.pop("distance", None)
            result["rrf_score"] = candidate["rrf_score"]
            result["component_ranks"] = candidate["component_ranks"]
            results.append(result)
        return results


def retrieval_metrics(qa_record: dict, ranked_chunks: list[dict], ks=(1, 3, 5)) -> dict:
    cutoff = max(ks)
    evidence = qa_record["evidence"]
    if not evidence:
        return {
            f"evidence_recall_at_{k}": None for k in ks
        } | {
            f"complete_evidence_hit_at_{k}": None for k in ks
        } | {
            "first_relevant_rank": None,
            f"reciprocal_rank_at_{cutoff}": None,
        }

    metrics = {}
    for k in ks:
        retrieved = ranked_chunks[:k]
        hits = [
            any(_chunk_hits_evidence(chunk, gold) for chunk in retrieved)
            for gold in evidence
        ]
        metrics[f"evidence_recall_at_{k}"] = sum(hits) / len(hits)
        metrics[f"complete_evidence_hit_at_{k}"] = all(hits)

    first_relevant_rank = next(
        (
            rank
            for rank, chunk in enumerate(ranked_chunks[:cutoff], start=1)
            if any(_chunk_hits_evidence(chunk, gold) for gold in evidence)
        ),
        None,
    )
    metrics["first_relevant_rank"] = first_relevant_rank
    metrics[f"reciprocal_rank_at_{cutoff}"] = (
        1 / first_relevant_rank if first_relevant_rank is not None else 0.0
    )
    return metrics


def _chunk_hits_evidence(chunk: dict, evidence: dict) -> bool:
    if (
        chunk.get("document_id") != evidence["document_id"]
        or chunk.get("revision") != evidence["revision"]
        or chunk.get("start_char") is None
        or chunk.get("end_char") is None
    ):
        return False
    return evidence_span_hits_chunk(
        evidence["start_char"],
        evidence["end_char"],
        chunk["start_char"],
        chunk["end_char"],
    )


def _tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())


def _chunk_to_result(chunk: Chunk, *, score: float) -> dict:
    return {
        "chunk_id": chunk.chunk_id,
        "source": chunk.source,
        "page": chunk.page,
        "text": chunk.text,
        "score": score,
        "start_char": chunk.start_char,
        "end_char": chunk.end_char,
        "document_id": chunk.document_id,
        "revision": chunk.revision,
    }
