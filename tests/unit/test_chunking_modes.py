from __future__ import annotations

import re

import pytest

from recipe_qa.corpus.build import build_passages, make_doc

COMMIT = "a" * 40


def whitespace_offsets(text: str) -> list[tuple[int, int]]:
    return [(match.start(), match.end()) for match in re.finditer(r"\S+", text)]


def sample_doc():
    row = {
        "title": "Test Recipe",
        "slug": "test-recipe",
        "source_year": "1896",
        "source_title": "Test Book",
        "body": (
            "## Ingredients\n\n- one egg\n- one cup milk\n\n"
            "## Directions\n\n1. Beat the egg.\n2. Add the milk and cook.\n"
        ),
    }
    doc = make_doc(row, COMMIT, "ye-old-american:test-recipe", "test-recipe")
    return doc.model_copy(update={"split": "train"})


def test_fixed_mode_uses_whole_document():
    doc = sample_doc()
    passages = build_passages(doc, whitespace_offsets, max_tokens=40, overlap=5, mode="fixed")
    assert passages
    assert all(passage.section == "fixed" for passage in passages)
    assert all("#fixed#" in passage.passage_id for passage in passages)
    for passage in passages:
        assert doc.text_clean[passage.char_start : passage.char_end] == passage.text


def test_hierarchical_mode_has_summary_and_steps():
    doc = sample_doc()
    passages = build_passages(
        doc,
        whitespace_offsets,
        max_tokens=40,
        overlap=5,
        mode="hierarchical",
    )
    sections = {passage.section for passage in passages}
    assert "summary" in sections
    assert "step" in sections
    summary = [passage for passage in passages if passage.section == "summary"][0]
    assert summary.text.startswith("Test Recipe")
    assert "- one egg" in summary.text
    steps = [passage for passage in passages if passage.section == "step"]
    assert [step.text for step in steps] == ["1. Beat the egg.", "2. Add the milk and cook."]
    for step in steps:
        assert doc.text_clean[step.char_start : step.char_end] == step.text


def test_section_mode_unchanged():
    doc = sample_doc()
    passages = build_passages(doc, whitespace_offsets, max_tokens=40, overlap=5)
    assert {passage.section for passage in passages} == {"ingredients", "directions"}
    assert all("#ingredients#" in passage.passage_id or "#directions#" in passage.passage_id for passage in passages)


def test_unknown_mode_raises():
    doc = sample_doc()
    with pytest.raises(ValueError, match="unknown chunking mode"):
        build_passages(doc, whitespace_offsets, mode="nope")
