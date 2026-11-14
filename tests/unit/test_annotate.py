"""Tests for blind annotation helpers."""

from __future__ import annotations

from pathlib import Path

from recipe_qa.benchmark.annotation import (
    JudgmentKey,
    append_qrel,
    evidence_passages,
    load_judged,
    load_pool,
    order_candidates,
    relevance_progress,
)
from recipe_qa.benchmark.schema import PoolCandidate, Qrel, Query
from recipe_qa.benchmark.validate import write_jsonl


def _write_pool(path: Path, query_id: str = "q001") -> list[PoolCandidate]:
    candidates = [
        PoolCandidate(query_id=query_id, passage_id=f"p{index}", doc_id=f"d{index}")
        for index in range(12)
    ]
    write_jsonl(path, [candidate.model_dump() for candidate in candidates])
    return candidates


def test_load_pool_preserves_grouping(tmp_path: Path) -> None:
    pool_path = tmp_path / "pool.jsonl"
    _write_pool(pool_path)
    pool = load_pool(pool_path)
    assert len(pool["q001"]) == 12


def test_order_candidates_is_deterministic_and_annotator_specific(tmp_path: Path) -> None:
    pool_path = tmp_path / "pool.jsonl"
    candidates = _write_pool(pool_path)
    first = [item.passage_id for item in order_candidates(candidates, "C")]
    second = [item.passage_id for item in order_candidates(candidates, "C")]
    other = [item.passage_id for item in order_candidates(candidates, "D")]
    assert first == second
    assert first != other
    assert sorted(first) == sorted(other)


def test_append_qrel_and_resume(tmp_path: Path) -> None:
    out = tmp_path / "qrels_c.jsonl"
    qrel = Qrel(
        query_id="q001",
        passage_id="p1",
        doc_id="d1",
        doc_version="a" * 40,
        relevance=2,
        annotator="C",
    )
    append_qrel(out, qrel)
    append_qrel(out, qrel.model_copy(update={"passage_id": "p2"}))
    judged = load_judged(out)
    assert judged == {
        JudgmentKey("q001", "p1"),
        JudgmentKey("q001", "p2"),
    }


def test_relevance_progress(tmp_path: Path) -> None:
    queries = [
        Query(
            query_id="q001",
            text="How long is tomato soup simmered in the 1896 book?",
            slice="easy",
            as_of=1896,
            gold_claims=["Tomato soup is simmered for twenty minutes."],
        )
    ]
    pool = {
        "q001": [
            PoolCandidate(query_id="q001", passage_id="p1", doc_id="d1"),
            PoolCandidate(query_id="q001", passage_id="p2", doc_id="d2"),
        ]
    }
    progress = relevance_progress(queries, pool, {JudgmentKey("q001", "p1")})
    assert progress["q001"] == (1, 2)


def test_evidence_passages_filters_by_relevance(tmp_path: Path) -> None:
    out = tmp_path / "qrels_c.jsonl"
    for passage_id, relevance in (("p1", 2), ("p2", 1), ("p3", 0)):
        append_qrel(
            out,
            Qrel(
                query_id="q001",
                passage_id=passage_id,
                doc_id="d",
                doc_version="a" * 40,
                relevance=relevance,
                annotator="C",
            ),
        )
    assert evidence_passages("q001", out) == ["p1"]
