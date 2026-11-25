from __future__ import annotations

from recipe_qa.retrieval.fusion import reciprocal_rank_fusion


def test_rrf_prefers_document_in_both_lists():
    fused = reciprocal_rank_fusion([["a", "b", "c"], ["b", "d"]], k=60)
    assert fused[0][0] == "b"
    assert dict(fused)["b"] > dict(fused)["a"]


def test_rrf_handles_empty_lists():
    assert reciprocal_rank_fusion([[], []], k=60) == []
    assert reciprocal_rank_fusion([["a"], []], k=60)[0][0] == "a"


def test_rrf_rejects_bad_k():
    try:
        reciprocal_rank_fusion([["a"]], k=0)
    except ValueError as exc:
        assert "k" in str(exc)
    else:
        raise AssertionError("expected ValueError")
