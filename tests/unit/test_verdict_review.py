from __future__ import annotations

import pytest

from recipe_qa.benchmark.verdict_review import (
    parse_answer_sheet,
    parse_verdict_decisions,
)


def test_parse_verdict_decisions_per_claim() -> None:
    decisions = parse_verdict_decisions("c1=s c2=n", ["c1", "c2"])
    assert decisions == {"c1": "SUPPORTED", "c2": "NOT_ENOUGH_EVIDENCE"}


def test_parse_verdict_decisions_supports_full_labels() -> None:
    decisions = parse_verdict_decisions("c1=SUPPORTED c2=REFUTED", ["c1", "c2"])
    assert decisions == {"c1": "SUPPORTED", "c2": "REFUTED"}


def test_parse_verdict_decisions_supports_numeric_claim_ids() -> None:
    assert parse_verdict_decisions("1=s", ["c1"]) == {"c1": "SUPPORTED"}


def test_parse_verdict_decisions_supports_all() -> None:
    assert parse_verdict_decisions("all=r", ["c1", "c2"]) == {
        "c1": "REFUTED",
        "c2": "REFUTED",
    }


def test_parse_verdict_decisions_rejects_missing_claim() -> None:
    with pytest.raises(ValueError, match="missing verdict"):
        parse_verdict_decisions("c1=s", ["c1", "c2"])


def test_parse_verdict_decisions_rejects_unknown_claim() -> None:
    with pytest.raises(ValueError, match="unknown claim"):
        parse_verdict_decisions("c9=s", ["c1"])


def test_parse_verdict_decisions_rejects_duplicate_claim() -> None:
    with pytest.raises(ValueError, match="duplicate verdict"):
        parse_verdict_decisions("c1=s c1=r", ["c1"])


def test_parse_verdict_decisions_rejects_unknown_verdict() -> None:
    with pytest.raises(ValueError, match="unknown verdict"):
        parse_verdict_decisions("c1=x", ["c1"])


def test_parse_answer_sheet_multiple_queries() -> None:
    text = """
    # answer sheet
    q001 c1=s
    q002: c1=s c2=n  # inline comment
    """
    answers = parse_answer_sheet(text, {"q001": ["c1"], "q002": ["c1", "c2"]})
    assert answers == {
        "q001": {"c1": "SUPPORTED"},
        "q002": {"c1": "SUPPORTED", "c2": "NOT_ENOUGH_EVIDENCE"},
    }


def test_parse_answer_sheet_supports_all() -> None:
    answers = parse_answer_sheet("q001 all=n", {"q001": ["c1", "c2"]})
    assert answers == {"q001": {"c1": "NOT_ENOUGH_EVIDENCE", "c2": "NOT_ENOUGH_EVIDENCE"}}


def test_parse_answer_sheet_rejects_duplicate_query() -> None:
    with pytest.raises(ValueError, match="duplicate query"):
        parse_answer_sheet("q001 c1=s\nq001 c1=r", {"q001": ["c1"]})


def test_parse_answer_sheet_rejects_unknown_query() -> None:
    with pytest.raises(ValueError, match="unknown query"):
        parse_answer_sheet("q999 c1=s", {"q001": ["c1"]})


def test_parse_answer_sheet_rejects_missing_verdicts() -> None:
    with pytest.raises(ValueError, match="missing verdicts"):
        parse_answer_sheet("q001", {"q001": ["c1"]})


def test_parse_answer_sheet_rejects_missing_claim() -> None:
    with pytest.raises(ValueError, match="missing verdict"):
        parse_answer_sheet("q001 c1=s", {"q001": ["c1", "c2"]})


def test_parse_answer_sheet_rejects_empty_sheet() -> None:
    with pytest.raises(ValueError, match="empty"):
        parse_answer_sheet("# only comments", {"q001": ["c1"]})
