from __future__ import annotations

import pytest

from recipe_qa.eval.metrics.coverage import (
    doc_recall_at_k,
    judged_rate_at_k,
    split_coverage_at_k,
    unjudged_test_rate_at_k,
)


def test_doc_recall_uses_unique_documents() -> None:
    ranked = ["d1", "d1", "d2", "d3"]
    relevant = {"d1", "d3", "d4"}
    assert doc_recall_at_k(ranked, relevant, k=2) == pytest.approx(1 / 3)
    assert doc_recall_at_k(ranked, relevant, k=4) == pytest.approx(2 / 3)
    assert doc_recall_at_k(ranked, set(), k=4) == 0.0


def test_judged_rate_counts_labelled_passages() -> None:
    assert judged_rate_at_k(["a", "b", "c"], {"a", "c"}, k=3) == pytest.approx(2 / 3)
    assert judged_rate_at_k(["a"], {"b"}, k=3) == 0.0
    assert judged_rate_at_k([], {"a"}, k=3) == 0.0


def test_split_coverage_counts_test_documents() -> None:
    assert split_coverage_at_k(["d1", "d2", "d3"], {"d1", "d3"}, k=2) == pytest.approx(0.5)
    assert split_coverage_at_k(["d1", "d2", "d3"], {"d1", "d3"}, k=3) == pytest.approx(2 / 3)
    assert split_coverage_at_k(["d1", "d2"], {"d3"}, k=2) == 0.0


def test_unjudged_test_rate_ignores_non_test_hits() -> None:
    ranked_passages = ["p1", "p2", "p3"]
    ranked_docs = ["d1", "d2", "d3"]
    judged = {"p1"}
    test_docs = {"d1", "d2"}
    assert unjudged_test_rate_at_k(
        ranked_passages, ranked_docs, judged, test_docs, k=3
    ) == pytest.approx(0.5)
    assert unjudged_test_rate_at_k(ranked_passages, ranked_docs, judged, {"none"}, k=3) == 0.0
