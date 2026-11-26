from __future__ import annotations

from recipe_qa.benchmark.schema import Qrel, Query
from recipe_qa.eval.nli_calibration import (
    build_probe,
    calibrate,
    select_threshold,
    sweep_thresholds,
    threshold_grid,
)


def _query(query_id: str, claims: list[str]) -> Query:
    return Query(
        query_id=query_id,
        text="How did the sweetener change between 1851 and 1871?",
        slice="temporal",
        as_of=1871,
        gold_claims=claims,
    )


def _qrel(query_id: str, passage_id: str, doc_id: str, relevance: int = 2) -> Qrel:
    return Qrel(
        query_id=query_id,
        passage_id=passage_id,
        doc_id=doc_id,
        doc_version="a" * 40,
        relevance=relevance,
        annotator="C",
    )


def _passage(
    doc_id: str, passage_id: str, text: str, year: int = 1871, split: str = "test"
) -> dict:
    return {
        "passage_id": passage_id,
        "doc_id": doc_id,
        "text": text,
        "source_year": year,
        "split": split,
    }


def _fixtures():
    queries = [_query("q001", ["The 1851 recipe uses white sugar."])]
    qrels = [
        _qrel("q001", "d1#ingredients#0", "d1"),
        _qrel("q001", "d2#ingredients#0", "d2"),
    ]
    passages = {
        "d1#ingredients#0": _passage(
            "d1", "d1#ingredients#0", "white sugar and flour", 1851, split="test"
        ),
        "d2#ingredients#0": _passage(
            "d2", "d2#ingredients#0", "powdered sugar and eggs", 1871, split="test"
        ),
        "d3#ingredients#0": _passage(
            "d3",
            "d3#ingredients#0",
            "white sugar and powdered sugar for the cake",
            1887,
            split="train",
        ),
        "d4#ingredients#0": _passage(
            "d4", "d4#ingredients#0", "roast the duck with salt", 1896, split="train"
        ),
    }
    return queries, qrels, passages


def test_build_probe_pairs_claims_with_gold_and_synthetic_negatives() -> None:
    queries, qrels, passages = _fixtures()
    pairs = build_probe(queries, qrels, passages, seed=42)
    positives = [pair for pair in pairs if pair.label == 1]
    negatives = [pair for pair in pairs if pair.label == 0]
    assert len(positives) == 2
    assert {pair.passage_id for pair in positives} == {
        "d1#ingredients#0",
        "d2#ingredients#0",
    }
    assert all(pair.kind == "gold" for pair in positives)
    assert len(negatives) == 1
    assert negatives[0].kind == "synthetic_negative"
    assert negatives[0].passage_id not in {
        "d1#ingredients#0",
        "d2#ingredients#0",
    }


def test_build_probe_negatives_use_train_split_and_skip_all_gold_docs() -> None:
    queries = [
        _query("q001", ["The 1851 recipe uses white sugar."]),
        _query("q002", ["The 1871 recipe uses powdered sugar."]),
    ]
    qrels = [
        _qrel("q001", "d1#ingredients#0", "d1"),
        _qrel("q002", "d2#ingredients#0", "d2"),
    ]
    passages = {
        "d1#ingredients#0": _passage(
            "d1", "d1#ingredients#0", "white sugar and flour", 1851, split="test"
        ),
        "d2#ingredients#0": _passage(
            "d2", "d2#ingredients#0", "powdered sugar and eggs", 1871, split="test"
        ),
        "d3#ingredients#0": _passage(
            "d3", "d3#ingredients#0", "white sugar for the cake", 1887, split="train"
        ),
    }
    pairs = build_probe(queries, qrels, passages, seed=42)
    negatives = [pair for pair in pairs if pair.label == 0]
    assert negatives
    assert all(passages[pair.passage_id]["split"] == "train" for pair in negatives)
    assert all(
        passages[pair.passage_id]["doc_id"] not in {"d1", "d2"} for pair in negatives
    )


def test_build_probe_is_deterministic() -> None:
    queries, qrels, passages = _fixtures()
    first = [pair.to_dict() for pair in build_probe(queries, qrels, passages, seed=42)]
    second = [pair.to_dict() for pair in build_probe(queries, qrels, passages, seed=42)]
    assert first == second


def test_build_probe_skips_no_evidence_queries() -> None:
    queries = [
        Query(
            query_id="q002",
            text="Does the 1796 book mention a gas oven?",
            slice="no-evidence",
            as_of=1796,
            gold_claims=[],
        )
    ]
    assert build_probe(queries, [], {}) == []


def test_build_probe_carries_slice_metadata() -> None:
    queries, qrels, passages = _fixtures()
    pairs = build_probe(queries, qrels, passages)
    assert {pair.slice for pair in pairs} == {"temporal"}


def test_sweep_computes_precision_recall_and_balanced_accuracy() -> None:
    scored = [(0.9, 1), (0.8, 1), (0.4, 0), (0.2, 0)]
    sweep = sweep_thresholds(scored, [0.5])
    row = sweep[0]
    assert (row["tp"], row["fp"], row["fn"], row["tn"]) == (2, 0, 0, 2)
    assert row["precision"] == 1.0
    assert row["recall"] == 1.0
    assert row["balanced_accuracy"] == 1.0


def test_select_threshold_prefers_balanced_accuracy_then_f1() -> None:
    sweep = sweep_thresholds([(0.9, 1), (0.6, 0), (0.3, 1)], [0.5, 0.7])
    best = select_threshold(sweep)
    assert best["threshold"] == 0.7
    assert best["balanced_accuracy"] == 0.75


def test_calibrate_reports_best_point_and_caveat() -> None:
    report = calibrate([(0.9, 1), (0.8, 1), (0.4, 0), (0.2, 0)], threshold_grid())
    assert report["pairs"] == 4
    assert report["positives"] == 2
    assert report["negatives"] == 2
    assert report["balanced_accuracy"] == 1.0
    assert report["precision"] == 1.0
    assert "synthetic" in report["caveat"]
    assert len(report["sweep"]) == len(threshold_grid())


def test_threshold_grid_is_inclusive() -> None:
    grid = threshold_grid(0.30, 0.90, 0.05)
    assert grid[0] == 0.3
    assert grid[-1] == 0.9
    assert len(grid) == 13
