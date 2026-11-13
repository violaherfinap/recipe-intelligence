# ADR-011 — BM25 preprocessing: title in index and stopword removal

- **Status:** accepted
- **Date:** 2026-11-14
- **Owner:** Orang A (Vio)
- **Related:** `RENCANA_LENGKAP.md` §7.2, §8.1; A2 ablation

## Context

The plan specifies BM25 tokenisation as lowercase with regex `[a-z0-9']+` and no
stemming by default. Two practical issues appeared in the first smoke run:

1. The passage text contains only the `Ingredients` / `Directions` sections.
   The recipe **title** is not in the passage, so a query such as `clam soup`
   does not match a recipe whose body says `clams`.
2. Natural-language questions contain many function words. Without removal,
   `How do you make clam soup?` ranked `how to make tea` first because
   `how ... make` dominated the score.

## Decision

For the default BM25 index:

- Index `recipe title + " " + passage text`; the citation text remains the
  passage text only.
- Remove English stopwords (NLTK list plus `make` / `made` / `making`) before
  indexing and querying.
- Keep the plan's rule: **no stemming by default**. Porter stemming remains an
  A2 variant.
- Record `title_in_index`, `stopwords`, `k1`, and `b` in
  `indexes/bm25/meta.json`.

## Consequences

- `clam soup`, `corn meal puffs`, `peaches in brandy`, and `roast goose` now
  return the expected recipe in the top-1 BM25 slot.
- Natural-language questions are less dominated by `how/do/you/make`.
- BM25 remains a lexical baseline; the dense index still wins on paraphrases
  (for example, `tomato soup` → `tomato-winter-soup`).
- A2 must compare the raw variant (no stopwords) and the Porter variant against
  this default, using the same qrels.

## Verification

```powershell
uv run python -m recipe_qa.index.cli bm25
uv run python scripts/smoke_retrieval.py
Get-Content indexes/bm25/meta.json
```

See `docs/w1-a-smoke.md` for the 10-query smoke table.
