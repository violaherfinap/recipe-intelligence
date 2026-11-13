from __future__ import annotations

import pytest

from recipe_qa.corpus.build import (
    deduplicate,
    make_doc,
    parse_recipes,
    parse_sections,
)
from recipe_qa.corpus.schema import Doc

COMMIT = "a" * 40


def sample_row(**overrides):
    row = {
        "title": "Tomato Soup",
        "slug": "tomato-soup",
        "collection": "ye-old-american",
        "culture": "american-historical",
        "author": "Fannie Merritt Farmer",
        "source_title": "The Boston Cooking-School Cook Book",
        "source_url": "https://www.gutenberg.org/ebooks/65061",
        "source_year": "1896",
        "license": "public-domain",
        "body": (
            "## Ingredients\n\n- two eggs\n- a quart of milk\n\n"
            "## Directions\n\n1. Beat the eggs.\n2. Add the milk and cook.\n\n"
            "## Provenance\n\nThis text is in the public domain.\n"
        ),
    }
    row.update(overrides)
    return row


def test_parse_sections_keeps_only_known_headings():
    sections = parse_sections(sample_row()["body"])
    assert set(sections) == {"ingredients", "directions", "provenance"}
    assert "- two eggs" in sections["ingredients"]


def test_make_doc_casts_year_and_excludes_provenance():
    doc = make_doc(sample_row(), COMMIT, "ye-old-american:tomato-soup", "tomato-soup")
    assert doc.source_year == 1896
    assert doc.doc_id == "ye-old-american:tomato-soup"
    assert "## Ingredients" in doc.text_clean
    assert "## Directions" in doc.text_clean
    assert "Provenance" not in doc.text_clean
    assert doc.sections["ingredients"][0] == "- two eggs"
    assert len(doc.sha256) == 64


def test_make_doc_rejects_missing_title():
    with pytest.raises(ValueError, match="missing title"):
        make_doc(sample_row(title=""), COMMIT, "ye-old-american:no-title", "no-title")


def test_make_doc_rejects_missing_sections():
    with pytest.raises(ValueError, match="missing Ingredients"):
        make_doc(
            sample_row(body="just some text without headings"),
            COMMIT,
            "ye-old-american:no-sections",
            "no-sections",
        )


def test_parse_recipes_suffixes_duplicate_slugs():
    docs, errors = parse_recipes([sample_row(), sample_row()], COMMIT)
    assert errors == []
    assert [doc.doc_id for doc in docs] == [
        "ye-old-american:tomato-soup",
        "ye-old-american:tomato-soup-2",
    ]


def test_deduplicate_removes_exact_duplicates():
    first = make_doc(sample_row(), COMMIT, "ye-old-american:tomato-soup", "tomato-soup")
    second = first.model_copy(update={"doc_id": "ye-old-american:tomato-soup-copy"})
    kept, removed = deduplicate([first, second])
    assert len(kept) == 1
    assert removed[0]["kind"] == "exact"
    assert removed[0]["duplicate_of"] == first.doc_id


def test_doc_model_forbids_unknown_fields():
    with pytest.raises(ValueError):
        Doc(
            doc_id="d",
            title="t",
            slug="s",
            collection="c",
            source_year=1900,
            sections={},
            text_clean="text",
            sha256="a" * 64,
            split="train",
            unknown="x",
        )
