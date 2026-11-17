from __future__ import annotations

from pathlib import Path

import pytest

from recipe_qa.benchmark.answer_sheet import (
    RELEVANCE_FIELDS,
    VERDICT_FIELDS,
    apply_relevance_labels,
    build_relevance_rows,
    build_verdict_rows,
    import_relevance_sheet,
    import_verdict_sheet,
    read_sheet,
    write_sheet,
)
from recipe_qa.benchmark.schema import PoolCandidate, Qrel, Query

DOC_VERSION = "a" * 40


def _query(query_id: str, slice_name: str = "easy", claims: list[str] | None = None) -> Query:
    return Query(
        query_id=query_id,
        text=f"What is the answer for {query_id} in 1871?",
        slice=slice_name,
        as_of=1871,
        gold_claims=[] if slice_name == "no-evidence" else claims or ["The answer is forty minutes."],
    )


def _pool() -> dict[str, list[PoolCandidate]]:
    return {
        "q001": [
            PoolCandidate(query_id="q001", passage_id="p1", doc_id="doc:p1"),
            PoolCandidate(query_id="q001", passage_id="p2", doc_id="doc:p2"),
        ],
        "q002": [
            PoolCandidate(query_id="q002", passage_id="p3", doc_id="doc:p3"),
        ],
    }


def _passages() -> dict[str, dict]:
    return {
        "p1": {
            "passage_id": "p1",
            "doc_id": "doc:p1",
            "split": "test",
            "source_title": "Book",
            "source_year": 1871,
            "section": "directions",
            "text": "Bake for forty minutes.",
        },
        "p2": {
            "passage_id": "p2",
            "doc_id": "doc:p2",
            "split": "test",
            "source_title": "Book",
            "source_year": 1871,
            "section": "ingredients",
            "text": "Mix butter and sugar.",
        },
        "p3": {
            "passage_id": "p3",
            "doc_id": "doc:p3",
            "split": "test",
            "source_title": "Book",
            "source_year": 1871,
            "section": "directions",
            "text": "Roast the beef.",
        },
    }


def test_build_relevance_rows_has_all_candidates_and_blank_labels() -> None:
    rows = build_relevance_rows(
        [_query("q001"), _query("q002", "no-evidence")],
        _pool(),
        _passages(),
    )
    assert len(rows) == 3
    assert {row["query_id"] for row in rows} == {"q001", "q002"}
    assert all(row["relevance"] == "" for row in rows)
    assert all(row["notes"] == "" for row in rows)
    assert "gold_claims" not in RELEVANCE_FIELDS
    assert not {"source", "rank", "score"} & set(RELEVANCE_FIELDS)


def test_build_verdict_rows_uses_only_level_two_evidence() -> None:
    queries = [_query("q001", claims=["Claim one.", "Claim two."])]
    qrels = [
        Qrel(
            query_id="q001",
            passage_id="p1",
            doc_id="doc:p1",
            doc_version=DOC_VERSION,
            relevance=2,
            annotator="D",
        ),
        Qrel(
            query_id="q001",
            passage_id="p2",
            doc_id="doc:p2",
            doc_version=DOC_VERSION,
            relevance=0,
            annotator="D",
        ),
    ]
    rows = build_verdict_rows(queries, qrels, _passages())
    assert len(rows) == 2
    assert rows[0]["claim_id"] == "c1"
    assert "Bake for forty minutes." in rows[0]["evidence"]
    assert "Mix butter and sugar." not in rows[0]["evidence"]
    assert all(row["verdict"] == "" for row in rows)
    assert "gold_claims" not in VERDICT_FIELDS


def test_apply_relevance_labels_prefills_existing_judgments() -> None:
    rows = [
        {"query_id": "q001", "passage_id": "p1", "relevance": "", "notes": ""},
        {"query_id": "q001", "passage_id": "p2", "relevance": "", "notes": ""},
    ]
    qrels = [
        Qrel(
            query_id="q001",
            passage_id="p1",
            doc_id="doc:p1",
            doc_version=DOC_VERSION,
            relevance=2,
            annotator="D",
            notes="already judged",
        )
    ]
    assert apply_relevance_labels(rows, qrels) == 1
    assert rows[0]["relevance"] == "2"
    assert rows[0]["notes"] == "already judged"
    assert rows[1]["relevance"] == ""


def test_write_and_read_sheet_round_trip_with_excel_bom(tmp_path: Path) -> None:
    path = tmp_path / "sheet.csv"
    rows = [{"query_id": "q001", "passage_id": "p1", "relevance": "2", "notes": "ok"}]
    write_sheet(path, rows, ["query_id", "passage_id", "relevance", "notes"])
    assert path.read_bytes().startswith(b"\xef\xbb\xbf")
    loaded = read_sheet(path, ["query_id", "passage_id", "relevance"])
    assert loaded[0]["relevance"] == "2"
    assert loaded[0]["_line"] == 2


def _write_relevance_sheet(path: Path, labels: dict[str, str]) -> None:
    rows = [
        {"query_id": query_id, "passage_id": passage_id, "relevance": label, "notes": ""}
        for (query_id, passage_id), label in labels.items()
    ]
    write_sheet(path, rows, ["query_id", "passage_id", "relevance", "notes"])


def test_import_relevance_sheet_valid(tmp_path: Path) -> None:
    path = tmp_path / "relevance.csv"
    _write_relevance_sheet(
        path,
        {("q001", "p1"): "2", ("q001", "p2"): "0", ("q002", "p3"): "1"},
    )
    rows, report = import_relevance_sheet(path, _pool(), _passages(), DOC_VERSION)
    assert report.ok
    assert len(rows) == 3
    assert report.labels == {"0": 1, "1": 1, "2": 1}
    assert all(row.annotator == "D" for row in rows)


def test_import_relevance_sheet_rejects_invalid_label(tmp_path: Path) -> None:
    path = tmp_path / "relevance.csv"
    _write_relevance_sheet(path, {("q001", "p1"): "3"})
    _rows, report = import_relevance_sheet(path, _pool(), _passages(), DOC_VERSION)
    assert not report.ok
    assert any("relevance must be 0, 1, or 2" in error for error in report.errors)


def test_import_relevance_sheet_rejects_missing_and_duplicate_keys(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.csv"
    _write_relevance_sheet(missing_path, {("q001", "p1"): "2"})
    _rows, report = import_relevance_sheet(missing_path, _pool(), _passages(), DOC_VERSION)
    assert any("missing pool keys" in error for error in report.errors)

    duplicate_path = tmp_path / "duplicate.csv"
    _write_relevance_sheet(
        duplicate_path,
        {("q001", "p1"): "2", ("q001", "p2"): "0", ("q002", "p3"): "0"},
    )
    content = duplicate_path.read_text(encoding="utf-8-sig").splitlines()
    duplicate_path.write_text(
        "\n".join([content[0], *content[1:], content[1]]) + "\n",
        encoding="utf-8-sig",
    )
    _rows, report = import_relevance_sheet(duplicate_path, _pool(), _passages(), DOC_VERSION)
    assert any("duplicate key" in error for error in report.errors)


def test_import_relevance_sheet_rejects_unknown_key(tmp_path: Path) -> None:
    path = tmp_path / "relevance.csv"
    _write_relevance_sheet(path, {("q001", "p9"): "2"})
    _rows, report = import_relevance_sheet(path, _pool(), _passages(), DOC_VERSION)
    assert any("is not in the pool" in error for error in report.errors)


def _write_verdict_sheet(
    path: Path,
    labels: dict[tuple[str, str], str],
    claims: dict[tuple[str, str], str],
) -> None:
    rows = [
        {
            "query_id": query_id,
            "claim_id": claim_id,
            "claim": claims[(query_id, claim_id)],
            "verdict": label,
            "notes": "",
        }
        for (query_id, claim_id), label in labels.items()
    ]
    write_sheet(
        path,
        rows,
        ["query_id", "claim_id", "claim", "verdict", "notes"],
    )


def test_import_verdict_sheet_valid(tmp_path: Path) -> None:
    path = tmp_path / "verdict.csv"
    claims = {
        ("q001", "c1"): "The answer is forty minutes.",
        ("q001", "c2"): "The answer is one hour.",
    }
    _write_verdict_sheet(
        path,
        {("q001", "c1"): "SUPPORTED", ("q001", "c2"): "NOT_ENOUGH_EVIDENCE"},
        claims,
    )
    rows, report = import_verdict_sheet(
        path,
        [_query("q001", claims=list(claims.values()))],
    )
    assert report.ok
    assert len(rows) == 2
    assert report.labels == {"NOT_ENOUGH_EVIDENCE": 1, "SUPPORTED": 1}


def test_import_verdict_sheet_rejects_invalid_label(tmp_path: Path) -> None:
    path = tmp_path / "verdict.csv"
    _write_verdict_sheet(
        path,
        {("q001", "c1"): "MAYBE"},
        {("q001", "c1"): "The answer is forty minutes."},
    )
    _rows, report = import_verdict_sheet(path, [_query("q001")])
    assert not report.ok
    assert any("verdict must be" in error for error in report.errors)


def test_build_relevance_rows_rejects_unknown_passage() -> None:
    pool = {"q001": [PoolCandidate(query_id="q001", passage_id="missing", doc_id="doc:x")]}
    with pytest.raises(ValueError, match="unknown passage"):
        build_relevance_rows([_query("q001")], pool, {})
