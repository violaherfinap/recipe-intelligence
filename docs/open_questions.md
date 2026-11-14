# Open questions

| ID | Question | Owner | Status | Notes |
| --- | --- | --- | --- | --- |
| Q1 | Does the lecturer approve Use Case C (temporal fact-checking) for the historical recipe corpus? | A / whole group | open | Needed before freezing the benchmark in Week 1. See `docs/adr/002-use-case-mapping.md`. |
| Q2 | Is the passage count target 15k–20k, or the measured section-aware count? | A / B | resolved in ADR-008 | `section` chunking (350 tokens, overlap 40) produced **11,266** passages for 5,600 indexed docs. The actual count is recorded in `manifest.json`; the count is not inflated. |
| Q3 | Does “the indexer must not mix splits” mean one index with a `split` metadata field, or separate indexes per split? | A / B | open | Current build keeps one index and stores `split` in the passage and dense metadata; benchmark gold + pool are restricted to `split=test` so qrels stay test-only. |
| Q4 | How do B/C/D access `passages.jsonl` and the indexes if they are not committed? | whole group | resolved | B rebuilt on their machine; all `manifest.sha256` hashes match A. See `docs/handoff/w1-b.md`. |
| Q5 | Are ingredient search and nutrition estimation in scope (Note 1), or deferred? | whole group | open | The recipe corpus has no nutrition data. Adding these features needs a new source and a new metric. |
| Q6 | Should benchmark gold evidence be restricted to `split=test`? | B / C / D | resolved | Yes. All 145 gold passage IDs are test passages; pool v1 is also test-only. |
| Q7 | What is the canonical `scope`/`filter` grammar for queries? | B | resolved | `scope` is human-readable (`year:1896`, `years:1851,1896`); `filter` is machine-readable (`year_min`, `year_max`, `book`, `section`). Documented in `benchmark/guidelines.md`. |
| Q8 | Does Gate 1 require 5.605 or 5.600 indexed documents? | A / whole group | open | 5.605 parsed; 5.600 canonical after 5 near-duplicates; 11.266 passages. All 5 dedup-excluded docs are train/dev, so no test document is missing from the index. |
| Q9 | q048 meminta dua resep 1871 (chocolate + cream), tetapi pool hanya memuat satu; `chocolate-charlotte-russe` tidak ada. Apakah pool perlu di-backfill atau q048 diterima sebagai partial multi-hop? | B / C / D | open | Qrels q048 hanya punya satu label 2 (`chocolate-ice-cream#ingredients#0`). Jangan menambah label 2 pada kandidat yang tidak memenuhi. Catat sebagai pool recall gap di `docs/handoff/w1-c.md`. |

