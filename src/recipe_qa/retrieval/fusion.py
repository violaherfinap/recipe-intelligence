"""Rank fusion for hybrid retrieval."""

from __future__ import annotations

from collections.abc import Sequence


def reciprocal_rank_fusion(
    rankings: Sequence[Sequence[str]],
    k: int = 60,
) -> list[tuple[str, float]]:
    """Fuse ranked passage-id lists with reciprocal rank fusion.

    ``score(d) = sum_i 1 / (k + rank_i(d))`` with 1-based ranks.
    """
    if k <= 0:
        raise ValueError("k must be positive")

    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, passage_id in enumerate(ranking, start=1):
            scores[passage_id] = scores.get(passage_id, 0.0) + 1.0 / (k + rank)

    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))
