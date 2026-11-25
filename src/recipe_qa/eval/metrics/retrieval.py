"""Retrieval metrics computed against annotated qrels."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence


def _relevant_ids(relevance: Mapping[str, int], threshold: int) -> set[str]:
    return {passage_id for passage_id, grade in relevance.items() if grade >= threshold}


def recall_at_k(
    ranked: Sequence[str],
    relevance: Mapping[str, int],
    k: int,
    threshold: int = 1,
) -> float:
    relevant = _relevant_ids(relevance, threshold)
    if not relevant:
        return 0.0
    retrieved = set(ranked[:k])
    return len(relevant & retrieved) / len(relevant)


def _gain(grade: int) -> float:
    return float((2**grade) - 1)


def ndcg_at_k(
    ranked: Sequence[str],
    relevance: Mapping[str, int],
    k: int = 10,
) -> float:
    dcg = sum(
        _gain(relevance.get(passage_id, 0)) / math.log2(rank + 1)
        for rank, passage_id in enumerate(ranked[:k], start=1)
    )
    ideal = sorted(relevance.values(), reverse=True)[:k]
    idcg = sum(_gain(grade) / math.log2(rank + 1) for rank, grade in enumerate(ideal, start=1))
    if idcg == 0:
        return 0.0
    return dcg / idcg


def mrr_at_k(
    ranked: Sequence[str],
    relevance: Mapping[str, int],
    k: int = 10,
    threshold: int = 1,
) -> float:
    for rank, passage_id in enumerate(ranked[:k], start=1):
        if relevance.get(passage_id, 0) >= threshold:
            return 1.0 / rank
    return 0.0


def evaluate_retrieval(
    qrels: Mapping[str, Mapping[str, int]],
    rankings: Mapping[str, Sequence[str]],
    recall_ks: Sequence[int] = (5, 10),
    rank_k: int = 10,
    threshold: int = 1,
) -> dict[str, float | int]:
    scores: dict[str, list[float]] = {f"recall@{k}": [] for k in recall_ks}
    scores[f"ndcg@{rank_k}"] = []
    scores[f"mrr@{rank_k}"] = []

    for query_id, relevance in qrels.items():
        if not _relevant_ids(relevance, threshold):
            continue
        ranked = rankings.get(query_id, [])
        for k in recall_ks:
            scores[f"recall@{k}"].append(recall_at_k(ranked, relevance, k, threshold))
        scores[f"ndcg@{rank_k}"].append(ndcg_at_k(ranked, relevance, rank_k))
        scores[f"mrr@{rank_k}"].append(mrr_at_k(ranked, relevance, rank_k, threshold))

    result: dict[str, float | int] = {"queries": len(scores[f"mrr@{rank_k}"])}
    for name, values in scores.items():
        result[name] = sum(values) / len(values) if values else 0.0
    return result
