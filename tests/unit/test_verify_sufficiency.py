from __future__ import annotations

import pytest

from recipe_qa.retrieval.types import Hit
from recipe_qa.verify.sufficiency import coverage, should_abstain, sigmoid, sufficiency


def _hit(passage_id: str, text: str, score: float = 1.0) -> Hit:
    return Hit(
        passage_id=passage_id,
        doc_id=f"doc:{passage_id}",
        score=score,
        passage={"passage_id": passage_id, "text": text, "source_year": 1871},
        rank=1,
    )


def test_sigmoid_bounds():
    assert sigmoid(0.0) == pytest.approx(0.5)
    assert sigmoid(50.0) == pytest.approx(1.0)
    assert sigmoid(-50.0) == pytest.approx(0.0)


def test_coverage_counts_unique_query_tokens():
    assert coverage("cinnamon mace", ["cinnamon and mace"]) == pytest.approx(1.0)
    assert coverage("cinnamon mace", ["cinnamon only"]) == pytest.approx(0.5)
    assert coverage("", ["cinnamon"]) == 0.0


def test_sufficiency_without_hits():
    result = sufficiency("bake apples", [])
    assert result.score == 0.0
    assert result.coverage == 0.0
    assert result.top_passage_id is None


def test_sufficiency_combines_score_and_coverage():
    result = sufficiency(
        "baked apples sugar",
        [_hit("p1", "baked apples with sugar", score=0.0)],
    )
    assert result.top_score == 0.0
    assert result.coverage == pytest.approx(1.0)
    assert result.score == pytest.approx(0.6 * 0.5 + 0.4 * 1.0)


def test_should_abstain_uses_threshold():
    result = sufficiency("baked apples sugar", [_hit("p1", "baked apples with sugar")])
    assert should_abstain(result, 0.99)
    assert not should_abstain(result, 0.0)
