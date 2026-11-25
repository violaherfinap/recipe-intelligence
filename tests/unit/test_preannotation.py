from __future__ import annotations

from recipe_qa.benchmark.preannotation import parse_answers, validate_answers


def test_parse_answers_accepts_pipe_format() -> None:
    parsed = parse_answers(
        "# comment\nq001|p1|2|langsung menjawab\nq002|p2|0|resep lain\n"
    )
    assert not parsed.errors
    assert parsed.rows == [
        {
            "query_id": "q001",
            "passage_id": "p1",
            "relevance": 2,
            "notes": "langsung menjawab",
        },
        {
            "query_id": "q002",
            "passage_id": "p2",
            "relevance": 0,
            "notes": "resep lain",
        },
    ]


def test_parse_answers_rejects_duplicate_and_bad_label() -> None:
    parsed = parse_answers("q001|p1|2\nq001|p1|1\nq001|p2|3\n")
    assert len(parsed.errors) == 2
    assert any("duplicate" in error for error in parsed.errors)
    assert any("relevance" in error for error in parsed.errors)


def test_validate_answers_reports_missing_and_extra() -> None:
    errors = validate_answers(
        [{"query_id": "q001", "passage_id": "p1", "relevance": 2, "notes": ""}],
        {("q001", "p1"), ("q002", "p2")},
    )
    assert any("missing answer keys" in error for error in errors)
