from __future__ import annotations

from recipe_qa.generation.generate import build_repair_prompt, generate_with_repair

VALID = (
    '{"query_id": "q001", "answer": "ok", "claims": [], "abstain": false, '
    '"abstain_reason": null, "confidence": 0.8, "schema_valid": true}'
)


def test_build_repair_prompt_includes_previous_response():
    prompt = build_repair_prompt("Question: bake?", "not json")
    assert "Question: bake?" in prompt
    assert "not json" in prompt
    assert "valid JSON object" in prompt


def test_generate_with_repair_retries_invalid_output():
    outputs = iter(["not json", VALID])
    calls: list[str] = []

    def generate(prompt: str) -> str:
        calls.append(prompt)
        return next(outputs)

    payload, raw, repairs = generate_with_repair(generate, "Question: bake?", "q001", 1)
    assert payload.schema_valid
    assert payload.answer == "ok"
    assert raw == VALID
    assert repairs == 1
    assert len(calls) == 2


def test_generate_with_repair_stops_after_max_repairs():
    outputs = iter(["not json", "still not json"])

    def generate(prompt: str) -> str:
        return next(outputs)

    payload, raw, repairs = generate_with_repair(generate, "Question: bake?", "q001", 1)
    assert not payload.schema_valid
    assert payload.abstain_reason == "format_error"
    assert raw == "still not json"
    assert repairs == 1


def test_generate_with_repair_can_be_disabled():
    payload, raw, repairs = generate_with_repair(
        lambda prompt: "not json",
        "Question: bake?",
        "q001",
        0,
    )
    assert not payload.schema_valid
    assert raw == "not json"
    assert repairs == 0
