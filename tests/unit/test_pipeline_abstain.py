from __future__ import annotations

from recipe_qa.config import AbstainConfig, RetrievalConfig, SystemConfig, VerificationConfig
from recipe_qa.generation.schema import AnswerPayload, Claim, EvidenceItem
from recipe_qa.pipeline.abstain import AbstainPolicy, decide_abstain
from recipe_qa.pipeline.common import run_query
from recipe_qa.retrieval.types import Hit
from recipe_qa.verify.citations import check_citations
from recipe_qa.verify.temporal import check_temporal


def _hit(passage_id: str = "p1", year: int = 1851) -> Hit:
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
    claim: str = "Bake for one hour.", evidence: list[EvidenceItem] | None = None
) -> AnswerPayload:
    return AnswerPayload(
        query_id="q001",
        answer=claim,
        claims=[
            Claim(
                claim_id="c1",
                claim=claim,
                verdict="SUPPORTED",
                as_of=1851,
                evidence_for=evidence or [],
            )
        ],
    )


def _evidence(passage_id: str = "p1", year: int = 1851) -> EvidenceItem:
    return EvidenceItem(passage_id=passage_id, doc_id=f"doc:{passage_id}", source_year=year)


class FakeRetriever:
    def __init__(self, hits: list[Hit]) -> None:
        self.hits = hits

    def retrieve(self, query: str, filter_spec=None) -> list[Hit]:
        return self.hits


class FakeGenerator:
    def __init__(self, payload: AnswerPayload) -> None:
        self.payload = payload

    def answer(self, prompt: str, query_id: str) -> tuple[AnswerPayload, str]:
        return self.payload.model_copy(update={"query_id": query_id}), "{}"

    def answer_with_repair(
        self,
        prompt: str,
        query_id: str,
        max_repairs: int = 0,
    ) -> tuple[AnswerPayload, str, int]:
        payload, raw = self.answer(prompt, query_id)
        return payload, raw, 0


def _config(**abstain) -> SystemConfig:
    return SystemConfig(
        id="test",
        retrieval=RetrievalConfig(mode="dense", final_k=2),
        verification=VerificationConfig(enabled=False),
        abstain=AbstainConfig(enabled=True, **abstain),
    )


def test_no_hits_abstains_with_no_recipe() -> None:
    payload, decision = decide_abstain(_payload(), [])
    assert decision.abstain
    assert decision.reason == "no_recipe"
    assert payload.abstain


def test_invalid_schema_abstains_with_format_error() -> None:
    payload = _payload().model_copy(update={"schema_valid": False})
    _, decision = decide_abstain(payload, [_hit()])
    assert decision.reason == "format_error"


def test_unknown_citation_abstains_when_policy_is_on() -> None:
    payload = _payload(evidence=[_evidence("p9")])
    citations = check_citations(payload, [_hit()])
    updated, decision = decide_abstain(
        payload,
        [_hit()],
        citations=citations,
        policy=AbstainPolicy(on_citation_failure=True),
    )
    assert decision.reason == "citation_failure"
    assert decision.triggers == ["unknown_citation"]
    assert updated.abstain
    assert updated.claims == []


def test_missing_evidence_abstains_only_when_required() -> None:
    payload = _payload()
    citations = check_citations(payload, [_hit()])
    _, decision = decide_abstain(
        payload,
        [_hit()],
        citations=citations,
        policy=AbstainPolicy(on_citation_failure=True, require_evidence=True),
    )
    assert decision.reason == "citation_failure"
    assert decision.triggers == ["missing_evidence"]


def test_temporal_violation_abstains_when_policy_is_on() -> None:
    payload = _payload("The 1871 book bakes it for an hour.", [_evidence(year=1871)])
    temporal = check_temporal(payload, [_hit(year=1871)], as_of=1851)
    _, decision = decide_abstain(
        payload,
        [_hit()],
        temporal=temporal,
        policy=AbstainPolicy(on_temporal_violation=True),
    )
    assert decision.reason == "temporal_violation"
    assert decision.triggers == ["temporal_violation"]


def test_clean_answer_is_not_abstained() -> None:
    payload = _payload(evidence=[_evidence()])
    citations = check_citations(payload, [_hit()])
    temporal = check_temporal(payload, [_hit()], as_of=1851)
    updated, decision = decide_abstain(
        payload,
        [_hit()],
        citations=citations,
        temporal=temporal,
        policy=AbstainPolicy(on_citation_failure=True, on_temporal_violation=True),
    )
    assert not decision.abstain
    assert updated.abstain is False


def test_pipeline_reports_citation_failure() -> None:
    result = run_query(
        _config(citations=True),
        {"query_id": "q001", "text": "How long are baked apples baked?", "as_of": 1851},
        retriever=FakeRetriever([_hit()]),
        generator=FakeGenerator(_payload(evidence=[_evidence("p9")])),
        verifier=None,
    )
    assert result["answer"]["abstain"]
    assert result["answer"]["abstain_reason"] == "citation_failure"
    assert result["citations"]["unknown_passages"] == ["p9"]
    assert result["abstain"]["triggers"] == ["unknown_citation"]


def test_pipeline_reports_temporal_violation() -> None:
    payload = _payload("The 1871 book bakes it for an hour.", [_evidence(year=1871)])
    result = run_query(
        _config(temporal=True),
        {"query_id": "q001", "text": "How long are baked apples baked?", "as_of": 1851},
        retriever=FakeRetriever([_hit(year=1871)]),
        generator=FakeGenerator(payload),
        verifier=None,
    )
    assert result["answer"]["abstain_reason"] == "temporal_violation"
    assert result["temporal"]["after_as_of"] == 1
    assert not result["temporal"]["ok"]


def test_pipeline_keeps_answer_when_checks_disabled() -> None:
    result = run_query(
        _config(),
        {"query_id": "q001", "text": "How long are baked apples baked?", "as_of": 1851},
        retriever=FakeRetriever([_hit()]),
        generator=FakeGenerator(_payload(evidence=[_evidence("p9")])),
        verifier=None,
    )
    assert not result["answer"]["abstain"]
    assert "citations" not in result
    assert "temporal" not in result


def test_b4_verify_config_enables_citation_and_temporal_checks() -> None:
    from pathlib import Path

    from recipe_qa.config import load_system_config

    config = load_system_config(Path("configs/b4_verify.yaml"))
    assert config.abstain.enabled
    assert config.abstain.citations
    assert config.abstain.temporal
    assert not config.abstain.require_evidence
