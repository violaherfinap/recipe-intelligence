from __future__ import annotations

import json
from pathlib import Path

import pytest

from recipe_qa.benchmark.query_split import (
    SLICES,
    allocate_train_counts,
    build_components,
    split_benchmark,
)
from recipe_qa.benchmark.schema import Qrel, Query
from recipe_qa.benchmark.validate import read_jsonl, write_jsonl


def make_query(query_id: str, slice_name: str) -> Query:
    return Query(
        query_id=query_id,
        text=f"Which recipe answers question number {query_id}?",
        slice=slice_name,
        as_of=1896 if slice_name == "temporal" else None,
        gold_claims=[] if slice_name == "no-evidence" else ["The recipe uses sugar."],
    )


def make_qrel(query_id: str, doc_id: str, relevance: int = 2) -> Qrel:
    return Qrel(
        query_id=query_id,
        passage_id=f"{doc_id}#ingredients#0",
        doc_id=doc_id,
        doc_version="a" * 40,
        relevance=relevance,
        annotator="C",
    )


def write_inputs(tmp_path: Path, queries: list[Query], qrels: list[Qrel]) -> tuple[Path, Path]:
    queries_path = tmp_path / "queries.jsonl"
    qrels_path = tmp_path / "qrels.jsonl"
    write_jsonl(queries_path, [row.model_dump() for row in queries])
    write_jsonl(qrels_path, [row.model_dump() for row in qrels])
    return queries_path, qrels_path


def test_allocate_train_counts_uses_largest_remainder() -> None:
    counts = {"easy": 35, "multi-hop": 25, "temporal": 30, "no-evidence": 25}
    assert allocate_train_counts(counts, 65) == {
        "easy": 20,
        "multi-hop": 14,
        "temporal": 17,
        "no-evidence": 14,
    }


def test_build_components_groups_queries_by_shared_gold_doc() -> None:
    queries = [make_query(f"q{index:03d}", "easy") for index in range(1, 6)]
    docs = {
        "q001": {"doc-a"},
        "q002": {"doc-a"},
        "q003": {"doc-b"},
        "q004": {"doc-c"},
        "q005": {"doc-c"},
    }
    components = build_components([query.query_id for query in queries], docs)
    assert components == [["q001", "q002"], ["q004", "q005"], ["q003"]]


def test_split_keeps_components_together_and_writes_files(tmp_path: Path) -> None:
    queries = [
        make_query(f"q{index:03d}", slice_name)
        for index, slice_name in enumerate(
            [
                "easy",
                "temporal",
                "multi-hop",
                "multi-hop",
                "easy",
                "temporal",
                "no-evidence",
                "no-evidence",
            ],
            start=1,
        )
    ]
    qrels = [
        make_qrel("q001", "doc-shared"),
        make_qrel("q002", "doc-shared"),
        make_qrel("q003", "doc-multi-a"),
        make_qrel("q004", "doc-multi-b"),
        make_qrel("q005", "doc-easy"),
        make_qrel("q006", "doc-temporal"),
        make_qrel("q002", "doc-noise", relevance=0),
    ]
    queries_path, qrels_path = write_inputs(tmp_path, queries, qrels)
    result = split_benchmark(
        queries_path=queries_path,
        qrels_path=qrels_path,
        out_path=tmp_path / "split.json",
        out_dir=tmp_path,
        train_total=4,
        train_counts={"easy": 1, "multi-hop": 1, "temporal": 1, "no-evidence": 1},
    )

    assert result.train == 4
    assert result.test == 4
    assert result.assignments["q001"] == result.assignments["q002"]
    assert result.gold_doc_overlap == []
    assert result.train_slices == {"easy": 1, "multi-hop": 1, "temporal": 1, "no-evidence": 1}
    assert len(read_jsonl(tmp_path / "queries_train.jsonl")) == 4
    assert len(read_jsonl(tmp_path / "queries_test.jsonl")) == 4
    payload = json.loads((tmp_path / "split.json").read_text(encoding="utf-8"))
    assert payload["assignments"] == result.assignments
    assert payload["gold_docs"]["overlap"] == []


def test_split_is_deterministic(tmp_path: Path) -> None:
    queries = [
        make_query(f"q{index:03d}", slice_name)
        for index, slice_name in enumerate(SLICES * 2, start=1)
    ]
    qrels = [make_qrel(query.query_id, f"doc-{query.query_id}") for query in queries]
    queries_path, qrels_path = write_inputs(tmp_path, queries, qrels)
    first = split_benchmark(
        queries_path=queries_path,
        qrels_path=qrels_path,
        out_path=tmp_path / "first.json",
        out_dir=tmp_path / "first",
        train_total=4,
    )
    second = split_benchmark(
        queries_path=queries_path,
        qrels_path=qrels_path,
        out_path=tmp_path / "second.json",
        out_dir=tmp_path / "second",
        train_total=4,
    )
    assert first.assignments == second.assignments
    assert first.train_sha256 == second.train_sha256
    assert first.test_sha256 == second.test_sha256


def test_split_rejects_infeasible_target(tmp_path: Path) -> None:
    queries = [make_query("q001", "easy"), make_query("q002", "easy")]
    qrels = [make_qrel("q001", "doc-a"), make_qrel("q002", "doc-b")]
    queries_path, qrels_path = write_inputs(tmp_path, queries, qrels)
    with pytest.raises(ValueError):
        split_benchmark(
            queries_path=queries_path,
            qrels_path=qrels_path,
            out_path=tmp_path / "split.json",
            out_dir=tmp_path,
            train_total=2,
            train_counts={"easy": 1, "multi-hop": 1, "temporal": 0, "no-evidence": 0},
        )


def test_committed_benchmark_split_is_reproducible(tmp_path: Path) -> None:
    queries_path = Path("benchmark/queries.jsonl")
    qrels_path = Path("benchmark/qrels.jsonl")
    split_path = Path("benchmark/query_split.json")
    if not split_path.exists():
        pytest.skip("committed query split not found")

    committed = json.loads(split_path.read_text(encoding="utf-8"))
    result = split_benchmark(
        queries_path=queries_path,
        qrels_path=qrels_path,
        out_path=tmp_path / "query_split.json",
        out_dir=tmp_path,
    )

    assert result.queries == 115
    assert result.train == 65
    assert result.test == 50
    assert result.train_slices == {
        "easy": 20,
        "multi-hop": 14,
        "temporal": 17,
        "no-evidence": 14,
    }
    assert result.test_slices == {
        "easy": 15,
        "multi-hop": 11,
        "temporal": 13,
        "no-evidence": 11,
    }
    assert result.gold_doc_overlap == []
    assert result.assignments == committed["assignments"]
    assert result.queries_sha256 == committed["source"]["queries_sha256"]
    assert result.qrels_sha256 == committed["source"]["qrels_sha256"]
