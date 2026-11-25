from __future__ import annotations

import math

import pytest

from recipe_qa.eval.metrics.retrieval import (
    evaluate_retrieval,
    mrr_at_k,
    ndcg_at_k,
    recall_at_k,
)


def test_recall_at_k_counts_relevant_hits() -> None:
    ranked = ["a", "b", "c", "d"]
    relevance = {"a": 2, "c": 1, "z": 2}
    assert recall_at_k(ranked, relevance, k=2) == pytest.approx(1 / 3)
    assert recall_at_k(ranked, relevance, k=4) == pytest.approx(2 / 3)
    assert recall_at_k(ranked, relevance, k=10) == pytest.approx(2 / 3)


def test_recall_at_k_supports_level_two_threshold() -> None:
    relevance = {"a": 2, "b": 1}
    assert recall_at_k(["a", "b"], relevance, k=2, threshold=2) == pytest.approx(1.0)
    assert recall_at_k(["b"], relevance, k=1, threshold=2) == pytest.approx(0.0)


def test_recall_at_k_without_relevant_passages_is_zero() -> None:
    assert recall_at_k(["a", "b"], {}, k=5) == 0.0
    assert recall_at_k(["a", "b"], {"a": 0}, k=5) == 0.0


def test_ndcg_at_k_matches_hand_calculation() -> None:
    ranked = ["a", "b", "c"]
    relevance = {"a": 2, "c": 1, "d": 2}
    expected = 3.0 / (3.0 + 3.0 / math.log2(3))
    assert ndcg_at_k(ranked, relevance, k=2) == pytest.approx(expected)


def test_ndcg_at_k_is_one_for_ideal_ranking() -> None:
    assert ndcg_at_k(["a", "b"], {"a": 2, "b": 1}, k=2) == pytest.approx(1.0)


def test_ndcg_at_k_without_relevant_passages_is_zero() -> None:
    assert ndcg_at_k(["a"], {"a": 0}, k=10) == 0.0


def test_mrr_at_k_returns_reciprocal_first_relevant_rank() -> None:
    assert mrr_at_k(["x", "a", "y"], {"a": 1}, k=10) == pytest.approx(0.5)
    assert mrr_at_k(["x", "a"], {"a": 2}, k=10, threshold=2) == pytest.approx(0.5)
    assert mrr_at_k(["x", "y"], {"a": 1}, k=10) == 0.0


def test_evaluate_retrieval_skips_queries_without_relevant() -> None:
    qrels = {"q1": {"a": 2, "b": 0}, "q2": {"x": 0}}
    rankings = {"q1": ["b", "a"], "q2": ["x"]}
    result = evaluate_retrieval(qrels, rankings, recall_ks=(1, 2), rank_k=2)
    assert result["queries"] == 1
    assert result["recall@1"] == pytest.approx(0.0)
    assert result["recall@2"] == pytest.approx(1.0)
    assert result["ndcg@2"] == pytest.approx(3.0 / (3.0 * math.log2(3)))
    assert result["mrr@2"] == pytest.approx(0.5)
