from __future__ import annotations

from recipe_qa.corpus.build import read_jsonl, write_jsonl
from recipe_qa.index.build import (
    bm25_search,
    build_bm25,
    tokenize,
    tokenize_for_index,
)


def make_passages(path):
    rows = [
        {
            "passage_id": "ye-old-american:tomato-soup#directions#0",
            "doc_id": "ye-old-american:tomato-soup",
            "section": "directions",
            "idx": 0,
            "text": "Cook tomatoes, water, peppercorns twenty minutes; strain.",
            "char_start": 0,
            "char_end": 56,
            "token_count": 8,
            "source_year": 1896,
            "source_title": "The Boston Cooking-School Cook Book",
            "split": "train",
        },
        {
            "passage_id": "ye-old-american:bread-pudding#directions#0",
            "doc_id": "ye-old-american:bread-pudding",
            "section": "directions",
            "idx": 0,
            "text": "Boil a quart of rich milk and pour it over the bread.",
            "char_start": 0,
            "char_end": 55,
            "token_count": 13,
            "source_year": 1851,
            "source_title": "Miss Leslie's Complete Cookery",
            "split": "train",
        },
        {
            "passage_id": "ye-old-american:apple-pudding#directions#0",
            "doc_id": "ye-old-american:apple-pudding",
            "section": "directions",
            "idx": 0,
            "text": "Bake the apples in a deep dish for half an hour.",
            "char_start": 0,
            "char_end": 49,
            "token_count": 11,
            "source_year": 1851,
            "source_title": "Miss Leslie's Complete Cookery",
            "split": "train",
        },
    ]
    write_jsonl(path, rows)


def test_tokenize_is_lowercase_and_keeps_apostrophes():
    assert tokenize("Don't boil the TOMATOES!") == ["don't", "boil", "the", "tomatoes"]


def test_tokenize_for_index_removes_stopwords():
    assert tokenize_for_index("How do you make clam soup?") == ["clam", "soup"]


def test_bm25_returns_the_matching_passage(tmp_path):
    passages_path = tmp_path / "passages.jsonl"
    make_passages(passages_path)
    out_dir = tmp_path / "indexes"

    meta = build_bm25(passages_path, out_dir)
    assert meta["passage_count"] == 3
    assert (out_dir / "bm25" / "meta.json").exists()

    passages = list(read_jsonl(passages_path))
    hits = bm25_search(out_dir, passages, "tomatoes", k=2)
    assert hits
    assert hits[0]["doc_id"] == "ye-old-american:tomato-soup"
    assert hits[0]["score"] > 0


def test_bm25_index_includes_recipe_title(tmp_path):
    passages_path = tmp_path / "passages.jsonl"
    write_jsonl(
        passages_path,
        [
            {
                "passage_id": "ye-old-american:clam-soup#directions#0",
                "doc_id": "ye-old-american:clam-soup",
                "section": "directions",
                "idx": 0,
                "text": "Clean and pick over clams, reserve liquor.",
                "char_start": 0,
                "char_end": 41,
                "token_count": 7,
                "source_year": 1896,
                "source_title": "Test Book",
                "split": "train",
            },
            {
                "passage_id": "ye-old-american:bread#directions#0",
                "doc_id": "ye-old-american:bread",
                "section": "directions",
                "idx": 0,
                "text": "Boil milk and pour it over bread.",
                "char_start": 0,
                "char_end": 33,
                "token_count": 7,
                "source_year": 1896,
                "source_title": "Test Book",
                "split": "train",
            },
        ],
    )
    write_jsonl(
        tmp_path / "docs.jsonl",
        [
            {"doc_id": "ye-old-american:clam-soup", "title": "Clam Soup"},
            {"doc_id": "ye-old-american:bread", "title": "Bread Pudding"},
        ],
    )

    build_bm25(passages_path, tmp_path / "indexes")
    passages = list(read_jsonl(passages_path))
    hits = bm25_search(tmp_path / "indexes", passages, "clam soup", k=2)
    assert hits[0]["doc_id"] == "ye-old-american:clam-soup"
