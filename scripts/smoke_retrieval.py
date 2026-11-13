"""Run a small retrieval smoke suite and write the evidence report.

Usage:
    uv run python scripts/smoke_retrieval.py
"""

from __future__ import annotations

import json
from pathlib import Path

from recipe_qa.corpus.build import read_jsonl
from recipe_qa.index.build import bm25_search, dense_search

QUERIES = [
    "How long is tomato soup cooked?",
    "How do you make bread pudding?",
    "What ingredients are in apple pie?",
    "How much flour for a pound cake?",
    "Which recipe uses nutmeg and mace?",
    "How do you roast a goose?",
    "How do you pickle peaches?",
    "How many eggs for corn meal puffs?",
    "What does the 1824 cookbook say about peaches in brandy?",
    "How do you make clam soup?",
]

OUT_PATH = Path("docs/w1-a-smoke.json")


def main() -> int:
    passages_path = Path("data/processed/passages.jsonl")
    indexes_dir = Path("indexes")
    passages = list(read_jsonl(passages_path))
    if not passages:
        raise SystemExit(f"no passages in {passages_path}")

    results = []
    for query in QUERIES:
        bm25_hits = bm25_search(indexes_dir, passages, query, k=5)
        dense_hits = dense_search(indexes_dir, query, k=5)
        results.append(
            {
                "query": query,
                "bm25_top": bm25_hits[:3],
                "dense_top": dense_hits[:3],
            }
        )
        bm25_top = bm25_hits[0]["doc_id"] if bm25_hits else "-"
        dense_top = dense_hits[0]["doc_id"] if dense_hits else "-"
        print(f"{query}\n  bm25  -> {bm25_top}\n  dense -> {dense_top}")

    OUT_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT_PATH} ({len(results)} queries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
