from __future__ import annotations

from recipe_qa.generation.schema import AnswerPayload, Claim
from recipe_qa.retrieval.types import Hit
from recipe_qa.verify.claims import verify_claims
from recipe_qa.verify.nli import NliScores
from recipe_qa.verify.premise import premise_text, recipe_title


def _hit() -> Hit:
    return Hit(
        passage_id="ye-old-american:a-cheap-seed-cake#directions#0",
        doc_id="ye-old-american:a-cheap-seed-cake",
        score=1.0,
        passage={
            "passage_id": "ye-old-american:a-cheap-seed-cake#directions#0",
            "doc_id": "ye-old-american:a-cheap-seed-cake",
            "text": "1. rub one pound sugar 5. bake one and a half hours",
            "source_title": "American Cookery",
            "source_year": 1796,
        },
        rank=1,
    )


def test_recipe_title_strips_numeric_suffix() -> None:
    assert recipe_title("ye-old-american:baked-apples-2") == "baked apples"
    assert recipe_title("ye-old-american:a-cheap-seed-cake") == "a cheap seed cake"


def test_premise_text_adds_recipe_book_and_year() -> None:
    premise = premise_text(_hit().passage)
    assert premise.startswith("a cheap seed cake. American Cookery (1796). ")
    assert premise.endswith("bake one and a half hours")


def test_premise_text_without_metadata_returns_passage_text() -> None:
    assert premise_text({"text": "bake it"}) == "bake it"


class RecordingScorer:
    def __init__(self) -> None:
        self.premises: list[str] = []

    def score(self, premise: str, hypothesis: str) -> NliScores:
        self.premises.append(premise)
        return NliScores(0.9, 0.0, 0.1)


def _payload() -> AnswerPayload:
    return AnswerPayload(
        query_id="q001",
        answer="The 1796 cheap seed cake is baked for one and a half hours.",
        claims=[
            Claim(
                claim_id="c1",
                claim="The 1796 cheap seed cake is baked for one and a half hours.",
                verdict="SUPPORTED",
            )
        ],
    )


def test_verify_claims_uses_metadata_premise_when_enabled() -> None:
    scorer = RecordingScorer()
    verify_claims(_payload(), [_hit()], scorer.score, premise_context=True)
    assert scorer.premises
    assert scorer.premises[0].startswith("a cheap seed cake. American Cookery (1796). ")


def test_verify_claims_uses_raw_passage_by_default() -> None:
    scorer = RecordingScorer()
    verify_claims(_payload(), [_hit()], scorer.score)
    assert scorer.premises == ["1. rub one pound sugar 5. bake one and a half hours"]
