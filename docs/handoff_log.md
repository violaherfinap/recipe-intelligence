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

**Artefak:** `benchmark/queries.jsonl`, `gold_candidates.jsonl`, `no_evidence_check.csv`, `guidelines.md`, `queries.sha256`, `tools/annotate.py`, `tools/build_pool.py`, `tools/validate_benchmark.py`, `src/recipe_qa/benchmark/`, `tests/unit/test_annotate.py`, `tests/unit/test_benchmark_schema.py`, `docs/w1-b-bootstrap.md`.
