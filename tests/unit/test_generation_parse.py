from __future__ import annotations

from recipe_qa.generation.generate import extract_json_object, parse_answer


def test_extract_json_object_handles_surrounding_text():
    text = 'Here is the answer:\n{"query_id": "q001", "answer": "ok"}\nDone.'
    assert extract_json_object(text) == '{"query_id": "q001", "answer": "ok"}'


def test_parse_answer_valid():
    payload = parse_answer(
        '{"query_id": "q001", "answer": "1.5 hours", "claims": [], "abstain": false, '
        '"abstain_reason": null, "confidence": 0.8, "schema_valid": true}',
        "q001",
    )
    assert payload.query_id == "q001"
    assert payload.schema_valid is True
    assert payload.answer == "1.5 hours"


def test_parse_answer_invalid_returns_abstain():
    payload = parse_answer("not json at all", "q001")
    assert payload.query_id == "q001"
    assert payload.schema_valid is False
    assert payload.abstain is True
    assert payload.abstain_reason == "format_error"


def test_parse_answer_normalises_near_json():
    text = (
        '{"query_id": "1", "answer": "One hour and a quarter", '
        '"claims": ["The recipe requires one hour and a quarter."], '
        '"abstain": {"reason": "not sure", "confidence": 0.9}, '
        '"abstain_reason": "not specified", "confidence": 0.9, "schema_valid": true}'
    )
    payload = parse_answer(text, "q002")
    assert payload.query_id == "q002"
    assert payload.schema_valid is True
    assert payload.answer == "One hour and a quarter"
    assert payload.claims[0].verdict == "NOT_ENOUGH_EVIDENCE"
    assert payload.abstain is False
    assert payload.abstain_reason is None
