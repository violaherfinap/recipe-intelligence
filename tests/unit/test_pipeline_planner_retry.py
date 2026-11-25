from __future__ import annotations

from recipe_qa.config import (
    AbstainConfig,
    PlannerConfig,
    RetrievalConfig,
    RetryConfig,
    SystemConfig,
)
from recipe_qa.generation.schema import AnswerPayload
from recipe_qa.pipeline.common import run_query
from recipe_qa.retrieval.types import Hit


def _hit(passage_id: str, text: str, score: float = 1.0) -> Hit:
    return Hit(
        passage_id=passage_id,
        doc_id=f"doc:{passage_id}",
        score=score,
        passage={
            "passage_id": passage_id,
            "doc_id": f"doc:{passage_id}",
            "text": text,
            "source_year": 1871,
        },
        rank=1,
    )


class RecordingRetriever:
    def __init__(self, responses: list[list[Hit]] | None = None) -> None:
        self.responses = responses
        self.calls: list[tuple[str, dict | None]] = []

    def retrieve(self, query: str, filter_spec=None) -> list[Hit]:
        self.calls.append((query, filter_spec))
        if self.responses is None:
            return [_hit(f"p{len(self.calls)}", query)]
        index = len(self.calls) - 1
        return self.responses[index] if index < len(self.responses) else []


def _config(
    planner: PlannerConfig | None = None,
    retry: RetryConfig | None = None,
) -> SystemConfig:
    return SystemConfig(
        id="test",
        retrieval=RetrievalConfig(mode="dense", final_k=5),
        abstain=AbstainConfig(enabled=False),
        planner=planner or PlannerConfig(enabled=False),
        retry=retry or RetryConfig(enabled=False),
    )


def test_pipeline_uses_planner_subqueries():
    retriever = RecordingRetriever()
    result = run_query(
        _config(PlannerConfig(enabled=True, max_subqueries=3)),
        {
            "query_id": "q001",
            "text": "Compare 1851 and 1871 recipes.",
            "filter": {"year_min": 1851, "year_max": 1871},
        },
        retriever=retriever,
        generator=None,
    )
    assert [call[1]["year_min"] for call in retriever.calls] == [1851, 1871]
    assert result["plan"]["rationale"] == "temporal-year-decomposition"
    assert len(result["retrieved"]) == 2
    assert "retry" not in result


def test_pipeline_retries_when_sufficiency_is_low():
    retriever = RecordingRetriever([[], [_hit("p1", "old recipe sugar")]])
    result = run_query(
        _config(retry=RetryConfig(enabled=True, max_retries=1, min_sufficiency=1.1)),
        {"query_id": "q001", "text": "old recipe"},
        retriever=retriever,
        generator=None,
    )
    assert len(retriever.calls) == 2
    assert result["retry"]["attempts"][0]["hits"] == 1
    assert result["retry"]["initial_score"] == 0.0
    assert len(result["retrieved"]) == 1


def test_pipeline_skips_retry_when_sufficiency_is_met():
    retriever = RecordingRetriever([[_hit("p1", "old recipe sugar")]])
    result = run_query(
        _config(retry=RetryConfig(enabled=True, max_retries=2, min_sufficiency=0.0)),
        {"query_id": "q001", "text": "old recipe"},
        retriever=retriever,
        generator=None,
    )
    assert len(retriever.calls) == 1
    assert result["retry"]["attempts"] == []


def test_pipeline_omits_planner_retry_metadata_when_disabled():
    retriever = RecordingRetriever()
    result = run_query(
        _config(),
        {"query_id": "q001", "text": "old recipe"},
        retriever=retriever,
        generator=None,
    )
    assert len(retriever.calls) == 1
    assert "plan" not in result
    assert "retry" not in result


class FakePlannerGenerator:
    def generate(self, prompt: str) -> str:
        return (
            '{"rationale": "llm split", "subqueries": ['
            '{"text": "nutmeg 1896"}, {"text": "mace 1896"}]}'
        )

    def answer(self, prompt: str, query_id: str) -> tuple[AnswerPayload, str]:
        return AnswerPayload(query_id=query_id, answer="Use nutmeg and mace."), "{}"


def test_pipeline_uses_llm_planner_when_generator_is_available():
    retriever = RecordingRetriever()
    result = run_query(
        _config(PlannerConfig(enabled=True, mode="llm", max_subqueries=3)),
        {"query_id": "q001", "text": "Which 1896 recipe uses both nutmeg and mace?"},
        retriever=retriever,
        generator=FakePlannerGenerator(),
    )
    assert [call[0] for call in retriever.calls] == ["nutmeg 1896", "mace 1896"]
    assert result["plan"]["rationale"] == "llm split"
    assert result["answer"]["answer"] == "Use nutmeg and mace."
