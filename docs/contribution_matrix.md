# Contribution matrix

| Week | Block | Owner | Planned hours | Actual hours | Scope | Status |
| --- | --- | --- | ---: | ---: | --- | --- |
| 1 | A | Vio | 14 | ≈16 | Corpus, passages, split, BM25 + dense indexes, manifests, tests | done |
| 1 | B | — | 14 | — | Annotation guideline, 115 queries | not started |
| 1 | C | — | 10 | — | Qrels pass 1, metrics library | not started |
| 1 | D | — | 12 | — | Qrels pass 2, κ, adjudication, freeze | not started |

## Block A detail

| Item | Artefact | Owner |
| --- | --- | --- |
| Corpus pin | `data/corpus_commit.txt` | Vio |
| ADR-001 corpus | `docs/adr/001-corpus.md` | Vio |
| ADR-002 use case | `docs/adr/002-use-case-mapping.md` | Vio |
| ADR-008 chunking | `docs/adr/008-chunking.md` | Vio |
| Parser | `src/recipe_qa/corpus/build.py` | Vio |
| Docs + passages + split | `data/processed/` | Vio |
| BM25 + dense index | `indexes/` | Vio |
| Tests | `tests/unit/` | Vio |
| Handoff | `docs/handoff_log.md` | Vio |
