from __future__ import annotations

from recipe_qa.generation.schema import AnswerPayload, Claim
from recipe_qa.retrieval.types import Hit
from recipe_qa.verify.claims import verify_claims
from recipe_qa.verify.nli import NliScores


class FakeScorer:
    def __init__(
        self,
        entailment: float = 0.0,
        contradiction: float = 0.0,
        mapping: dict[str, tuple[float, float]] | None = None,
    ) -> None:
        self.entailment = entailment
        self.contradiction = contradiction
        self.mapping = mapping or {}

    def __call__(self, premise: str, hypothesis: str) -> NliScores:
        entailment, contradiction = self.mapping.get(
            hypothesis,
            (self.entailment, self.contradiction),
        )
        return NliScores(
            entailment=entailment,
            contradiction=contradiction,
            neutral=max(0.0, 1.0 - entailment - contradiction),
        )


def _hit(passage_id: str = "p1", text: str = "baked apples with sugar") -> Hit:
    return Hit(
        passage_id=passage_id,
        doc_id=f"doc:{passage_id}",
        score=1.0,
        passage={
            "passage_id": passage_id,
            "text": text,
            "source_year": 1871,
        },
        rank=1,
    )


def _payload(*claims: str) -> AnswerPayload:
    return AnswerPayload(
        query_id="q001",
        answer=" ".join(claims),
        claims=[
            Claim(claim_id=f"c{index}", claim=claim, verdict="SUPPORTED")
            for index, claim in enumerate(claims, start=1)
        ],
    )


def test_verify_claims_keeps_supported_claim():
    payload, report = verify_claims(
        _payload("The recipe uses cinnamon."),
        [_hit(text="This recipe uses cinnamon and mace.")],
        FakeScorer(entailment=0.9),
        model="fake",
    )
    assert report.supported == 1
    assert report.dropped == 0
    assert not payload.abstain
    assert payload.claims[0].verdict == "SUPPORTED"
    assert payload.claims[0].evidence_for[0].passage_id == "p1"


def test_verify_claims_drops_unsupported_and_abstains():
    payload, report = verify_claims(
        _payload("The recipe bakes for 15 to 20 minutes."),
        [_hit(text="Mix the apples with sugar.")],
        FakeScorer(entailment=0.1, contradiction=0.1),
        model="fake",
    )
    assert report.supported == 0
    assert report.dropped == 1
    assert report.abstained
    assert payload.abstain
    assert payload.abstain_reason == "not_specified"
    assert payload.answer == ""
    assert payload.claims == []


def test_verify_claims_drops_refuted_by_default():
    payload, report = verify_claims(
        _payload("The recipe uses one pound of butter."),
        [_hit(text="The recipe uses four ounces of butter.")],
        FakeScorer(contradiction=0.9),
        model="fake",
    )
    assert report.refuted == 1
    assert report.dropped == 1
    assert payload.abstain


def test_verify_claims_can_keep_refuted():
    payload, report = verify_claims(
        _payload("The recipe uses one pound of butter."),
        [_hit(text="The recipe uses four ounces of butter.")],
        FakeScorer(contradiction=0.9),
        model="fake",
        keep_refuted=True,
    )
    assert report.refuted == 1
    assert report.dropped == 0
    assert not payload.abstain
    assert payload.claims[0].verdict == "REFUTED"
    assert payload.claims[0].evidence_against[0].passage_id == "p1"


def test_verify_claims_rewrites_partial_answer():
    payload, report = verify_claims(
        _payload(
            "The recipe uses cinnamon.",
            "The recipe bakes for 15 to 20 minutes.",
        ),
        [_hit(text="This recipe uses cinnamon and mace.")],
        FakeScorer(
            mapping={
                "The recipe uses cinnamon.": (0.9, 0.0),
                "The recipe bakes for 15 to 20 minutes.": (0.1, 0.1),
            }
        ),
        model="fake",
    )
    assert report.supported == 1
    assert report.dropped == 1
    assert not payload.abstain
    assert payload.answer == "The recipe uses cinnamon."
    assert len(payload.claims) == 1


def test_verify_claims_leaves_abstain_payload_unchanged():
    original = AnswerPayload(
        query_id="q001",
        abstain=True,
        abstain_reason="not_specified",
    )
    payload, report = verify_claims(original, [], FakeScorer(), model="fake")
    assert payload is original
    assert report.abstained
    assert report.claims_before == 0


class PremiseScorer:
    def __init__(self, mapping: dict[str, tuple[float, float]]) -> None:
        self.mapping = mapping

    def __call__(self, premise: str, hypothesis: str) -> NliScores:
        entailment, contradiction = self.mapping[premise]
        return NliScores(
            entailment=entailment,
            contradiction=contradiction,
            neutral=max(0.0, 1.0 - entailment - contradiction),
        )


def test_verify_claims_cited_support_wins_over_other_contradiction():
    supporting = _hit("p1", "Steam the quinces in the oven for one hour.")
    conflicting = _hit("p2", "Steam the quinces for two hours.")
    payload = AnswerPayload(
        query_id="q021",
        answer="The quinces were steamed in the oven for one hour.",
        claims=[
            Claim(
                claim_id="c1",
                claim="The quinces were steamed in the oven for one hour.",
                verdict="SUPPORTED",
                evidence_for=[
                    {
                        "passage_id": "p1",
                        "doc_id": "doc:p1",
                        "source_year": 1871,
                        "span": "Steam the quinces in the oven for one hour.",
                    }
                ],
            )
        ],
    )
    payload, report = verify_claims(
        payload,
        [supporting, conflicting],
        PremiseScorer(
            {
                supporting.passage["text"]: (0.9, 0.0),
                conflicting.passage["text"]: (0.0, 1.0),
            }
        ),
        model="fake",
    )
    assert report.supported == 1
    assert report.dropped == 0
    assert payload.claims[0].verdict == "SUPPORTED"
    assert payload.claims[0].evidence_for[0].passage_id == "p1"
