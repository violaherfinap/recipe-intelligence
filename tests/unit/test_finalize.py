from __future__ import annotations

from recipe_qa.benchmark.finalize import merge_qrel_rows, validate_final_qrels
from recipe_qa.benchmark.schema import Query

DOC_VERSION = "a" * 40


def _qrel(query_id: str, passage_id: str, relevance: int = 0) -> dict:
    return {
        "query_id": query_id,
        "passage_id": passage_id,
        "doc_id": f"doc:{passage_id}",
        "doc_version": DOC_VERSION,
        "relevance": relevance,
        "annotator": "C",
        "notes": "",
    }


def _query(query_id: str, slice_name: str) -> Query:
    return Query(
        query_id=query_id,
        text=f"What is the answer for {query_id}?",
        slice=slice_name,
        as_of=1871,
        gold_claims=[] if slice_name == "no-evidence" else ["An answer."],
    )


def _passages() -> dict[str, dict]:
    return {
        "p1": {"passage_id": "p1", "doc_id": "doc:p1", "split": "test"},
        "p2": {"passage_id": "p2", "doc_id": "doc:p2", "split": "test"},
    }


def _pool() -> list[dict]:
    return [
        {"query_id": "q001", "passage_id": "p1", "doc_id": "doc:p1"},
        {"query_id": "q002", "passage_id": "p2", "doc_id": "doc:p2"},
    ]


def _validate(manual: list[dict], reviewed: list[dict], draft: list[dict]):
    return validate_final_qrels(
        manual_rows=manual,
        reviewed_rows=reviewed,
        draft_rows=draft,
        pool_rows=_pool(),
        queries=[_query("q001", "easy"), _query("q002", "no-evidence")],
        passages=_passages(),
        doc_version=DOC_VERSION,
    )


def test_merge_qrel_rows_sorts_by_query_and_passage() -> None:
    merged = merge_qrel_rows([_qrel("q002", "p2")], [_qrel("q001", "p1")])
    assert [(row["query_id"], row["passage_id"]) for row in merged] == [
        ("q001", "p1"),
        ("q002", "p2"),
    ]


def test_validate_final_qrels_accepts_complete_union() -> None:
    report = _validate(
        manual=[_qrel("q001", "p1", 2)],
        reviewed=[_qrel("q002", "p2", 0)],
        draft=[_qrel("q002", "p2", 0)],
    )
    assert report.ok
    assert report.merged == 2
    assert report.labels == {0: 1, 2: 1}


def test_validate_final_qrels_rejects_missing_reviewed_key() -> None:
    report = _validate(
        manual=[_qrel("q001", "p1", 2)],
        reviewed=[],
        draft=[_qrel("q002", "p2", 0)],
    )
    assert not report.ok
    assert any("missing from reviewed" in error for error in report.errors)


def test_validate_final_qrels_rejects_nonzero_no_evidence() -> None:
    report = _validate(
        manual=[_qrel("q001", "p1", 2)],
        reviewed=[_qrel("q002", "p2", 1)],
        draft=[_qrel("q002", "p2", 1)],
    )
    assert not report.ok
    assert any("no-evidence query has non-zero" in error for error in report.errors)


def test_validate_final_qrels_rejects_answerable_without_two() -> None:
    report = _validate(
        manual=[_qrel("q001", "p1", 1)],
        reviewed=[_qrel("q002", "p2", 0)],
        draft=[_qrel("q002", "p2", 0)],
    )
    assert not report.ok
    assert any("no relevance-2 passage" in error for error in report.errors)
