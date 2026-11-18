from __future__ import annotations

from recipe_qa.retrieval.filters import normalize_filter, passage_matches_filter


def passage(**overrides):
    row = {
        "source_year": 1896,
        "source_title": "The Boston Cooking-School Cook Book",
        "section": "directions",
    }
    row.update(overrides)
    return row


def test_year_filter():
    spec = {"year_min": 1890, "year_max": 1900}
    assert passage_matches_filter(passage(), spec)
    assert not passage_matches_filter(passage(source_year=1871), spec)


def test_book_filter_is_case_insensitive():
    spec = {"book": "boston cooking"}
    assert passage_matches_filter(passage(), spec)
    assert not passage_matches_filter(passage(source_title="American Cookery"), spec)


def test_section_filter_matches_hierarchical_steps():
    assert passage_matches_filter(passage(section="step"), {"section": "directions"})
    assert passage_matches_filter(passage(section="summary"), {"section": "ingredients"})
    assert not passage_matches_filter(passage(section="step"), {"section": "ingredients"})


def test_normalize_filter_drops_none():
    assert normalize_filter({"year_min": None, "book": "x"}) == {"book": "x"}
    assert normalize_filter(None) is None
