"""Tests for benchmark schema contracts."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from recipe_qa.benchmark.schema import (
    GoldCandidate,
    Qrel,
    Query,
    QueryFilter,
    VerdictQrel,
)


def test_temporal_query_requires_as_of() -> None:
    with pytest.raises(ValidationError):
        Query(
            query_id="q001",
            text="Did the 1851 and 1896 books agree on baking powder?",
            slice="temporal",
            as_of=None,
        )


def test_no_evidence_query_rejects_gold_claims() -> None:
    with pytest.raises(ValidationError):
        Query(
            query_id="q001",
            text="What internal temperature does the 1896 book require?",
            slice="no-evidence",
            as_of=1896,
            gold_claims=["Chicken is roasted."],
        )


def test_query_accepts_filter() -> None:
    query = Query(
        query_id="q001",
        text="How long is tomato soup simmered in the 1896 book?",
        slice="easy",
        scope="year:1896",
        as_of=1896,
        filter=QueryFilter(year_min=1896, year_max=1896),
        gold_claims=["Tomato soup is simmered for twenty minutes."],
    )
    assert query.query_id == "q001"
    assert query.filter is not None and query.filter.year_min == 1896


def test_qrel_rejects_invalid_relevance() -> None:
    with pytest.raises(ValidationError):
        Qrel(
            query_id="q001",
            passage_id="p",
            doc_id="d",
            doc_version="a" * 40,
            relevance=3,
            annotator="C",
        )


def test_gold_candidate_requires_passages() -> None:
    with pytest.raises(ValidationError):
        GoldCandidate(query_id="q001", passage_ids=[], doc_ids=["d"])


def test_verdict_qrel_accepts_three_labels() -> None:
    for verdict in ("SUPPORTED", "REFUTED", "NOT_ENOUGH_EVIDENCE"):
        row = VerdictQrel(
            query_id="q001",
            claim_id="c1",
            verdict=verdict,
            annotator="D",
        )
        assert row.verdict == verdict
