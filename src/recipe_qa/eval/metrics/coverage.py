from __future__ import annotations

from collections.abc import Iterable, Sequence


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def doc_recall_at_k(
    ranked_doc_ids: Sequence[str],
    relevant_doc_ids: Iterable[str],
    k: int,
) -> float:
    relevant = set(relevant_doc_ids)
    if not relevant or k <= 0:
        return 0.0
    retrieved = set(_unique(ranked_doc_ids)[:k])
    return len(retrieved & relevant) / len(relevant)


def judged_rate_at_k(
    ranked_passage_ids: Sequence[str],
    judged_passage_ids: Iterable[str],
    k: int,
) -> float:
    retrieved = list(ranked_passage_ids)[:k]
    if not retrieved:
        return 0.0
    judged = set(judged_passage_ids)
    return sum(1 for passage_id in retrieved if passage_id in judged) / len(retrieved)


def split_coverage_at_k(
    ranked_doc_ids: Sequence[str],
    test_doc_ids: Iterable[str],
    k: int,
) -> float:
    retrieved = list(ranked_doc_ids)[:k]
    if not retrieved:
        return 0.0
    test_docs = set(test_doc_ids)
    return sum(1 for doc_id in retrieved if doc_id in test_docs) / len(retrieved)


def unjudged_test_rate_at_k(
    ranked_passage_ids: Sequence[str],
    ranked_doc_ids: Sequence[str],
    judged_passage_ids: Iterable[str],
    test_doc_ids: Iterable[str],
    k: int,
) -> float:
    pairs = list(zip(ranked_passage_ids, ranked_doc_ids, strict=False))[:k]
    judged = set(judged_passage_ids)
    test_docs = set(test_doc_ids)
    test_pairs = [(passage_id, doc_id) for passage_id, doc_id in pairs if doc_id in test_docs]
    if not test_pairs:
        return 0.0
    unjudged = sum(1 for passage_id, _ in test_pairs if passage_id not in judged)
    return unjudged / len(test_pairs)
