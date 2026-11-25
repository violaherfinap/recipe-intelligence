from __future__ import annotations

from recipe_qa.config import PlannerConfig
from recipe_qa.pipeline.planner import Planner


def test_planner_disabled_returns_original_query():
    planner = Planner(PlannerConfig(enabled=False))
    plan = planner.plan("How did the sweetener change between 1851 and 1871?")
    assert len(plan.subqueries) == 1
    assert plan.subqueries[0].text.startswith("How did")
    assert plan.rationale == "disabled"


def test_planner_decomposes_two_year_temporal_query():
    planner = Planner(PlannerConfig(enabled=True, max_subqueries=3))
    plan = planner.plan(
        "How did the sweetener change between 1851 and 1871?",
        filter_spec={"year_min": 1851, "year_max": 1871, "book": None},
    )
    assert plan.rationale == "temporal-year-decomposition"
    assert len(plan.subqueries) == 2
    assert [subquery.filter["year_min"] for subquery in plan.subqueries] == [1851, 1871]
    assert [subquery.filter["year_max"] for subquery in plan.subqueries] == [1851, 1871]
    assert all(subquery.filter.get("book") is None for subquery in plan.subqueries)


def test_planner_decomposes_both_entities():
    planner = Planner(PlannerConfig(enabled=True, max_subqueries=3))
    plan = planner.plan("Which 1896 recipe uses both nutmeg and mace?")
    assert plan.rationale == "multi-entity-decomposition"
    assert [subquery.text for subquery in plan.subqueries] == [
        "Which 1896 recipe uses nutmeg?",
        "Which 1896 recipe uses mace?",
    ]


def test_planner_does_not_decompose_duplicate_entities():
    planner = Planner(PlannerConfig(enabled=True, max_subqueries=3))
    plan = planner.plan("Which recipe uses both mace and mace?")
    assert len(plan.subqueries) == 1
    assert plan.rationale == "single"


def test_planner_respects_max_subqueries():
    planner = Planner(PlannerConfig(enabled=True, max_subqueries=1))
    plan = planner.plan("Compare 1851 and 1871 recipes.")
    assert len(plan.subqueries) == 1
    assert plan.rationale == "single"


def test_planner_plan_is_serializable():
    planner = Planner(PlannerConfig(enabled=True, max_subqueries=3))
    plan = planner.plan("Which 1896 recipe uses both nutmeg and mace?")
    payload = plan.to_dict()
    assert payload["rationale"] == "multi-entity-decomposition"
    assert len(payload["subqueries"]) == 2


class FakeLlm:
    def __init__(self, output: str) -> None:
        self.output = output
        self.prompts: list[str] = []

    def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.output


def test_llm_planner_uses_json_subqueries():
    llm = FakeLlm(
        '{"rationale": "llm split", "subqueries": ['
        '{"text": "nutmeg 1896", "filter": {"year_min": 1896}},'
        '{"text": "mace 1896", "filter": null}]}'
    )
    planner = Planner(
        PlannerConfig(enabled=True, mode="llm", max_subqueries=3),
        llm=llm,
    )
    plan = planner.plan(
        "Which 1896 recipe uses both nutmeg and mace?",
        filter_spec={"year_min": 1896, "book": "boston"},
    )
    assert plan.rationale == "llm split"
    assert [subquery.text for subquery in plan.subqueries] == [
        "nutmeg 1896",
        "mace 1896",
    ]
    assert plan.subqueries[0].filter["book"] == "boston"
    assert plan.subqueries[1].filter["year_min"] == 1896
    assert llm.prompts


def test_llm_planner_falls_back_to_rule_on_invalid_json():
    planner = Planner(
        PlannerConfig(enabled=True, mode="llm", max_subqueries=3),
        llm=FakeLlm("not json"),
    )
    plan = planner.plan(
        "Compare 1851 and 1871 recipes.",
        filter_spec={"year_min": 1851, "year_max": 1871},
    )
    assert plan.rationale == "temporal-year-decomposition"
    assert len(plan.subqueries) == 2


def test_llm_planner_respects_max_subqueries():
    planner = Planner(
        PlannerConfig(enabled=True, mode="llm", max_subqueries=2),
        llm=FakeLlm(
            '{"rationale": "too many", "subqueries": ['
            '{"text": "a"}, {"text": "b"}, {"text": "c"}]}'
        ),
    )
    plan = planner.plan("test query")
    assert [subquery.text for subquery in plan.subqueries] == ["a", "b"]


def test_llm_planner_without_model_falls_back_to_rule():
    planner = Planner(PlannerConfig(enabled=True, mode="llm", max_subqueries=3))
    plan = planner.plan(
        "Compare 1851 and 1871 recipes.",
        filter_spec={"year_min": 1851, "year_max": 1871},
    )
    assert plan.rationale == "temporal-year-decomposition"
