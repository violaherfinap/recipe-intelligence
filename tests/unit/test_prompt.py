from __future__ import annotations

from pathlib import Path

from recipe_qa.generation.prompt import (
    format_evidence,
    load_examples,
    render_prompt,
)
from recipe_qa.retrieval.types import Hit


def fake_hit():
    passage = {
        "passage_id": "ye-old-american:test#directions#0",
        "doc_id": "ye-old-american:test",
        "source_year": 1896,
        "source_title": "Test Book",
        "section": "directions",
        "text": "Bake for one and a half hours.",
    }
    return Hit(
        passage_id=passage["passage_id"],
        doc_id=passage["doc_id"],
        score=0.9,
        passage=passage,
        rank=1,
    )


def test_render_prompt_with_evidence_and_few_shot():
    prompt, meta = render_prompt(
        Path("prompts/registry/structured_v1.yaml"),
        "How long is the cake baked?",
        1896,
        format_evidence([fake_hit()]),
        examples=load_examples(Path("prompts/examples.jsonl"), 2),
        few_shot=True,
    )
    assert "How long is the cake baked?" in prompt
    assert "ye-old-american:test#directions#0" in prompt
    assert "Example 1" in prompt
    assert meta["id"] == "structured_v1"
    assert len(meta["hash"]) == 64


def test_render_prompt_without_evidence_or_examples():
    prompt, _ = render_prompt(
        Path("prompts/registry/structured_v1.yaml"),
        "Who wrote this?",
        None,
        "(no evidence retrieved)",
        examples=[],
        few_shot=False,
    )
    assert "Who wrote this?" in prompt
    assert "Example 1" not in prompt
    assert "not specified" in prompt
