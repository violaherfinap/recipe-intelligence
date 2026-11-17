# Contribution matrix

| Week | Block | Owner | Planned hours | Actual hours | Scope | Status |
| --- | --- | --- | ---: | ---: | --- | --- |
| 1 | A | Vio | 14 | ≈16 | Corpus, passages, split, BM25 + dense indexes, manifests, tests | done |
| 1 | B | B | 14 | — | Guideline, tool anotasi blind, 115 query, no-evidence check | done |
| 1 | C | C | 10 | 11.47 | Qrels pass 1 (1.789), metrics library | done |
| 1 | D | D | 12 | — (tidak dilacak) | Qrels pass 2, κ, adjudication, freeze | done |

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
| Bootstrap verification | `docs/handoff/w1-b.md` | B |
| Handoff | `docs/handoff/w1-b.md` | B |

## Block C detail

| Item | Artefact | Owner |
| --- | --- | --- |
| Final relevance qrels | `benchmark/qrels_c.jsonl` (1.789 baris) | C |
| Verdict pass 1 | `benchmark/verdict_qrels_c.jsonl` (145 klaim) | C |
| Reviewed draft q009–q115 | `benchmark/qrels_c_reviewed.jsonl` (1.666 baris; arsip lokal) | C |
| Preannotation draft | `benchmark/qrels_c_draft.jsonl` (1.666 baris; arsip lokal, LLM-assisted) | C |
| Manual qrels backup | `benchmark/qrels_c_pass1_2026-11-14.jsonl` (123 baris; arsip lokal) | C |
| Local audit archive | `benchmark/work/w1-c-audit-2026-11-14/` (gitignored) | C |
| Review CLI | `tools/review_preannotation.py` | C |
| Finalize + validation CLI | `tools/finalize_qrels.py` | C |
| Batch verdict CLI (`dump`/`fill`/`review`) | `tools/review_verdicts.py` | C |
| Review/finalize helpers | `src/recipe_qa/benchmark/review.py`, `finalize.py` | C |
| Verdict parser | `src/recipe_qa/benchmark/verdict_review.py` | C |
| Retrieval metrics | `src/recipe_qa/eval/metrics/retrieval.py` | C |
| Claim metrics | `src/recipe_qa/eval/metrics/claims.py` | C |
| Tests | `tests/unit/test_review.py`, `test_finalize.py`, `test_verdict_review.py`, `test_metrics_*.py` | C |
| Handoff | `docs/handoff/w1-c.md` | C |

## Block D detail

| Item | Artefak | Owner |
| --- | --- | --- |
| Relevance pass 2 | `benchmark/qrels_d.jsonl` (1.789 baris) | D |
| Verdict pass 2 | `benchmark/verdict_qrels_d.jsonl` (145 klaim) | D |
| Agreement C/D | `benchmark/kappa.json` | D |
| Konflik + adjudikasi | `benchmark/conflicts.jsonl`, `benchmark/adjudication.jsonl` | D |
| Annotation log konflik | `benchmark/annotation_log.csv` (14 baris) | D |
| Final frozen qrels | `benchmark/qrels.jsonl` (1.789 baris) | D |
| Final frozen verdict | `benchmark/verdict_qrels.jsonl` (145 klaim) | D |
| Test doc list | `benchmark/test_docs.txt` (846 dokumen) | D |
| Manifest final | `benchmark/manifest.sha256` | D |
| Tool agreement/adjudikasi/finalisasi | `tools/compute_agreement.py`, `tools/adjudicate.py`, `tools/finalize_benchmark.py` | D |
| Laporan | `reports/week1.md` | D |
| Tests | `tests/unit/test_agreement.py`, `test_adjudication.py`, `test_answer_sheet.py` | D |
