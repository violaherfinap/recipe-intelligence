from __future__ import annotations

from collections import Counter

from recipe_qa.corpus.schema import Doc
from recipe_qa.corpus.split import assign_splits, split_summary


def make_doc(index: int, year: int) -> Doc:
    return Doc(
        doc_id=f"ye-old-american:recipe-{index:03d}",
        title=f"Recipe {index}",
        slug=f"recipe-{index:03d}",
        collection="ye-old-american",
        source_year=year,
        sections={},
        text_clean=f"recipe number {index}",
        sha256="a" * 64,
        split=None,
    )


def make_docs() -> list[Doc]:
    years = [1796, 1824, 1851, 1871, 1887, 1896]
    return [make_doc(index, years[index % len(years)]) for index in range(120)]


def test_split_covers_every_doc_once():
    docs = make_docs()
    assignments = assign_splits(docs, seed=42)
    assert set(assignments) == {doc.doc_id for doc in docs}
    assert set(assignments.values()) <= {"train", "dev", "test"}


def test_split_is_stratified_by_year():
    docs = make_docs()
    assignments = assign_splits(docs, seed=42)
    summary = split_summary(assignments, docs, seed=42)
    for year, counts in summary["by_year"].items():
        assert counts["train"] > 0, year
        assert counts["dev"] > 0, year
        assert counts["test"] > 0, year


def test_split_counts_are_roughly_70_15_15():
    docs = make_docs()
    assignments = assign_splits(docs, seed=42)
    counts = Counter(assignments.values())
    total = len(docs)
    assert abs(counts["train"] / total - 0.70) < 0.05
    assert abs(counts["dev"] / total - 0.15) < 0.05
    assert abs(counts["test"] / total - 0.15) < 0.05


def test_split_is_deterministic():
    docs = make_docs()
    first = assign_splits(docs, seed=42)
    second = assign_splits(list(reversed(docs)), seed=42)
    assert first == second


def test_split_summary_counts_match_assignments():
    docs = make_docs()
    assignments = assign_splits(docs, seed=42)
    summary = split_summary(assignments, docs, seed=42)
    assert sum(summary["counts"].values()) == len(docs)
