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
