# Handoff log

> Three lines per block: what is done, what is not done, what the next owner
> must do. Keep this file short; details live in the linked artefacts.

## Week 1 — Block A (Orang A / Vio) — 2026-11-14

- **Selesai:** 5,605 resep di-parse ke `docs.jsonl`; 5,600 dokumen kanonik menjadi 11,266 passage section-aware (350 token, overlap 40); split 70/15/15 seed 42 (train 3,921 / dev 838 / test 846); manifest + SHA-256; index BM25 (title + stopwords, lihat ADR-011) dan dense 384d; smoke 10 query di `docs/w1-a-smoke.json`; 22 unit test lulus; ruff bersih.
- **Belum:** konfirmasi dosen untuk Use Case C (ADR-002); keputusan tim soal akses file besar ke B/C/D; verifikasi apakah index harus dipisah per split (Q3).
- **Berikutnya untuk B:** baca `data/processed/passages.jsonl`, `data/processed/source_register.csv`, dan `data/processed/split.json`; tulis 115 query tanpa memakai passage `test` untuk few-shot/training.

**Commit kode:** `0940e32` — tag `w1-a-ok` menunjuk ke commit evidence terakhir di branch ini.

**Status lengkap:** `docs/handoff/w1-a.md`.

**Artefak:** `data/processed/docs.jsonl` (5,605 baris),
`data/processed/passages.jsonl` (11,266 baris),
`data/processed/source_register.csv` (5,605 baris),
`data/processed/split.json`, `data/processed/manifest.json`,
`data/processed/manifest.sha256`, `data/processed/dedup_log.jsonl` (5 entri),
`indexes/bm25/`, `indexes/dense.npy` (11,266 x 384),
`indexes/dense_meta.parquet`, `indexes/manifest.json`,
`docs/w1-a-smoke.json`, `docs/w1-a-smoke.md`.

**Catatan dedup:** 5 near-duplicate dalam buku yang sama dicatat dan
dikeluarkan dari index; `docs.jsonl` tetap 5,605 baris. Duplikat antar-buku
dipertahankan. Lihat `docs/adr/001-corpus.md` dan `docs/adr/008-chunking.md`.

**Catatan akses:** file besar tidak di-commit. B harus memakai mesin yang sama,
shared drive, atau rebuild. Langkah lengkapnya ada di `docs/handoff/w1-a.md`
bagian **Rebuild di laptop lain**.

## Week 1 — Block B (Orang B) — 2026-11-14

- **Selesai:** benchmark v1 freeze — 115 query (35 easy / 25 multi-hop / 30 temporal / 25 no-evidence), guideline anotasi, tool anotasi blind + pool builder + validator, gold candidate test-only, verifikasi no-evidence 25/25, hash query di `benchmark/queries.sha256`; rebuild korpus/index identik dengan hash A; 33 unit test lulus; ruff bersih.
- **Belum:** pool v1 + qrels pass 1 + metrics library (C); qrels pass 2, κ, adjudikasi, dan `benchmark/manifest.sha256` (D); konfirmasi Q1 (approval dosen) dan Q8 (gate 5.605 vs 5.600).
- **Berikutnya untuk C:** baca `benchmark/guidelines.md`; bangun pool test-only dengan `tools/build_pool.py`; anotasi relevance pass 1 ke `benchmark/qrels_c.jsonl`; jangan mengubah query dan jangan membuka `pool_v1_meta.jsonl`.

**Commit kode:** `6fde121` di branch `feat/w1-b-benchmark` (belum di-merge ke `dev`).

**Status lengkap:** `docs/handoff/w1-b.md`.

**Artefak:** `benchmark/queries.jsonl`, `gold_candidates.jsonl`, `no_evidence_check.csv`, `guidelines.md`, `queries.sha256`, `tools/annotate.py`, `tools/build_pool.py`, `tools/validate_benchmark.py`, `src/recipe_qa/benchmark/`, `tests/unit/test_annotate.py`, `tests/unit/test_benchmark_schema.py`.

## Week 1 — Block C (Orang C) — 2026-11-14

- **Selesai:** pool test-only 1.789 kandidat; qrels relevance pass 1 final 1.789 baris (1.608×0 / 12×1 / 169×2) untuk 115 query; review q009–q115 1.666 baris dengan 3 override; 25 query no-evidence semuanya 0; metrics library (Recall@k, nDCG@k, MRR@k, macro-F1, citation precision/recall, unsupported claim rate); batch verdict tool (`dump`/`fill`/`review`); verdict C pass 1 145/145 klaim (144 SUPPORTED, 0 REFUTED, 1 NOT_ENOUGH_EVIDENCE); actual 11,47 jam; 75 unit test lulus; ruff bersih.
- **Belum:** q048 pool gap (`chocolate-charlotte-russe` tidak ada di pool, hanya satu label 2; q048 c2 = NOT_ENOUGH_EVIDENCE); verdict D pass 2.
- **Berikutnya untuk D:** relevance pass 2 blind ke `benchmark/qrels_d.jsonl` tanpa membuka `qrels_c.jsonl`/`qrels_c_reviewed.jsonl`/`benchmark/work/w1-c-audit-2026-11-14/`; verdict C sudah selesai, lanjut verdict pass 2 blind dengan `tools/review_verdicts.py` (`dump`/`fill`/`review`, `--annotator D`); hitung κ dan adjudikasi.

**Commit kode:** `79dd9fb` di branch `feat/w1-c-qrels-metrics`.

**Status lengkap:** `docs/handoff/w1-c.md`.

**Artefak final:** `benchmark/qrels_c.jsonl` (1.789 baris), `benchmark/qrels_c.sha256`, `benchmark/verdict_qrels_c.jsonl` (145 klaim), `tools/review_preannotation.py`, `tools/finalize_qrels.py`, `tools/review_verdicts.py`, `src/recipe_qa/benchmark/review.py`, `src/recipe_qa/benchmark/finalize.py`, `src/recipe_qa/benchmark/verdict_review.py`, `src/recipe_qa/eval/metrics/`, `tests/unit/test_review.py`, `test_finalize.py`, `test_verdict_review.py`, `test_metrics_retrieval.py`, `test_metrics_claims.py`.

**Arsip lokal (tidak di-commit):** `benchmark/work/w1-c-audit-2026-11-14/` berisi draft LLM, reviewed, backup manual, prompt/answer verdict, pool, dan `SHA256SUMS.txt`.

## Week 1 — Block D (Orang D) — 2026-11-18

- **Selesai:** relevance pass 2 1.789 baris; verdict pass 2 145/145 klaim; κ relevance 0.9607 dan verdict 0.4983; 13 konflik relevance + 1 konflik verdict diadjudikasi; annotation log 14 baris; benchmark frozen (`benchmark/qrels.jsonl`, `benchmark/verdict_qrels.jsonl`, `benchmark/test_docs.txt`, `benchmark/manifest.sha256`); `validate_benchmark.py --strict` valid; 100 test lulus; ruff bersih.
- **Belum:** merge D ke `dev`; actual hours tidak dilacak; q048 tetap partial multi-hop (hanya satu relevance-2); pass 2 D AI-assisted, bukan human inter-annotator murni.
- **Berikutnya:** review commit D, merge ke `dev`, lalu pakai benchmark frozen untuk Week 2; pertimbangkan human re-annotation jika rubrik membutuhkan human κ, dan backfill q048 jika B/C setuju.
- **Catatan:** relevance dan verdict D disusun dengan bantuan AI; lihat deviasi di `reports/week1.md`.

**Commit kode:** `f0a436d` di branch `feat/w1-d-pass2`; sudah di-push ke `origin/feat/w1-d-pass2`.

**Status lengkap:** `reports/week1.md`.

**Artefak final:** `benchmark/qrels_d.jsonl`, `benchmark/verdict_qrels_d.jsonl`, `benchmark/kappa.json`, `benchmark/conflicts.jsonl`, `benchmark/adjudication.jsonl`, `benchmark/annotation_log.csv`, `benchmark/qrels.jsonl`, `benchmark/verdict_qrels.jsonl`, `benchmark/test_docs.txt`, `benchmark/manifest.sha256`, `tools/compute_agreement.py`, `tools/adjudicate.py`, `tools/finalize_benchmark.py`, `tests/unit/test_agreement.py`, `tests/unit/test_adjudication.py`, `tests/unit/test_answer_sheet.py`, `reports/week1.md`.

## Week 1 — Revisi v1.1 (Orang A / Vio) — 2026-11-19

- **Selesai:** adjudikasi ulang 14 konflik oleh A, blind ke keputusan lama — 12 sama, 2 berubah (`q083` x2, `0` → `1`); sensus 183 item non-zero — 181 dipertahankan, 2 dikoreksi; klarifikasi §6 (relevance per passage/per klaim) ditulis di `benchmark/guidelines.md` v1.1; artefak baru `benchmark/adjudication_v1_1.jsonl`, `benchmark/audit_v1_1.jsonl`, `benchmark/audit_v1_1_summary.json`, `benchmark/changes_v1_1.jsonl`, `tools/audit_qrels.py`; manifest di-regenerate; `validate_benchmark.py --strict` valid.
- **Alasan:** D tidak yakin dengan pass 2-nya sendiri. Guideline §13 meminta adjudikasi pihak ketiga, tetapi D yang memutus konflik C vs D, dan 12 dari 13 keputusan jatuh ke label C. κ pool penuh (0.9607) juga menyesatkan karena 1.606 dari 1.789 item bernilai `0`.
- **Belum:** dua item yang berubah belum di-spot-check manusia; pass ketiga penuh (1.789 item) tidak dilakukan; qrels v2 dengan 3 anotator belum dimulai; `benchmark/kappa.json` masih berisi κ C vs D pada pool penuh, belum κ subset 183 item (0.6333).
- **Berikutnya:** B/C/D meninjau klarifikasi §6. Kalau setuju, pakai qrels v1.1 untuk evaluasi Week 2; kalau tidak, kembalikan label satu per satu lewat `benchmark/changes_v1_1.jsonl`. Untuk qrels v2, anotasi dilakukan 3 orang (C, D, A) dengan Fleiss κ + adjudikasi sisa seri.

**Status lengkap:** bagian **v1.1** di `reports/week1.md`.

**Commit:** tag `benchmark-v1.1` (lokal; belum di-push).

**Artefak v1.1:** `benchmark/guidelines.md`, `benchmark/adjudication_v1_1.jsonl`, `benchmark/audit_v1_1.jsonl`, `benchmark/audit_v1_1_summary.json`, `benchmark/changes_v1_1.jsonl`, `benchmark/qrels.jsonl`, `benchmark/manifest.sha256`, `tools/audit_qrels.py`, `reports/week1.md`.

## Week 2 — Block A (Orang A / Vio) — 2026-11-19

- **Selesai:** B2 (dense + fixed chunk + top-5) dan B3 (BM25 + dense + RRF + reranker + filter) berjalan end-to-end sampai JSON answer; A1 tiga index (section 11.266, fixed 5.738, hierarchical 37.754 passage); A2 empat config retrieval; prompt registry B0/B1 + config equality; 120 unit test lulus; ruff bersih. Smoke: B0/B2/B3 schema-valid; A2 10 query hybrid+rerank Recall@10 0.80 vs dense 0.45.
- **Belum:** evaluasi penuh B2/B3/A2 dan Gate 2 (itu B/C/D); reranker q001 perlu diperiksa; B2 belum memakai filter/title; kualitas jawaban generator belum diaudit manusia; config B1 vs B2 berbeda juga di `prompt.few_shot` (deviasi pragmatis, lihat handoff).
- **Berikutnya untuk B:** jalankan smoke B0/B1, evaluasi B2/B3 di dev, evaluasi A2 dengan **qrels v1.1**, lalu isi `reports/b2b3_dev.md` dan `reports/a2_dev.md`. C mengevaluasi A1; D menyiapkan qrels v2 + error taxonomy.

**Branch:** `feat/w2-a-retrieval` (w2-a). **Commit:** `bf77125`. **Status lengkap:** `docs/handoff/w2-a.md`.

**Status merge:** branch ini **belum di-merge** ke `dev`/`main`; B harus pull branch ini atau merge ke `dev` dulu.

**Config equality:** test `tests/unit/test_config_equality.py` mengizinkan `prompt.few_shot` pada B1 vs B2; lihat test sebelum mengubah config.

**Artefak:** `src/recipe_qa/retrieval/`, `src/recipe_qa/pipeline/`, `src/recipe_qa/generation/`, `configs/b0.yaml`–`configs/b3.yaml`, `configs/retrieval_*.yaml`, `prompts/registry/structured_v1.yaml`, `prompts/examples.jsonl`, `indexes/fixed/`, `indexes/hierarchical/`, `data/processed/passages_fixed.jsonl`, `data/processed/passages_hierarchical.jsonl`.

## Week 2 — Block B (Orang B) — 2026-11-19

- **Selesai:** smoke B0/B1 20 query (B0 20/20 schema valid, B1 18/20); A2 penuh 115 query dengan qrels v1.1 (dense 0,3019; BM25 0,3917; hybrid 0,4324; hybrid+rerank+filter 0,7120; rerank tanpa filter 0,4102); evaluasi B2/B3 (B2 passage 0 secara struktural, doc recall 0,2889; B3 passage 0,7120, doc 0,7833); pool v2 2.237 kandidat / 448 baru / median 19 per query; tool `eval_retrieval.py`, `run_config.py`, `build_pool_v2.py`, coverage metrics; guidelines v1.2; laporan A2 dan B2/B3; 127 test lulus, ruff bersih, validator lulus.
- **Belum:** Gate 2 passage-level (B2 butuh qrels fixed); qrels v2 dan anotasi 448 kandidat baru ada di C/D; dev query set terpisah (Q10); keputusan 2 vs 3 anotator (Q12).
- **Berikutnya untuk C:** seed `benchmark/qrels.jsonl` ke `qrels_v2_c.jsonl`, lalu anotasi 448 kandidat baru dari `benchmark/pool_v2.jsonl` dengan `--passages data/processed/passages.jsonl data/processed/passages_fixed.jsonl`; jangan membuka `pool_v2_meta.jsonl`.

**Branch:** `feat/w2-b-eval-pool`. **Status lengkap:** `docs/handoff/w2-b.md`.

**Gate 2:** qrels v2 belum; Recall@10 B3 > B2 lulus di doc-level (0,7833 > 0,2889), passage-level menunggu qrels v2.

**Artefak:** `reports/a2_dev.md`, `reports/b2b3_dev.md`, `benchmark/pool_v2.jsonl`, `benchmark/pool_v2.sha256`, `benchmark/guidelines.md` v1.2, `tools/eval_retrieval.py`, `tools/run_config.py`, `tools/build_pool_v2.py`, `tools/summarize_runs.py`, `src/recipe_qa/benchmark/pool_v2.py`, `src/recipe_qa/eval/metrics/coverage.py`, `artifacts/runs/` (lokal).

## Week 2 - Block C (Orang C) - 2026-11-22

- **Selesai:** qrels v2 pass 1 - 448/448 kandidat baru direview (LLM preannotation + 100% human review, 5 override), `qrels_v2_c.jsonl` 2.237 baris/115 query (SHA-256 `6523382a21df...`); A1 tiga chunking dengan dense-only - doc recall@10 fixed 0,3889, section 0,3500, hierarchical 0,5778; section passage R@10 0,3019; `reports/a1_dev.md`; 130 test lulus, ruff bersih, validator v1.1 lulus.
- **Belum:** audit provenance verdict C 145 klaim; Q12 (2 vs 3 anotator) belum diputuskan; q048 warning multi-hop 3 relevance-2 dalam 1 dokumen diterima sebagai known pool gap; qrels v2 belum diadjudikasi D.
- **Berikutnya untuk D:** jangan buka `qrels_v2_c.jsonl`/reviewed/draft sebelum pass 2; seed `benchmark/qrels.jsonl` v1.1 ke `qrels_v2_d.jsonl`, anotasi 448 kandidat baru blind, hitung agreement, adjudikasi, freeze qrels v2, lalu rerun A1/B2/B3 dan tutup Gate 2.

**Branch:** `feat/w2-c-qrels-v2-a1`. **Status lengkap:** `docs/handoff/w2-c.md`.

**Artefak:** `benchmark/qrels_v2_c.jsonl` (commit; jangan dibuka D sebelum pass 2), `benchmark/qrels_v2_c.sha256`, `benchmark/work/w2-c/` (lokal), `reports/a1_dev.md`, `configs/a1_*.yaml`, `tools/a1_context_stats.py`, `artifacts/runs/a1_*.json` (lokal), `tools/finalize_qrels_v2.py`, `tools/export_preannotation.py`, `tools/import_preannotation.py`, `src/recipe_qa/benchmark/preannotation.py`, `tests/unit/test_preannotation.py`.

## Week 2 - Block D (Orang D) - 2026-11-24

- **Selesai:** qrels v2 pass 2 - 448/448 kandidat baru; A final 448/448; C/D kappa 0.9629 (6 konflik); Fleiss A/C/D 0.9223; 1 tie q013 diputuskan final 1; verdict C/D kappa 0.4983, q048 final REFUTED; qrels v2 frozen 2.237 baris (label 0=1955, 1=38, 2=244), verdict 145 (SUPPORTED=144, REFUTED=1); manifest dan test_docs di-regenerate; B3 R@10 0.5369 vs B2 0.1515; Gate 2 lulus; error taxonomy final 162 kegagalan/83 query (E1=134, E2=6, E3=14, E5=8; E4=0; E6-E8 NE); spot-check 5 no-evidence; A1 v2 tiga mode; 139 test lulus, ruff bersih, validator strict valid.
- **Belum:** E6-E8 sengaja Not Evaluated; E3/E5 hanya sampel 24 query generation; A1 hierarchical passage-level tidak valid secara struktural; audit provenance verdict C (145 klaim) masih C-owned; branch belum di-push.
- **Berikutnya untuk A:** pakai qrels v2 dan `artifacts/runs/retrieval_b3_v2.json` untuk test B0-B3; jangan tuning pada 115 query test; jangan ubah query/qrels tanpa versi baru.
- **Catatan:** `benchmark/pool_v1.jsonl` hanya 1.789 key; finalisasi wajib memakai `benchmark/pool_v2.jsonl`. Keputusan relevance lama di `benchmark/adjudication.jsonl` tidak dipakai lagi setelah majority A/C/D; keputusan aktif ada di `benchmark/adjudication_v2.jsonl`.

**Branch:** `feat/w2-d-finalize-qrels-v2`. **Commit:** `0497de8` (qrels/tooling) dan `c674d28` (taxonomy/A1 v2); commit dokumentasi adalah HEAD branch.

**Artefak final:** `benchmark/qrels.jsonl` (SHA-256 `8ed07e8e...`), `benchmark/verdict_qrels.jsonl` (SHA-256 `b86d1d39...`), `benchmark/manifest.sha256`, `benchmark/archive/`, `benchmark/kappa_v2.json`, `benchmark/adjudication_v2.jsonl`, `benchmark/no_evidence_spotcheck_v2.csv`, `error_analysis.csv`, `docs/error_taxonomy.md`, `reports/a1_dev.md`, `reports/b2b3_dev.md`, `artifacts/runs/retrieval_b2_v2.json`, `artifacts/runs/retrieval_b3_v2.json` (lokal), `docs/handoff/w2-d.md`.

## Week 3 - P0 Grounding Gate (Orang D) - 2026-11-25

- **Selesai:** prioritas P0 error taxonomy - verifier NLI per klaim (`cross-encoder/nli-deberta-v3-base`, threshold 0.5), claim splitting, repair JSON, kebijakan drop/abstain, metadata verifikasi di pipeline; sufficiency gate diimplementasikan tetapi dimatikan karena belum terkalibrasi; config `a3_verify` (verifier-only) dan `a3_verify_suff` (eksperimen); 161 test lulus, ruff bersih, validator v2 valid.
- **Belum:** kalibrasi NLI/τ di dev (dev set belum ada, Q10); A3 penuh 115 query; sufficiency masih over-abstain (easy 17/35, multi-hop 23/25, temporal 27/30); residual `q071` (entity swap) butuh planner; `keep_refuted=false` membuang klaim REFUTED.
- **Berikutnya untuk A/B:** buat dev query+label, bekukan baseline B0-B3 test seed 1, lalu kalibrasi threshold dan lanjut planner/E1.
- **Bukti sample:** 6/6 no-evidence abstain (baseline 0/6); 24 query generation audit -> 21/22 error diblokir, `q021` benar dipertahankan, `q060` NE jadi abstain `format_error`; latency p50 29,2 s / p95 55,2 s.

**Artefak:** `src/recipe_qa/verify/`, `src/recipe_qa/generation/generate.py`, `src/recipe_qa/pipeline/common.py`, `tools/run_config.py`, `configs/a3_verify.yaml`, `configs/a3_verify_suff.yaml`, `tests/unit/test_verify_*.py`, `tests/unit/test_generation_repair.py`, `tests/unit/test_pipeline_verify.py`, `reports/a3_verify_dev.md`, `docs/handoff/w3-notes.md`, `artifacts/runs/a3_verify_*` (lokal).

## Week 3 - Block A (Orang A) - 2026-11-25

- **Selesai:** baseline B0-B3 test seed 1 lengkap 115 query/config (`reports/b0_b3_test_s1.md`); planner rule + LLM (`planner_v1`) dengan validasi JSON dan fallback rule; retry maks. 2 berbasis `retry.min_sufficiency`; integrasi B4 (`planner -> retrieve -> retry -> sufficiency -> generate -> verify`) dengan metadata `plan`/`retry`; `configs/b4.yaml`, `configs/b4_calib.yaml`; tool kalibrasi τ (`tools/calibrate_sufficiency.py`); 188 test lulus, ruff bersih.
- **Baseline:** B0 schema 107/115 (p50 14,7 s), B1 108/115 (13,9 s), B2 113/115 (20,9 s), B3 103/115 (20,9 s, p95 39,3 s). Artefak di `artifacts/runs/b0-test-s1/`..`b3-test-s1/`.
- **B4 smoke:** `q061` dan `q036` berjalan; plan/retry terisi; keduanya abstain (satu `format_error`). `q021` menghasilkan jawaban valid, 1 klaim SUPPORTED, tidak abstain. Planner LLM 0.5B sering tidak layak; fallback rule-based dipakai. Ini smoke integrasi, bukan evaluasi.
- **Belum:** dev query+label (Q10) sehingga τ/NLI belum dikalibrasi; B4 20 query dev; A3/A4 penuh; B4 test seed 1 (D); kualitas planner LLM dan abstain B4 belum dievaluasi.
- **Status A-only:** langkah 1-5 selesai; langkah 6-8 menunggu dev set frozen dari B/C/D. A tidak menulis query/label dev.
- **Berikutnya untuk B/D:** pakai `reports/b0_b3_test_s1.md` sebagai baseline; siapkan dev set; kalibrasi τ/NLI di dev; jalankan B4 test hanya setelah konfigurasi dibekukan. Jangan tuning di 115 query test.

**Branch:** `feat/w3-p0-grounding` (`9edf55b`) -> `feat/w3-a-planner-b4` (`92d1452`, follow-up `53939a1`). **Status:** belum di-push/merge.

**Artefak:** `src/recipe_qa/pipeline/{planner,retry,b4}.py`, `src/recipe_qa/eval/sufficiency_calibration.py`, `tools/calibrate_sufficiency.py`, `configs/b4.yaml`, `configs/b4_calib.yaml`, `prompts/registry/planner_v1.yaml`, `reports/b0_b3_test_s1.md`, `tests/unit/test_{planner,retry,pipeline_planner_retry,sufficiency_calibration}.py`, `artifacts/runs/b0-test-s1/`..`b4-smoke/` (lokal).

## Week 3 - Master Handoff A/B/C/D - 2026-11-26

- **Dokumen lengkap:** `docs/handoff/w3.md`.
- **Mapping:** A = Lois, B = Anin, C = Dhea, D = Vio.
- **Keputusan:** Lois adjudikasi dev; Dhea mengirim adapter via Google Drive; tugas A tetap dikerjakan Lois.
- **Status:** base `w3-base-a2` siap (instruksi branch ada di handoff); dev set belum ada; tag `w3-dev-frozen` dan `w3-config-frozen` belum dibuat.
- **Urutan:** Lois base -> Anin query dev -> Dhea/Vio label -> Lois adjudikasi/freeze -> Lois tau + Anin NLI -> config freeze -> Vio test/A3/A6 -> Gate 3.
- **Peringatan:** orang keempat (Vio/D) wajib melapor ke grup Lois/Anin/Vio setelah test B4/B5, A3/A4/A6, dan 3 seed selesai; jangan menunggu Gate 3.

## Week 3 - Block B (Orang B) - 2026-11-26

- **Selesai:** split query 65 train / 50 test (cluster-aware, 0 gold-doc overlap; easy 20/15, multi-hop 14/11, temporal 17/13, no-evidence 14/11) di `benchmark/query_split.json` + `queries_train.jsonl` / `queries_test.jsonl`; tool `tools/split_queries.py`; 6 unit test baru (termasuk reproduksibilitas split); 194 test lulus, ruff bersih. Dev 24 query dibatalkan karena requirement baru.
- **Belum:** split belum di-review/di-tag A; baseline B0-B3 masih dihitung pada 115 query; `reports/verifier_calibration.md`, `reports/b4_dev.md`, `verify/citations.py`, `verify/temporal.py`, `pipeline/abstain.py` belum ada.
- **Berikutnya untuk A:** review + tag split, jalankan ulang B0-B3 pada 50 test, revisi `docs/handoff/w3.md` §5; untuk C/D: tidak ada branch label dev, lanjut LoRA/prep.

**Branch:** `feat/w3-b-dev` (dari `w3-base-a2`). **Artefak:** `benchmark/query_split.json`, `benchmark/queries_train.jsonl` (SHA-256 `9d000d51...`), `benchmark/queries_test.jsonl` (SHA-256 `08f4e3fa...`), `tools/split_queries.py`, `src/recipe_qa/benchmark/query_split.py`, `tests/unit/test_query_split.py`, `docs/handoff/w3-b.md`, `benchmark/guidelines.md` v2.1.

## Week 3 - Block A - Revisi split 65/50 - 2026-11-26

- **Keputusan:** dev 24 query dibatalkan. 115 query beku dipecah menjadi 65 train (kalibrasi) dan 50 test (angka final) pada level query, cluster-aware (0 gold-doc overlap, seed 42). Artefak: `benchmark/query_split.json`, `benchmark/queries_train.jsonl` (65), `benchmark/queries_test.jsonl` (50).
- **Dampak A:** baseline B0-B3 115 query menjadi development evaluation; A harus merge split, review + tag `w3-query-split`, rerun baseline di test-50, kalibrasi tau di train-65, lalu config freeze (`w3-config-frozen`) sebelum B4 test-50.
- **Guardrail baru:** kalibrasi hanya train-65; test-50 hanya angka final; passage gold milik 65 query train tetap `split=test` sehingga tidak boleh dipakai sebagai teks training LoRA.
- **Handoff diperbarui:** `docs/handoff/w3.md`, `docs/handoff/w3-notes.md`. Dev set, branch label dev, dan tag `w3-dev-frozen` dihapus dari alur.

## Week 3 - Block A - Calibration dan config freeze - 2026-11-26

- **Selesai:** baseline B0-B3 test-50 (`reports/b0_b3_test50_s1.md`; B0/B1 schema 0,94, B2 1,00, B3 0,86); kalibrasi tau train-65 (`reports/sufficiency_calibration_train65.md`; tau 0,17, balanced accuracy 0,8305); config freeze `configs/b4.yaml` dengan `premise_context: true`, `abstain.sufficiency: true` (tau 0,17), citation/temporal gate aktif; `configs/b4_calib.yaml` dipin ke setting pra-freeze; tag `w3-config-frozen` (commit `a6b7a26`); B4 final test-50 (`reports/b4_test50.md`; schema 49/50, abstain 39/50, p50 43,4 s, p95 82,0 s); 197 test lulus, ruff bersih.
- **Belum:** B5/A4 menunggu adapter C; A3/A6 menunggu D; `reports/b4_train65.md` milik B; false confident verdict `q099` (no-evidence) dan residual temporal `q062` belum diperbaiki.
- **Berikutnya untuk B:** tulis `reports/b4_train65.md` dari run train-65 tanpa run duplikat. **Untuk D:** mulai A3/A6 dari `w3-config-frozen`; test-50 B4 sudah tersedia. **Untuk C:** lanjut LoRA/B5; test-50 B5 setelah adapter siap.

**Branch:** `feat/w3-a-calibration`. **Artefak:** `reports/b0_b3_test50_s1.md`, `reports/sufficiency_calibration_train65.md`, `reports/b4_test50.md`, `configs/b4.yaml`, `configs/b4_calib.yaml`, `tests/unit/test_config_equality.py`, `docs/handoff/w3.md`.

## Week 3 - Catatan post-freeze untuk B/C/D - 2026-11-26

- **Selesai:** `docs/handoff/w3.md` §16 dan ringkasan di `docs/handoff/w3-notes.md`; berisi guardrail post-freeze, tugas B/C/D, temuan B4 test-50 (`q099`, `q062`, abstain 78%), dan keputusan terbuka.
- **Belum:** keputusan sumber `reports/b4_train65.md`, hash split di manifest, dan ACC Q13.
- **Berikutnya:** B/C/D fetch tag `w3-config-frozen` dan branch dari situ; jangan memakai `w3-base-a3` sebagai base kode.

## Week 3 - Block A - Sync tag, integration, artefak test-50 - 2026-11-28

- **Selesai:** tag `w3-config-frozen` di-push & terverifikasi (`ca35609` -> commit `a6b7a26`); `configs/b4.yaml` SHA-256 `57339e7b6b4a9d06630f26d7485d80d7fc2e5469c1fe5ab35831b240029c6a44`; `feat/w3-integration` sinkron ke `b8a50e7` (frozen config + `reports/b4_test50.md`); artefak `b4-test50-s1` + `SHA256SUMS.txt` dibagikan via Drive (link di `docs/handoff/w3.md` section 16.0); B4 final train-65 dijalankan (`artifacts/runs/b4-train65-s1/`; 65 query, schema 61/65, abstain 48/65; `results.jsonl` SHA-256 `8db0f7dc3132dacceb1ee7dbdaf429e92a06e329617e60024d49cb99d28a299c`).
- **Belum:** upload `b4-train65-s1` ke Drive; `reports/b4_train65.md` (B); keputusan bug `verify_claims`/`sufficiency` (fix + re-freeze `w3-config-frozen-r2` vs known limitation).
- **Berikutnya:** A upload `b4-train65-s1` -> B tulis `b4_train65.md`; B audit q099/q062 dari artefak test-50.
