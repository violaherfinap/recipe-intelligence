from __future__ import annotations

from recipe_qa.generation.schema import AnswerPayload, Claim, EvidenceItem
from recipe_qa.retrieval.types import Hit
from recipe_qa.verify.citations import check_citations


def _hit(passage_id: str = "p1") -> Hit:
    return Hit(
        passage_id=passage_id,
        doc_id=f"doc:{passage_id}",
        score=1.0,
        passage={
            "passage_id": passage_id,
            "doc_id": f"doc:{passage_id}",
            "text": "Bake the apples with sugar for one hour.",
            "source_year": 1871,
        },
        rank=1,
    )


def _payload(evidence: list[EvidenceItem]) -> AnswerPayload:
    return AnswerPayload(
        query_id="q001",
        answer="Bake for one hour.",
        claims=[
            Claim(
                claim_id="c1",
                claim="Bake for one hour.",
                verdict="SUPPORTED",
                evidence_for=evidence,
            )
        ],
    )


def _evidence(passage_id: str = "p1", span: str = "Bake the apples with sugar") -> EvidenceItem:
    return EvidenceItem(
        passage_id=passage_id,
        doc_id=f"doc:{passage_id}",
        source_year=1871,
        span=span,
    )


def test_citation_passes_for_retrieved_passage_and_matching_span() -> None:
    report = check_citations(_payload([_evidence()]), [_hit()])
    assert report.ok
    assert report.coverage == 1.0
    assert report.unknown_passages == []


def test_citation_flags_unknown_passage() -> None:
    report = check_citations(_payload([_evidence("p9", "anything")]), [_hit()])
    assert not report.ok
    assert report.unknown_passages == ["p9"]


def test_citation_flags_missing_evidence() -> None:
    report = check_citations(_payload([]), [_hit()])
    assert report.missing_evidence == 1
    assert report.coverage == 0.0


def test_citation_flags_span_that_is_not_in_passage() -> None:
    report = check_citations(_payload([_evidence(span="Roast the duck overnight")]), [_hit()])
    assert report.span_mismatches == 1
    assert not report.ok


def test_citation_skips_abstained_payload() -> None:
    payload = AnswerPayload(query_id="q001", abstain=True, abstain_reason="no_recipe")
    report = check_citations(payload, [])
    assert report.claims == 0
    assert report.coverage == 0.0
