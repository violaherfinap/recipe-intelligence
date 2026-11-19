from __future__ import annotations

import json
from pathlib import Path

import pytest

from recipe_qa.benchmark.pool_v2 import build_pool_v2
from recipe_qa.benchmark.schema import GoldCandidate, PoolCandidate, PoolMeta, Query
from recipe_qa.benchmark.validate import load_passages_many, write_jsonl


def _passage(passage_id: str, doc_id: str, split: str, section: str = "directions") -> dict:
    return {
        "passage_id": passage_id,
        "doc_id": doc_id,
        "section": section,
        "idx": 0,
        "text": f"text for {passage_id}",
        "source_year": 1896,
        "source_title": "Book",
        "split": split,
    }


def _write_fixture(tmp_path: Path) -> dict[str, Path]:
    passages = tmp_path / "passages.jsonl"
    write_jsonl(
        passages,
        [
            _passage("p1", "d1", "test"),
            _passage("p2", "d2", "test"),
            _passage("p3", "d3", "train"),
            _passage("p4", "d4", "test", section="fixed"),
        ],
    )
    pool = tmp_path / "pool_v1.jsonl"
    write_jsonl(pool, [PoolCandidate(query_id="q001", passage_id="p1", doc_id="d1").model_dump()])
    meta = tmp_path / "pool_v1_meta.jsonl"
    write_jsonl(
        meta,
        [
            PoolMeta(
                query_id="q001", passage_id="p1", source="gold", rank=None, score=None
            ).model_dump()
        ],
    )
    queries = tmp_path / "queries.jsonl"
    write_jsonl(
        queries,
        [
            Query(
                query_id="q001",
                text="How long is the cake baked?",
                slice="easy",
                gold_claims=["The cake is baked for one hour."],
            ).model_dump()
        ],
    )
    gold = tmp_path / "gold.jsonl"
    write_jsonl(
        gold,
        [GoldCandidate(query_id="q001", passage_ids=["p1"], doc_ids=["d1"]).model_dump()],
    )
    test_docs = tmp_path / "test_docs.txt"
    test_docs.write_text("d1\nd2\nd4\n", encoding="utf-8")
    rankings = tmp_path / "rankings.json"
    rankings.write_text(
        json.dumps(
            {
                "chunking": "fixed",
                "rankings": {
                    "q001": [
                        {"passage_id": "p2", "doc_id": "d2", "score": 0.9},
                        {"passage_id": "p3", "doc_id": "d3", "score": 0.8},
                        {"passage_id": "p4", "doc_id": "d4", "score": 0.7},
                        {"passage_id": "missing", "doc_id": "d9", "score": 0.1},
                    ]
                },
            }
        ),
        encoding="utf-8",
    )
    return {
        "passages": passages,
        "pool": pool,
        "meta": meta,
        "queries": queries,
        "gold": gold,
        "test_docs": test_docs,
        "rankings": rankings,
    }


def test_build_pool_v2_unions_and_filters(tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path)
    out = tmp_path / "pool_v2.jsonl"
    meta_out = tmp_path / "pool_v2_meta.jsonl"
    result = build_pool_v2(
        queries_path=paths["queries"],
        pool_path=paths["pool"],
        meta_path=paths["meta"],
        rankings={"b2": paths["rankings"]},
        passages_paths=[paths["passages"]],
        test_docs_path=paths["test_docs"],
        gold_path=paths["gold"],
        out_path=out,
        meta_out_path=meta_out,
    )
    assert result.candidates == 3
    assert result.new_candidates == 2
    assert result.sources["retrieval"] == 2
    assert result.skipped["wrong_split"] == 1
    assert result.skipped["unknown_passage"] == 1
    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert {row["passage_id"] for row in rows} == {"p1", "p2", "p4"}
    assert all("source" not in row for row in rows)


def test_build_pool_v2_requires_gold_passage(tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path)
    gold = tmp_path / "bad_gold.jsonl"
    write_jsonl(
        gold,
        [GoldCandidate(query_id="q001", passage_ids=["p9"], doc_ids=["d9"]).model_dump()],
    )
    with pytest.raises(ValueError, match="gold passage missing"):
        build_pool_v2(
            queries_path=paths["queries"],
            pool_path=paths["pool"],
            meta_path=paths["meta"],
            rankings={},
            passages_paths=[paths["passages"]],
            test_docs_path=paths["test_docs"],
            gold_path=gold,
            out_path=tmp_path / "out.jsonl",
            meta_out_path=tmp_path / "out_meta.jsonl",
        )


def test_load_passages_many_merges_and_rejects_conflicts(tmp_path: Path) -> None:
    first = tmp_path / "first.jsonl"
    second = tmp_path / "second.jsonl"
    write_jsonl(first, [_passage("p1", "d1", "test")])
    write_jsonl(second, [_passage("p2", "d2", "test", section="fixed")])
    merged = load_passages_many([first, second])
    assert set(merged) == {"p1", "p2"}

    conflicting = tmp_path / "conflicting.jsonl"
    write_jsonl(conflicting, [_passage("p1", "d1", "train")])
    with pytest.raises(ValueError, match="conflicting rows"):
        load_passages_many([first, conflicting])
