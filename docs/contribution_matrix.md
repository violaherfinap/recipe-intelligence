# Contribution matrix

| Week | Block | Owner | Planned hours | Actual hours | Scope | Status |
| --- | --- | --- | ---: | ---: | --- | --- |
| 1 | A | Vio | 14 | ≈16 | Corpus, passages, split, BM25 + dense indexes, manifests, tests | done |
| 1 | B | B | 14 | — | Guideline, tool anotasi blind, 115 query, no-evidence check | done |
| 1 | C | — | 10 | — | Qrels pass 1, metrics library | not started |
| 1 | D | — | 12 | — | Qrels pass 2, κ, adjudication, freeze | not started |

## Block A detail

| Item | Artefact | Owner |
| --- | --- | --- |
| Corpus pin | `data/corpus_commit.txt` | Vio |
| ADR-001 corpus | `docs/adr/001-corpus.md` | Vio |
| ADR-002 use case | `docs/adr/002-use-case-mapping.md` | Vio |
| ADR-008 chunking | `docs/adr/008-chunking.md` | Vio |
| ADR-011 BM25 preprocessing | `docs/adr/011-bm25-preprocessing.md` | Vio |
| Retrieval smoke (10 queries) | `docs/w1-a-smoke.md` | Vio |
| Parser | `src/recipe_qa/corpus/build.py` | Vio |
| Docs + passages + split | `data/processed/` | Vio |
| BM25 + dense index | `indexes/` | Vio |
| Tests | `tests/unit/` | Vio |
| Handoff | `docs/handoff_log.md` | Vio |

## Block B detail

| Item | Artefact | Owner |
| --- | --- | --- |
| Annotation guideline | `benchmark/guidelines.md` | B |
| 115 frozen queries | `benchmark/queries.jsonl`, `queries.sha256` | B |
| Gold evidence candidates | `benchmark/gold_candidates.jsonl` | B |
| No-evidence verification | `benchmark/no_evidence_check.csv` | B |
| Blind annotation tool | `tools/annotate.py` | B |
| Pool builder | `tools/build_pool.py` | B |
| Query validator | `tools/validate_benchmark.py` | B |
| Benchmark schema/validators | `src/recipe_qa/benchmark/` | B |
| Tests | `tests/unit/test_annotate.py`, `test_benchmark_schema.py` | B |
| Bootstrap verification | `docs/w1-b-bootstrap.md` | B |
| Handoff | `docs/handoff/w1-b.md` | B |
