from __future__ import annotations

import re

from recipe_qa.corpus.build import (
    build_passages,
    chunk_offsets,
    make_doc,
    split_clean_sections,
)

COMMIT = "a" * 40


def whitespace_offsets(text: str) -> list[tuple[int, int]]:
    return [(match.start(), match.end()) for match in re.finditer(r"\S+", text)]


def sample_doc(split: str = "train"):
    row = {
        "title": "Test Recipe",
        "slug": "test-recipe",
        "source_year": "1896",
        "source_title": "Test Book",
        "body": (
            "## Ingredients\n\n- one egg\n- one cup milk\n\n"
            "## Directions\n\n1. Beat the egg.\n2. Add the milk.\n"
        ),
    }
    doc = make_doc(row, COMMIT, "ye-old-american:test-recipe", "test-recipe")
    return doc.model_copy(update={"split": split})


def test_chunk_offsets_without_overlap():
    text = "one two three four five"
    chunks = chunk_offsets(whitespace_offsets(text), text, max_tokens=2, overlap=0)
    assert [chunk["text"] for chunk in chunks] == ["one two", "three four", "five"]
    assert [chunk["token_end"] - chunk["token_start"] for chunk in chunks] == [2, 2, 1]


def test_chunk_offsets_with_overlap():
    text = "one two three four"
    chunks = chunk_offsets(whitespace_offsets(text), text, max_tokens=3, overlap=1)
    assert [chunk["text"] for chunk in chunks] == ["one two three", "three four"]


def test_chunk_offsets_rejects_invalid_overlap():
    text = "one two"
    try:
        chunk_offsets(whitespace_offsets(text), text, max_tokens=2, overlap=2)
    except ValueError as exc:
        assert "overlap" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_split_clean_sections_offsets_are_absolute():
    doc = sample_doc()
    sections = split_clean_sections(doc.text_clean)
    content, start = sections["ingredients"]
    assert doc.text_clean[start : start + len(content)] == content
    assert content.startswith("- one egg")


def test_build_passages_has_unique_ids_and_valid_spans():
    doc = sample_doc()
    passages = build_passages(doc, whitespace_offsets, max_tokens=4, overlap=1)
    assert passages
    ids = [passage.passage_id for passage in passages]
    assert len(ids) == len(set(ids))
    for passage in passages:
        assert doc.text_clean[passage.char_start : passage.char_end] == passage.text
        assert passage.token_count <= 4
        assert passage.split == "train"


def test_build_passages_requires_split():
    doc = make_doc(
        {
            "title": "No Split",
            "slug": "no-split",
            "source_year": "1896",
            "body": "## Ingredients\n\n- salt\n## Directions\n\n1. Add salt.\n",
        },
        COMMIT,
        "ye-old-american:no-split",
        "no-split",
    )
    try:
        build_passages(doc, whitespace_offsets)
    except ValueError as exc:
        assert "split" in str(exc)
    else:
        raise AssertionError("expected ValueError")
