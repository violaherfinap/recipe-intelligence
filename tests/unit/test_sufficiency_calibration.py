from __future__ import annotations

from recipe_qa.eval.sufficiency_calibration import (
    answerable_labels,
    balanced_accuracy,
    calibrate,
    extract_scores,
)


def test_answerable_labels_use_any_nonzero_relevance():
    labels = answerable_labels(
        [
            {"query_id": "q1", "relevance": 2},
            {"query_id": "q1", "relevance": 0},
            {"query_id": "q2", "relevance": 0},
            {"query_id": "q3", "relevance": 1},
        ]
    )
    assert labels == {"q1": True, "q2": False, "q3": True}


def test_extract_scores_skips_missing_sufficiency():
    rows = [
        {"query_id": "q1", "sufficiency": {"score": 0.4}},
        {"query_id": "q2", "sufficiency": None},
        {"query_id": "q3"},
    ]
    assert extract_scores(rows) == [("q1", 0.4)]


def test_calibration_separates_clean_classes():
    scored = [("a", 0.9), ("b", 0.8), ("n1", 0.1), ("n2", 0.2)]
    labels = {"a": True, "b": True, "n1": False, "n2": False}
    report = calibrate(scored, labels, step=0.05)
    assert report["balanced_accuracy"] == 1.0
    assert report["threshold"] == 0.25
    assert report["answerable"] == 2
    assert report["no_evidence"] == 2


def test_balanced_accuracy_requires_both_classes():
    assert balanced_accuracy([("a", 0.9)], {"a": True}, 0.5) == 0.0
