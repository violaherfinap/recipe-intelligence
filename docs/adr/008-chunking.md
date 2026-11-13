# ADR-008 — Section-aware chunking and passage granularity

- **Status:** accepted
- **Date:** 2026-11-14
- **Owner:** Orang A (Vio)
- **Related:** `RENCANA_LENGKAP.md` §7.1, `RENCANA_MINGGUAN.md` Week 1 block A, `docs/open_questions.md` Q2

## Context

Retrieval operates on passages, not whole recipes. The plan proposes three
chunking modes (`fixed`, `section`, `hierarchical`) and estimates 15k–20k
passages for the full corpus. The measured corpus is smaller than that estimate:
the median recipe body is 102 words and the longest is 1,614 words.

## Decision

Use **section-aware chunking** as the default:

- Split each recipe on `## Ingredients` and `## Directions`.
- Chunk each section into windows of at most **350 tokens** with **40 tokens**
  overlap, using the `BAAI/bge-small-en-v1.5` tokenizer so chunk size matches
  the embedding model.
- Preserve source text and record absolute `char_start` / `char_end` offsets in
  `text_clean`.
- Passage id: `<doc_id>#<section>#<idx>`.

## Measured result

| Item | Value |
| --- | ---: |
| Documents in `docs.jsonl` | 5,605 |
| Documents indexed (canonical) | 5,600 |
| Within-book near-duplicates logged | 5 |
| Passages | **11,266** |
| Max tokens per passage | 350 |
| Min tokens per passage | 3 |
| Ingredient passages | 5,601 |
| Direction passages | 5,665 |

The plan's 15k–20k estimate does not match this corpus at 350-token section
chunking. The actual count is reported in `data/processed/manifest.json` and
must not be inflated.

## Consequences

- A1 (fixed vs section vs hierarchical) will compare this mode against `fixed`
  (expected ~5.7k passages) and `hierarchical` (built later).
- Smaller passages keep citations precise; short recipes still produce one
  passage per section.
- The 5 within-book near-duplicates are logged in `dedup_log.jsonl` and excluded
  from the index; `docs.jsonl` keeps all 5,605 rows so the corpus inventory
  remains complete. Cross-book duplicates are kept, as required by the plan.

## Alternatives considered

| Alternative | Why not the default |
| --- | --- |
| Fixed 350-token windows | Ignores section structure; ~5.7k passages |
| Per-line / per-step passages | ~68k passages, too fragmented and expensive |
| Smaller windows (150 tokens) | Only ~11.9k passages; fragments short recipes without benefit |
