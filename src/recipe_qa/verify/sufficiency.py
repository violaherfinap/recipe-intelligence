"""Sufficiency scoring before generation."""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..index.build import tokenize_for_index


@dataclass(frozen=True)
class SufficiencyResult:
    score: float
    top_score: float
    coverage: float
    top_passage_id: str | None = None


def sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


def coverage(query: str, passages: list[str], top_n: int = 3) -> float:
    query_tokens = set(tokenize_for_index(query))
    if not query_tokens:
        return 0.0
    text = " ".join(passages[:top_n])
    passage_tokens = set(tokenize_for_index(text))
    return len(query_tokens & passage_tokens) / len(query_tokens)


def sufficiency(query: str, hits: list, top_n: int = 3) -> SufficiencyResult:
    if not hits:
        return SufficiencyResult(score=0.0, top_score=0.0, coverage=0.0)
    top = hits[0]
    top_score = float(top.score)
    texts = [str(hit.passage.get("text", "")) for hit in hits]
    hit_coverage = coverage(query, texts, top_n=top_n)
    score = 0.6 * sigmoid(top_score) + 0.4 * hit_coverage
    return SufficiencyResult(
        score=score,
        top_score=top_score,
        coverage=hit_coverage,
        top_passage_id=top.passage_id,
    )


def should_abstain(result: SufficiencyResult, threshold: float) -> bool:
    return result.score < threshold
