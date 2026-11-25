from __future__ import annotations

from recipe_qa.config import AbstainConfig, RetrievalConfig, SystemConfig, VerificationConfig
from recipe_qa.generation.schema import AnswerPayload, Claim
from recipe_qa.pipeline.common import run_query
from recipe_qa.retrieval.types import Hit
from recipe_qa.verify.nli import NliScores


def _hit(text: str = "Bake the apples with sugar for one hour.") -> Hit:
    return Hit(
        passage_id="p1",
        doc_id="doc:p1",
        score=1.0,
        passage={
            "passage_id": "p1",
            "doc_id": "doc:p1",
            "text": text,
            "source_year": 1871,
        },
        rank=1,
    )


class FakeRetriever:
    def __init__(self, hits: list[Hit]) -> None:
        self.hits = hits

    def retrieve(self, query: str, filter_spec=None) -> list[Hit]:
        return self.hits


class FakeGenerator:
    def __init__(self, payload: AnswerPayload, repairs: int = 0) -> None:
        self.payload = payload
        self.repairs = repairs

    def answer(self, prompt: str, query_id: str) -> tuple[AnswerPayload, str]:
        return self.payload.model_copy(update={"query_id": query_id}), "{}"

    def answer_with_repair(
        self,
        prompt: str,
        query_id: str,
        max_repairs: int = 0,
    ) -> tuple[AnswerPayload, str, int]:
        payload, raw = self.answer(prompt, query_id)
        return payload, raw, min(self.repairs, max_repairs)


class FakeVerifier:
    def __init__(self, scores: NliScores) -> None:
        self.scores = scores

    def score(self, premise: str, hypothesis: str) -> NliScores:
        return self.scores


def _config(
    verification: VerificationConfig | None = None,
    abstain: AbstainConfig | None = None,
) -> SystemConfig:
    return SystemConfig(
        id="test",
        retrieval=RetrievalConfig(mode="dense", final_k=2),
        verification=verification or VerificationConfig(enabled=False),
        abstain=abstain or AbstainConfig(enabled=True),
    )


def _payload() -> AnswerPayload:
    return AnswerPayload(
        query_id="q001",
        answer="Bake for 15 to 20 minutes.",
        claims=[
            Claim(
                claim_id="c1",
                claim="Bake for 15 to 20 minutes.",
                verdict="SUPPORTED",
            )
        ],
    )


def test_pipeline_drops_unsupported_claim_and_abstains():
    result = run_query(
        _config(VerificationConfig(enabled=True, max_repair_rounds=0)),
        {"query_id": "q001", "text": "How long are baked apples baked?"},
        retriever=FakeRetriever([_hit()]),
        generator=FakeGenerator(_payload()),
        verifier=FakeVerifier(NliScores(0.1, 0.1, 0.8)),
    )
    assert result["answer"]["abstain"]
    assert result["answer"]["answer"] == ""
    assert result["verification"]["dropped"] == 1
    assert result["verification"]["abstained"]


def test_pipeline_keeps_supported_claim():
    result = run_query(
        _config(VerificationConfig(enabled=True, max_repair_rounds=0)),
        {"query_id": "q001", "text": "How long are baked apples baked?"},
        retriever=FakeRetriever([_hit()]),
        generator=FakeGenerator(_payload()),
        verifier=FakeVerifier(NliScores(0.9, 0.0, 0.1)),
    )
    assert not result["answer"]["abstain"]
    assert result["verification"]["supported"] == 1
    assert result["answer"]["claims"][0]["verdict"] == "SUPPORTED"


def test_pipeline_abstains_when_sufficiency_is_low():
    config = _config(
        abstain=AbstainConfig(
            enabled=True,
            sufficiency=True,
            sufficiency_threshold=0.99,
        )
    )
    result = run_query(
        config,
        {"query_id": "q001", "text": "How long are baked apples baked?"},
        retriever=FakeRetriever([_hit()]),
        generator=None,
    )
    assert result["answer"]["abstain"]
    assert result["answer"]["abstain_reason"] == "not_specified"
    assert result["sufficiency"]["abstained"]


def test_pipeline_reports_repairs():
    result = run_query(
        _config(VerificationConfig(enabled=True, max_repair_rounds=2)),
        {"query_id": "q001", "text": "How long are baked apples baked?"},
        retriever=FakeRetriever([_hit()]),
        generator=FakeGenerator(_payload(), repairs=1),
        verifier=FakeVerifier(NliScores(0.9, 0.0, 0.1)),
    )
    assert result["repairs"] == 1
    assert result["verification"]["enabled"]


def test_pipeline_splits_answer_into_sentence_claims():
    payload = AnswerPayload(
        query_id="q001",
        answer="Sugar was used in 1851. Soda was added in 1871.",
        claims=[],
    )
    result = run_query(
        _config(VerificationConfig(enabled=True, max_repair_rounds=0)),
        {"query_id": "q001", "text": "How did the sweetener change?"},
        retriever=FakeRetriever([_hit()]),
        generator=FakeGenerator(payload),
        verifier=FakeVerifier(NliScores(0.9, 0.0, 0.1)),
    )
    claims = result["answer"]["claims"]
    assert [claim["claim"] for claim in claims] == [
        "Sugar was used in 1851.",
        "Soda was added in 1871.",
    ]
    assert claims[0]["evidence_for"][0]["passage_id"] == "p1"


def test_pipeline_ignores_trivial_sentence_fragments():
    payload = AnswerPayload(
        query_id="q006",
        answer="The spices are cinnamon and mace. 3.",
        claims=[],
    )
    result = run_query(
        _config(VerificationConfig(enabled=True, max_repair_rounds=0)),
        {"query_id": "q006", "text": "Which spices are used?"},
        retriever=FakeRetriever([_hit()]),
        generator=FakeGenerator(payload),
        verifier=FakeVerifier(NliScores(0.9, 0.0, 0.1)),
    )
    claims = result["answer"]["claims"]
    assert [claim["claim"] for claim in claims] == ["The spices are cinnamon and mace."]
