# Open questions

| ID | Question | Owner | Status | Notes |
| --- | --- | --- | --- | --- |
| Q1 | Does the lecturer approve Use Case C (temporal fact-checking) for the historical recipe corpus? | A / whole group | open | Needed before freezing the benchmark in Week 1. See `docs/adr/002-use-case-mapping.md`. |
| Q2 | Is the passage count target 15k–20k, or the measured section-aware count? | A / B | resolved in ADR-008 | `section` chunking (350 tokens, overlap 40) produced **11,266** passages for 5,600 indexed docs. The actual count is recorded in `manifest.json`; the count is not inflated. |
| Q3 | Does “the indexer must not mix splits” mean one index with a `split` metadata field, or separate indexes per split? | A / B | open | Current build keeps one index and stores `split` in the passage and dense metadata; training/few-shot must never use test passages. |
| Q4 | How do B/C/D access `passages.jsonl` and the indexes if they are not committed? | whole group | open | Options: same laptop, shared drive, or rebuild with `make corpus && make index`. Document the choice in the handoff. |
| Q5 | Are ingredient search and nutrition estimation in scope (Note 1), or deferred? | whole group | open | The recipe corpus has no nutrition data. Adding these features needs a new source and a new metric. |
