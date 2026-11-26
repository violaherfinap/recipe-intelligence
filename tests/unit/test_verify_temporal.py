from __future__ import annotations

from recipe_qa.generation.schema import AnswerPayload, Claim, EvidenceItem
from recipe_qa.retrieval.types import Hit
from recipe_qa.verify.temporal import check_temporal, claim_years


def _hit(passage_id: str = "p1", year: int = 1871) -> Hit:
    return Hit(
        passage_id=passage_id,
        doc_id=f"doc:{passage_id}",
        score=1.0,
        passage={
            "passage_id": passage_id,
            "doc_id": f"doc:{passage_id}",
            "text": "Bake the apples with sugar for one hour.",
            "source_year": year,
        },
        rank=1,
    )


def _payload(
    claim: str,
    as_of: int | None = None,
    evidence: list[EvidenceItem] | None = None,
) -> AnswerPayload:
    return AnswerPayload(
        query_id="q001",
        answer=claim,
        claims=[
            Claim(
                claim_id="c1",
                claim=claim,
                verdict="SUPPORTED",
                as_of=as_of,
                evidence_for=evidence or [],
            )
        ],
    )


def _evidence(passage_id: str = "p1", year: int | None = 1871) -> EvidenceItem:
    return EvidenceItem(passage_id=passage_id, doc_id=f"doc:{passage_id}", source_year=year)


def test_claim_years_extracts_historical_years() -> None:
    assert claim_years("Baked in 1851 and 1871 with 20 eggs.") == [1851, 1871]


def test_claim_year_after_as_of_is_a_violation() -> None:
    report = check_temporal(_payload("The 1871 book bakes it for an hour.", as_of=1851), [_hit()])
    assert not report.ok
    assert report.after_as_of == 1
    assert "as_of 1851" in report.violations[0]


def test_evidence_year_after_as_of_is_a_violation() -> None:
    payload = _payload("Bake it for one hour.", as_of=1851, evidence=[_evidence(year=1871)])
    report = check_temporal(payload, [_hit(year=1871)], as_of=1851)
    assert not report.ok
    assert report.evidence_after_as_of == 1


def test_single_claim_year_must_match_evidence_year() -> None:
    payload = _payload("The 1851 recipe uses sugar.", evidence=[_evidence(year=1871)])
    report = check_temporal(payload, [_hit(year=1871)], as_of=1871)
    assert report.year_mismatches == 1
    assert report.ok


def test_two_claim_years_accept_either_evidence_year() -> None:
    payload = _payload(
        "Sugar in 1851, soda in 1871.",
        as_of=1871,
        evidence=[_evidence(year=1851), _evidence("p2", year=1871)],
    )
    report = check_temporal(payload, [_hit(year=1851), _hit("p2", year=1871)], as_of=1871)
    assert report.year_mismatches == 0
    assert report.ok


def test_evidence_year_falls_back_to_retrieved_passage() -> None:
    payload = _payload("Bake it for one hour.", as_of=1851, evidence=[_evidence(year=None)])
    report = check_temporal(payload, [_hit(year=1871)], as_of=1851)
    assert report.evidence_after_as_of == 1
