from __future__ import annotations

import pytest

from recipe_qa.benchmark.schema import Qrel, VerdictQrel
from recipe_qa.eval.agreement import (
    cohen_kappa,
    compare_relevance,
    compare_verdict,
    fleiss_kappa,
)

DOC_VERSION = "a" * 40


def _qrel(query_id: str, passage_id: str, relevance: int, annotator: str = "C") -> Qrel:
    return Qrel(
        query_id=query_id,
        passage_id=passage_id,
        doc_id=f"doc:{passage_id}",
        doc_version=DOC_VERSION,
        relevance=relevance,
        annotator=annotator,
    )


def _verdict(
    query_id: str,
    claim_id: str,
    verdict: str,
    annotator: str = "C",
) -> VerdictQrel:
    return VerdictQrel(
        query_id=query_id,
        claim_id=claim_id,
        verdict=verdict,
        annotator=annotator,
    )


def test_cohen_kappa_perfect_agreement() -> None:
    result = cohen_kappa([0, 0, 1, 2], [0, 0, 1, 2])
    assert result.n == 4
    assert result.observed == 1.0
    assert result.kappa == 1.0


def test_cohen_kappa_known_disagreement() -> None:
    result = cohen_kappa([0, 0, 1, 1], [0, 1, 0, 1])
    assert result.observed == pytest.approx(0.5)
    assert result.expected == pytest.approx(0.5)
    assert result.kappa == pytest.approx(0.0)


def test_cohen_kappa_undefined_for_single_class() -> None:
    result = cohen_kappa([0, 0], [0, 0])
    assert result.kappa is None
    assert not result.defined


def test_cohen_kappa_rejects_length_mismatch() -> None:
    with pytest.raises(ValueError, match="same length"):
        cohen_kappa([0, 1], [0])


def test_fleiss_kappa_known_disagreement() -> None:
    result = fleiss_kappa([[0, 0, 1], [0, 1, 1], [0, 1, 2]])
    assert result.n == 3
    assert result.observed == pytest.approx(2 / 9)
    assert result.expected == pytest.approx(11 / 27)
    assert result.kappa == pytest.approx(-5 / 16)
    assert result.labels == {"0": 4, "1": 4, "2": 1}


def test_fleiss_kappa_undefined_for_single_class() -> None:
    result = fleiss_kappa([[0, 0, 0], [0, 0, 0]])
    assert result.kappa is None
    assert not result.defined


def test_fleiss_kappa_rejects_mismatched_raters() -> None:
    with pytest.raises(ValueError, match="same number of raters"):
        fleiss_kappa([[0, 1], [0, 1, 2]])


def test_compare_relevance_reports_conflicts_and_missing() -> None:
    report = compare_relevance(
        [_qrel("q001", "p1", 2), _qrel("q001", "p2", 0)],
        [_qrel("q001", "p1", 1, "D"), _qrel("q001", "p3", 0, "D")],
    )
    assert report.n == 1
    assert report.complete is False
    assert report.only_c == [("q001", "p2")]
    assert report.only_d == [("q001", "p3")]
    assert len(report.disagreements) == 1
    assert report.disagreements[0].label_c == "2"
    assert report.disagreements[0].label_d == "1"


def test_compare_verdict_reports_conflict() -> None:
    report = compare_verdict(
        [_verdict("q001", "c1", "SUPPORTED"), _verdict("q001", "c2", "NOT_ENOUGH_EVIDENCE")],
        [_verdict("q001", "c1", "REFUTED", "D"), _verdict("q001", "c2", "NOT_ENOUGH_EVIDENCE", "D")],
    )
    assert report.n == 2
    assert report.complete is True
    assert len(report.disagreements) == 1
    assert report.disagreements[0].item_id == "c1"
