from __future__ import annotations

from recipe_qa.corpus.build import read_jsonl, write_jsonl
from recipe_qa.index.build import bm25_search, build_bm25, tokenize


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
