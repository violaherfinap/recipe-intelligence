from __future__ import annotations

import pytest

from recipe_qa.benchmark.review import (
    DECISION_ACCEPT,
    DECISION_SKIP,
    combine_review_notes,
    parse_decisions,
    reviewed_progress,
)
from recipe_qa.benchmark.schema import Qrel


def _qrel(
    query_id: str,
    passage_id: str,
    relevance: int = 0,
    notes: str = "",
) -> Qrel:
    return Qrel(
        query_id=query_id,
        passage_id=passage_id,
        doc_id=f"doc:{passage_id}",
        doc_version="a" * 40,
        relevance=relevance,
        annotator="preannotator",
        notes=notes,
    )


def test_reviewed_progress_ignores_rows_outside_draft() -> None:
    draft = [
        _qrel("q009", "p1"),
        _qrel("q009", "p2"),
        _qrel("q010", "p3"),
    ]
    reviewed = [
        _qrel("q009", "p1", relevance=2),
        _qrel("q009", "p9", relevance=2),
        _qrel("q010", "p3", relevance=1),
    ]
    assert reviewed_progress(draft, reviewed) == {
        "q009": (1, 2),
        "q010": (1, 1),
    }


def test_combine_review_notes_marks_override() -> None:
    assert combine_review_notes("draft reason", "checked passage", 1, 2) == (
        "draft reason | review: checked passage | override: 1->2"
    )


def test_combine_review_notes_accept_keeps_draft_note() -> None:
    assert combine_review_notes("draft reason", "", 2, 2) == "draft reason"


def test_parse_decisions_accepts_aliases_and_ordering() -> None:
    assert parse_decisions("A 0 1 2 s", 5) == [
        DECISION_ACCEPT,
        "0",
        "1",
        "2",
        DECISION_SKIP,
    ]


def test_parse_decisions_all_accepts_every_candidate() -> None:
    assert parse_decisions("all", 3) == [DECISION_ACCEPT] * 3


def test_parse_decisions_rejects_wrong_count() -> None:
    with pytest.raises(ValueError, match="perlu 3 keputusan"):
        parse_decisions("a a", 3)


def test_parse_decisions_rejects_unknown_token() -> None:
    with pytest.raises(ValueError, match="token tidak dikenal"):
        parse_decisions("a x", 2)
