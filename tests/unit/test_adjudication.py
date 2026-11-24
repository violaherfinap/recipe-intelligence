from __future__ import annotations

from pathlib import Path

import pytest

from recipe_qa.benchmark.adjudication import (
    AdjudicationDecision,
    build_final_benchmark,
    build_final_qrels,
    build_final_verdicts,
    load_decisions,
    split_doc_ids,
    write_manifest,
    write_test_docs,
)
from recipe_qa.benchmark.schema import Qrel, Query, VerdictQrel
from recipe_qa.benchmark.validate import write_jsonl

DOC_VERSION = "a" * 40


def _qrel(query_id: str, passage_id: str, relevance: int, annotator: str) -> Qrel:
    return Qrel(
        query_id=query_id,
        passage_id=passage_id,
        doc_id=f"doc:{passage_id}",
        doc_version=DOC_VERSION,
        relevance=relevance,
        annotator=annotator,
    )


def _verdict(query_id: str, claim_id: str, verdict: str, annotator: str) -> VerdictQrel:
    return VerdictQrel(
        query_id=query_id,
        claim_id=claim_id,
        verdict=verdict,
        annotator=annotator,
    )


def _decision(
    kind: str,
    query_id: str,
    item_id: str,
    label_c: str,
    label_d: str,
    final: str,
    label_a: str | None = None,
) -> dict:
    row = {
        "kind": kind,
        "query_id": query_id,
        "item_id": item_id,
        "label_c": label_c,
        "label_d": label_d,
        "final": final,
        "notes": "checked passage",
    }
    if label_a is not None:
        row["label_a"] = label_a
    return row


def _query(query_id: str, slice_name: str = "easy") -> Query:
    return Query(
        query_id=query_id,
        text=f"What is the answer for {query_id} in 1871?",
        slice=slice_name,
        as_of=1871,
        gold_claims=[] if slice_name == "no-evidence" else ["The answer is forty minutes."],
    )


def _pool() -> list[dict]:
    return [
        {"query_id": "q001", "passage_id": "p1", "doc_id": "doc:p1"},
        {"query_id": "q002", "passage_id": "p2", "doc_id": "doc:p2"},
    ]


def _passages() -> dict[str, dict]:
    return {
        "p1": {"passage_id": "p1", "doc_id": "doc:p1", "split": "test"},
        "p2": {"passage_id": "p2", "doc_id": "doc:p2", "split": "test"},
        "p3": {"passage_id": "p3", "doc_id": "doc:p3", "split": "train"},
    }


def test_build_final_qrels_applies_decision() -> None:
    decisions = {
        ("relevance", "q001", "p1"): AdjudicationDecision(
            kind="relevance",
            query_id="q001",
            item_id="p1",
            label_c="0",
            label_d="2",
            final="2",
            notes="D is right",
        )
    }
    rows, report = build_final_qrels(
        rows_c=[_qrel("q001", "p1", 0, "C")],
        rows_d=[_qrel("q001", "p1", 2, "D")],
        pool_rows=[{"query_id": "q001", "passage_id": "p1", "doc_id": "doc:p1"}],
        doc_version=DOC_VERSION,
        decisions=decisions,
    )
    assert report.ok
    assert len(rows) == 1
    assert rows[0].relevance == 2
    assert rows[0].annotator == "D"
    assert "adjudicated" in rows[0].notes


def test_build_final_qrels_rejects_unresolved_conflict() -> None:
    rows, report = build_final_qrels(
        rows_c=[_qrel("q001", "p1", 0, "C")],
        rows_d=[_qrel("q001", "p1", 2, "D")],
        pool_rows=[{"query_id": "q001", "passage_id": "p1", "doc_id": "doc:p1"}],
        doc_version=DOC_VERSION,
    )
    assert rows == []
    assert not report.ok
    assert any("unresolved conflict" in error for error in report.errors)


def test_build_final_qrels_rejects_stale_decision() -> None:
    decisions = {
        ("relevance", "q001", "p1"): AdjudicationDecision(
            kind="relevance",
            query_id="q001",
            item_id="p1",
            label_c="0",
            label_d="1",
            final="1",
        )
    }
    rows, report = build_final_qrels(
        rows_c=[_qrel("q001", "p1", 0, "C")],
        rows_d=[_qrel("q001", "p1", 2, "D")],
        pool_rows=[{"query_id": "q001", "passage_id": "p1", "doc_id": "doc:p1"}],
        doc_version=DOC_VERSION,
        decisions=decisions,
    )
    assert rows == []
    assert any("stale decision" in error for error in report.errors)


def test_build_final_qrels_three_way_majority() -> None:
    rows, report = build_final_qrels(
        rows_c=[_qrel("q001", "p1", 0, "C")],
        rows_d=[_qrel("q001", "p1", 2, "D")],
        rows_a=[_qrel("q001", "p1", 0, "A")],
        pool_rows=[{"query_id": "q001", "passage_id": "p1", "doc_id": "doc:p1"}],
        doc_version=DOC_VERSION,
        annotator="consensus",
        required_a_keys={("q001", "p1")},
    )
    assert report.ok
    assert report.majority == 1
    assert report.ties == 0
    assert len(rows) == 1
    assert rows[0].relevance == 0
    assert rows[0].annotator == "consensus"
    assert "consensus A=0; C=0; D=2; majority=0" in rows[0].notes


def test_build_final_qrels_three_way_tie_needs_decision() -> None:
    rows, report = build_final_qrels(
        rows_c=[_qrel("q001", "p1", 0, "C")],
        rows_d=[_qrel("q001", "p1", 2, "D")],
        rows_a=[_qrel("q001", "p1", 1, "A")],
        pool_rows=[{"query_id": "q001", "passage_id": "p1", "doc_id": "doc:p1"}],
        doc_version=DOC_VERSION,
        required_a_keys={("q001", "p1")},
    )
    assert rows == []
    assert report.ties == 1
    assert any("unresolved tie" in error for error in report.errors)


def test_build_final_qrels_three_way_tie_decision() -> None:
    decisions = {
        ("relevance", "q001", "p1"): AdjudicationDecision(
            kind="relevance",
            query_id="q001",
            item_id="p1",
            label_a="1",
            label_c="0",
            label_d="2",
            final="1",
            notes="A is right",
        )
    }
    rows, report = build_final_qrels(
        rows_c=[_qrel("q001", "p1", 0, "C")],
        rows_d=[_qrel("q001", "p1", 2, "D")],
        rows_a=[_qrel("q001", "p1", 1, "A")],
        pool_rows=[{"query_id": "q001", "passage_id": "p1", "doc_id": "doc:p1"}],
        doc_version=DOC_VERSION,
        decisions=decisions,
        required_a_keys={("q001", "p1")},
    )
    assert report.ok
    assert report.resolved == 1
    assert rows[0].relevance == 1
    assert "adjudicated: A=1; C=0; D=2; final=1" in rows[0].notes


def test_build_final_qrels_requires_a_for_new_keys() -> None:
    rows, report = build_final_qrels(
        rows_c=[_qrel("q001", "p1", 0, "C")],
        rows_d=[_qrel("q001", "p1", 0, "D")],
        pool_rows=[{"query_id": "q001", "passage_id": "p1", "doc_id": "doc:p1"}],
        doc_version=DOC_VERSION,
        required_a_keys={("q001", "p1")},
    )
    assert rows == []
    assert report.missing_a == 1
    assert any("missing required A label" in error for error in report.errors)


def test_build_final_qrels_seed_falls_back_without_a() -> None:
    rows, report = build_final_qrels(
        rows_c=[_qrel("q001", "p1", 2, "C")],
        rows_d=[_qrel("q001", "p1", 2, "D")],
        pool_rows=[{"query_id": "q001", "passage_id": "p1", "doc_id": "doc:p1"}],
        doc_version=DOC_VERSION,
    )
    assert report.ok
    assert len(rows) == 1
    assert rows[0].relevance == 2


def test_build_final_qrels_rejects_stale_three_way_decision() -> None:
    decisions = {
        ("relevance", "q001", "p1"): AdjudicationDecision(
            kind="relevance",
            query_id="q001",
            item_id="p1",
            label_a="0",
            label_c="0",
            label_d="2",
            final="0",
        )
    }
    rows, report = build_final_qrels(
        rows_c=[_qrel("q001", "p1", 0, "C")],
        rows_d=[_qrel("q001", "p1", 2, "D")],
        rows_a=[_qrel("q001", "p1", 1, "A")],
        pool_rows=[{"query_id": "q001", "passage_id": "p1", "doc_id": "doc:p1"}],
        doc_version=DOC_VERSION,
        decisions=decisions,
        required_a_keys={("q001", "p1")},
    )
    assert rows == []
    assert any("stale decision" in error for error in report.errors)


def test_build_final_verdicts_applies_decision() -> None:
    decisions = {
        ("verdict", "q001", "c1"): AdjudicationDecision(
            kind="verdict",
            query_id="q001",
            item_id="c1",
            label_c="SUPPORTED",
            label_d="REFUTED",
            final="SUPPORTED",
            notes="support is explicit",
        )
    }
    rows, report = build_final_verdicts(
        rows_c=[_verdict("q001", "c1", "SUPPORTED", "C")],
        rows_d=[_verdict("q001", "c1", "REFUTED", "D")],
        queries=[_query("q001")],
        decisions=decisions,
    )
    assert report.ok
    assert len(rows) == 1
    assert rows[0].verdict == "SUPPORTED"
    assert rows[0].annotator == "D"
    assert "adjudicated" in rows[0].notes


def test_build_final_benchmark_validates_full_output() -> None:
    report = build_final_benchmark(
        rows_qrels_c=[_qrel("q001", "p1", 2, "C"), _qrel("q002", "p2", 0, "C")],
        rows_qrels_d=[_qrel("q001", "p1", 2, "D"), _qrel("q002", "p2", 0, "D")],
        rows_verdict_c=[_verdict("q001", "c1", "SUPPORTED", "C")],
        rows_verdict_d=[_verdict("q001", "c1", "SUPPORTED", "D")],
        pool_rows=_pool(),
        queries=[_query("q001"), _query("q002", "no-evidence")],
        passages=_passages(),
        doc_version=DOC_VERSION,
    )
    assert report.ok
    assert len(report.qrels) == 2
    assert len(report.verdicts) == 1
    assert report.relevance_labels == {0: 1, 2: 1}


def test_load_decisions_rejects_invalid_final(tmp_path: Path) -> None:
    path = tmp_path / "decisions.jsonl"
    write_jsonl(path, [_decision("relevance", "q001", "p1", "0", "1", "3")])
    with pytest.raises(ValueError, match="invalid final"):
        load_decisions(path)


def test_write_manifest_uses_sha256_and_relative_paths(tmp_path: Path) -> None:
    queries = tmp_path / "queries.jsonl"
    queries.write_text("{}\n", encoding="utf-8")
    manifest = tmp_path / "manifest.sha256"
    lines = write_manifest(manifest, [queries], base=tmp_path)
    assert len(lines) == 1
    digest, relative = lines[0].split("  ", maxsplit=1)
    assert len(digest) == 64
    assert relative == "queries.jsonl"


def test_write_test_docs_and_ids(tmp_path: Path) -> None:
    assert split_doc_ids(_passages()) == ["doc:p1", "doc:p2"]
    path = tmp_path / "test_docs.txt"
    write_test_docs(path, ["doc:p1", "doc:p2"])
    assert path.read_text(encoding="utf-8") == "doc:p1\ndoc:p2\n"
