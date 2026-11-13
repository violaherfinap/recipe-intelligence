# ADR-001 — Corpus selection and licence

- **Status:** accepted
- **Date:** 2026-11-14
- **Owner:** Orang A (Vio)
- **Related:** `RENCANA_LENGKAP.md` §3, `spek.md` §3

## Context

The project needs a real, legally usable corpus of at least 300 documents on a
single topic, with temporal variation, so that evidence-grounded claims and
`as_of` questions can be evaluated. The corpus must preserve source metadata
(author, title, year, URL, licence) and be reproducible from a pinned commit.

## Decision

Use the **`ye-old-american`** collection from
[`AdamBouhmad/open-recipe-archive`](https://github.com/AdamBouhmad/open-recipe-archive):

- **5,605 recipes** in one collection, one JSONL file.
- **Public domain** (`license = "public-domain"`, repository Unlicense).
- Source years: 1796, 1824, 1851, 1871, 1887, 1896.
- Fields available: `title`, `slug`, `collection`, `collection_name`, `culture`,
  `author`, `body`, `source_title`, `source_url`, `source_year`, `license`,
  `tags`, `export_date`.
- Pinned commit is stored in `data/corpus_commit.txt` and in
  `data/processed/manifest.json`.

## Rationale

- 5,605 documents comfortably exceed the 300-document minimum.
- Six publication years support temporal and conflicting-source questions.
- Public domain removes licensing risk; source URLs and hashes are retained.
- One collection keeps the topic narrow enough for a 4-week project.

## Consequences

- The text is historical English, with archaic units and transcription noise.
  This is part of the task; the system must cite the source rather than
  modernise it silently.
- `source_year` arrives as a string and must be cast to an integer.
- The corpus has no `date` field; `export_date` exists but is not the
  publication year.
- Modern nutrition and food-safety advice are **not** supported by this corpus.
  Questions about them should abstain with `not_specified`.
- Exact duplicates within the collection: 0. SimHash found **5 within-book
  near-duplicates** (same `source_title`); they are logged in
  `data/processed/dedup_log.jsonl` and excluded from the retrieval index.
  Duplicates across different books are kept, as required by the plan.
  `docs.jsonl` still contains all 5,605 rows; `docs_indexed` is 5,600.

## Alternatives considered

| Alternative | Why not chosen |
| --- | --- |
| 330 documents from news/official sources | Smaller, licensing and scraping burden; no ready public-domain pack |
| Other collections in the same archive | Would mix topics and languages; the project needs one topic |
| Modern recipe sites | Copyright and terms-of-service risk |

## Verification

```powershell
Get-Content data/corpus_commit.txt
(Get-Content data/raw/open-recipe-archive/collections/ye-old-american/recipes.jsonl).Count
Get-Content data/processed/manifest.json
```
