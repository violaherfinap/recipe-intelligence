from __future__ import annotations

import pytest

from recipe_qa.eval.metrics.claims import (
    VERDICT_LABELS,
    citation_precision,
    citation_recall,
    macro_f1,
    unsupported_claim_rate,
)


def test_macro_f1_perfect_predictions() -> None:
    gold = ["SUPPORTED", "REFUTED", "NOT_ENOUGH_EVIDENCE", "SUPPORTED"]
    assert macro_f1(gold, gold, VERDICT_LABELS) == pytest.approx(1.0)


def test_macro_f1_matches_hand_calculation() -> None:
    gold = ["SUPPORTED", "SUPPORTED", "REFUTED", "NOT_ENOUGH_EVIDENCE"]
    predicted = ["SUPPORTED", "REFUTED", "REFUTED", "NOT_ENOUGH_EVIDENCE"]
    expected = (2 / 3 + 2 / 3 + 1.0) / 3
    assert macro_f1(gold, predicted, VERDICT_LABELS) == pytest.approx(expected)


def test_macro_f1_includes_absent_labels_as_zero() -> None:
    assert macro_f1(["SUPPORTED"], ["SUPPORTED"], VERDICT_LABELS) == pytest.approx(1 / 3)


def test_macro_f1_rejects_mismatched_lengths() -> None:
    with pytest.raises(ValueError):
        macro_f1(["SUPPORTED"], [])


def test_citation_precision() -> None:
    assert citation_precision(3, 4) == pytest.approx(0.75)
    assert citation_precision(0, 0) == 0.0


def test_citation_recall() -> None:
    assert citation_recall(8, 10) == pytest.approx(0.8)
    assert citation_recall(0, 0) == 0.0


def test_unsupported_claim_rate() -> None:
    assert unsupported_claim_rate(2, 8) == pytest.approx(0.25)
    assert unsupported_claim_rate(0, 0) == 0.0
