# Contribution matrix

| Week | Block | Owner | Planned hours | Actual hours | Scope | Status |
| --- | --- | --- | ---: | ---: | --- | --- |
| 1 | A | Vio | 14 | ≈16 | Corpus, passages, split, BM25 + dense indexes, manifests, tests | done |
| 1 | B | B | 14 | — | Guideline, tool anotasi blind, 115 query, no-evidence check | done |
| 1 | C | C | 10 | 11.47 | Qrels pass 1 (1.789), metrics library | done |
| 1 | D | D | 12 | — (tidak dilacak) | Qrels pass 2, κ, adjudication, freeze | done |
| 1 | A (revisi v1.1) | Vio | 3 | ≈3 | Adjudikasi ulang 14 konflik, audit 183 item, klarifikasi §6, qrels v1.1 | done |
| 2 | A | Vio | 14 | ≈10 | B2/B3, A1 chunking, A2 retrieval configs, prompt registry B0/B1 | done |
| 2 | B | B | 13 | ≈13 | Smoke B0/B1, evaluasi A2/B2/B3, pool v2, laporan | done |
| 2 | C | C | 10 | ≈10 | Qrels v2 pass 1, evaluasi A1, handoff | done |
| 2 | D | D | 13 | ≈16 (termasuk closeout) | Qrels v2 pass 2, adjudikasi, Gate 2, taxonomy, A1 v2, handoff | done |
| 3 | C | Dhea | 13 | — | Dataset LoRA, training adapter, evaluasi B5 | in progress |

`≈` berarti estimasi jam kerja, bukan timer otomatis. Nilai D mencakup
2-3 jam closeout qrels v2, A1 v2, dan dokumentasi.

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

## Revisi v1.1 detail (Week 1, dikerjakan A)

| Item | Artefak | Owner |
| --- | --- | --- |
| Klarifikasi aturan relevance | `benchmark/guidelines.md` (§6, §13, §16) | Vio |
| Adjudikasi ulang 14 konflik | `benchmark/adjudication_v1_1.jsonl` | Vio |
| Sensus 183 item non-zero | `benchmark/audit_v1_1.jsonl`, `benchmark/audit_v1_1_summary.json` | Vio |
| Perubahan label | `benchmark/changes_v1_1.jsonl` (2 item) | Vio |
| Tool audit | `tools/audit_qrels.py` | Vio |
| Freeze ulang | `benchmark/manifest.sha256` | Vio |
| Laporan | `reports/week1.md` bagian v1.1 | Vio |

## Block A - Week 2 detail

| Item | Artefak | Owner |
| --- | --- | --- |
| B2 pipeline + config | `src/recipe_qa/pipeline/b2.py`, `configs/b2.yaml` | Vio |
| B3 pipeline + config | `src/recipe_qa/pipeline/b3.py`, `configs/b3.yaml` | Vio |
| Retrieval primitives | `src/recipe_qa/retrieval/` | Vio |
| A1 section index | `indexes/` (11.266 passage) | Vio |
| A1 fixed index | `indexes/fixed/` (5.738 passage) | Vio |
| A1 hierarchical index | `indexes/hierarchical/` (37.754 passage) | Vio |
| A2 retrieval configs | `configs/retrieval_*.yaml` | Vio |
| A2 runner | `src/recipe_qa/retrieval/cli.py` | Vio |
| B0/B1 configs + prompt | `configs/b0.yaml`, `b1.yaml`, `prompts/registry/structured_v1.yaml` | Vio |
| Generation + parser | `src/recipe_qa/generation/` | Vio |
| Config schema | `src/recipe_qa/config.py`, `configs/schema.py` | Vio |
| Tests | `tests/unit/test_chunking_modes.py`, `test_fusion.py`, `test_filters.py`, `test_config_equality.py`, `test_prompt.py`, `test_generation_parse.py` | Vio |
| Handoff | `docs/handoff/w2-a.md` | Vio |

## Block B - Week 2 detail

| Item | Artefak | Owner |
| --- | --- | --- |
| Retrieval evaluation tool | `tools/eval_retrieval.py`, `src/recipe_qa/eval/metrics/coverage.py` | B |
| Batch smoke tool | `tools/run_config.py` | B |
| Smoke B0/B1 | `artifacts/runs/smoke/b0/`, `artifacts/runs/smoke/b1/` (lokal) | B |
| A2 evaluation | `reports/a2_dev.md`, `artifacts/runs/a2_*_full.json` | B |
| B2/B3 evaluation | `reports/b2b3_dev.md`, `artifacts/runs/retrieval_b2_full.json`, `retrieval_b3_full.json` | B |
| Diagnostic rerank tanpa filter | `configs/retrieval_hybrid_rerank_nofilter.yaml`, `artifacts/runs/a2_hybrid_rerank_nofilter_full.json` | B |
| Pool v2 builder | `tools/build_pool_v2.py`, `src/recipe_qa/benchmark/pool_v2.py` | B |
| Pool v2 blinded | `benchmark/pool_v2.jsonl`, `benchmark/pool_v2.sha256` | B |
| Pool v2 provenance | `benchmark/pool_v2_meta.jsonl` (tidak di-commit) | B |
| Multi-passage annotation | `tools/annotate.py`, `src/recipe_qa/benchmark/validate.py` | B |
| Guidelines v1.2 | `benchmark/guidelines.md` | B |
| Tests | `tests/unit/test_coverage_metrics.py`, `test_pool_v2.py` | B |
| Handoff | `docs/handoff/w2-b.md` | B |

## Block C - Week 2 detail

| Item | Artefak | Owner |
| --- | --- | --- |
| Qrels v2 pass 1 | `benchmark/qrels_v2_c.jsonl` (2.237 baris), `benchmark/qrels_v2_c.sha256` | C |
| Draft/review lokal | `benchmark/work/w2-c/` (gitignored) | C |
| A1 evaluation v1.1 | `reports/a1_dev.md`, `configs/a1_*.yaml`, `tools/a1_context_stats.py` | C |
| Run A1 v1.1 | `artifacts/runs/a1_*_full.json` (lokal) | C |
| Handoff | `docs/handoff/w2-c.md` | C |

## Block D - Week 2 detail

| Item | Artefak | Owner |
| --- | --- | --- |
| Qrels v2 pass 2 | `benchmark/qrels_v2_d.jsonl` (lokal, gitignored) | D |
| Qrels A v2 | `benchmark/qrels_v2_a.jsonl` (lokal, gitignored) | D |
| Agreement v2 | `benchmark/kappa_v2.json` | D |
| Keputusan adjudikasi v2 | `benchmark/adjudication_v2.jsonl` | D |
| Log konflik + annotation log | `benchmark/conflicts.jsonl`, `benchmark/annotation_log.csv` | D |
| Final qrels/verdict v2 | `benchmark/qrels.jsonl`, `benchmark/verdict_qrels.jsonl`, `benchmark/manifest.sha256` | D |
| Spot-check no-evidence | `benchmark/no_evidence_spotcheck_v2.csv` | D |
| Error taxonomy | `docs/error_taxonomy.md`, `error_analysis.csv`, `tools/analyze_retrieval_errors.py` | D |
| A1 v2 rerun | `reports/a1_dev.md`, `artifacts/runs/a1_context_stats_v2.json` (lokal) | D |
| Gate 2 report | `reports/b2b3_dev.md`, `artifacts/runs/retrieval_b2_v2.json`, `retrieval_b3_v2.json` (lokal) | D |
| Handoff | `docs/handoff/w2-d.md` | D |

## Block C - Week 3 detail (in progress)

| Item | Artefak | Owner |
| --- | --- | --- |
| Dataset builder | `train/build_dataset.py`, `src/recipe_qa/training/dataset.py` | Dhea |
| Dataset 700 contoh + hash + audit | `train/dataset.jsonl`, `train/dataset.sha256`, `train/dataset_audit.json` | Dhea |
| Test kebocoran dataset | `tests/unit/test_lora_dataset.py` | Dhea |
| Dukungan adapter | `src/recipe_qa/config.py`, `src/recipe_qa/generation/generate.py` | Dhea |
| Config B5 | `configs/b5.yaml` | Dhea |
| Training LoRA | `train/lora_config.yaml`, `train/train_lora.py` | Dhea |
| Adapter + log | `train/adapter/`, `train/logs/` (lokal, gitignored) | Dhea |
| Evaluasi B5 | `reports/b5_train65.md`, `reports/b5_test50.md` | Dhea |
| Handoff | `docs/handoff/w3-c.md` | Dhea |
