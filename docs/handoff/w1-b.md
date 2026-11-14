# Handoff W1-B — Benchmark 115 query

- **Owner:** B
- **Branch:** `feat/w1-b-benchmark`
- **Commit kode:** `6fde121`
- **Commit docs/freeze:** `fa90e54`
- **Tanggal:** 2026-11-14
- **Handoff ke:** C

## Ringkasan

Benchmark v1 selesai: guideline anotasi, tool anotasi blind, 115 query frozen,
gold candidate test-only, dan verifikasi 25/25 query no-evidence. Query tidak
boleh diubah setelah handoff ini.

## Angka kunci

| Item | Nilai |
| --- | ---: |
| Query | 115 |
| `easy` | 35 (q001–q035) |
| `multi-hop` | 25 (q036–q060) |
| `temporal` | 30 (q061–q090) |
| `no-evidence` | 25 (q091–q115) |
| Gold candidate rows | 90 |
| Gold passage total | 145 |
| No-evidence `absent` | 25/25 |

Distribusi tahun (termasuk no-evidence): 1796=13, 1824=16, 1851=16, 1871=24,
1887=27, 1896=19.

## Rebuild verification

B membangun ulang korpus dan index di mesin sendiri. Semua hash isi file cocok
dengan `data/processed/manifest.sha256` milik A:

| Artefak | Jumlah | Hash cocok |
| --- | ---: | --- |
| `docs.jsonl` | 5.605 | ya |
| `passages.jsonl` | 11.266 | ya |
| `source_register.csv` | 5.605 | ya |
| `split.json` | 5.605 assignment | ya |
| `dedup_log.jsonl` | 5 | ya |

Split: train 3.921 / dev 838 / test 846. Test per tahun: 1796=19, 1824=68,
1851=126, 1871=140, 1887=226, 1896=267. Lima dokumen yang ter-dedup semuanya
train/dev; tidak ada dokumen test yang hilang dari index. Index: BM25 11.266
passage dan dense 11.266 × 384 (`BAAI/bge-small-en-v1.5`).

## Artefak

| Artefak | Path |
| --- | --- |
| Guideline | `benchmark/guidelines.md` |
| Query | `benchmark/queries.jsonl` |
| Hash query | `benchmark/queries.sha256` |
| Gold candidate | `benchmark/gold_candidates.jsonl` |
| No-evidence check | `benchmark/no_evidence_check.csv` |
| Tool anotasi | `tools/annotate.py` |
| Pool builder | `tools/build_pool.py` |
| Validator | `tools/validate_benchmark.py` |
| Schema/validator | `src/recipe_qa/benchmark/` |
| Test | `tests/unit/test_annotate.py`, `test_benchmark_schema.py` |

## Verifikasi

- `uv run python tools/validate_benchmark.py --strict` lulus tanpa warning.
- `uv run pytest -q` lulus (33 test).
- `uv run ruff check src tests tools` lulus.
- Semua gold passage `split=test` dan ada di `passages.jsonl`.
- Semua `multi-hop` punya ≥2 dokumen; semua `temporal` punya ≥2 tahun dan ≥2 buku.
- 25/25 no-evidence: key term tidak ditemukan di seluruh korpus; BM25 top-20
  sudah dibaca dan tidak menjawab.
- Pool v1 diuji: 1.789 kandidat (145 gold, 1.069 dense, 575 negatif).

## Yang belum

- `benchmark/pool_v1.jsonl` (C; gitignored; bangun ulang).
- `benchmark/qrels_c.jsonl` dan metrics library (C).
- `benchmark/qrels_d.jsonl`, κ, adjudikasi, `benchmark/qrels.jsonl`,
  `benchmark/manifest.sha256` (D).
- Q1 approval dosen; Q8 gate 5.605 vs 5.600.

## Instruksi untuk C

Baca `benchmark/guidelines.md` sebelum mulai. Bangun pool test-only:

```powershell
uv run python tools/build_pool.py `
  --queries benchmark/queries.jsonl `
  --gold benchmark/gold_candidates.jsonl `
  --passages data/processed/passages.jsonl `
  --dense-dir indexes `
  --out benchmark/pool_v1.jsonl `
  --meta benchmark/pool_v1_meta.jsonl `
  --split test --dense-k 10 --negatives 5 --seed 42
```

Jangan membuka `benchmark/pool_v1_meta.jsonl` saat anotasi. Anotasi relevance:

```powershell
uv run python tools/annotate.py relevance --annotator C `
  --queries benchmark/queries.jsonl --pool benchmark/pool_v1.jsonl `
  --passages data/processed/passages.jsonl --out benchmark/qrels_c.jsonl
```

Anotasi verdict:

```powershell
uv run python tools/annotate.py verdict --annotator C `
  --queries benchmark/queries.jsonl --qrels benchmark/qrels_c.jsonl `
  --passages data/processed/passages.jsonl `
  --out benchmark/verdict_qrels_c.jsonl
```

Jangan mengubah `benchmark/queries.jsonl`. Saat handoff ke D, pastikan label C
tidak terlihat dan serahkan `qrels_c.jsonl` + `verdict_qrels_c.jsonl`.

## Instruksi untuk D

1. Ulangi relevance dan verdict dengan `--annotator D` ke file `*_d.jsonl`.
2. Jangan membaca file C sebelum pass 2 selesai.
3. Hitung Cohen's κ relevance dan verdict.
4. Adjudikasi konflik, tulis `benchmark/qrels.jsonl` final.
5. Buat `benchmark/manifest.sha256` (hash query, qrels final, daftar doc test).
6. Spot-check 5 query no-evidence.

## Aturan yang tidak boleh dilanggar

- Query frozen; jangan renumber atau mengubah teks.
- Jangan memakai gold test untuk few-shot, prompt, atau training.
- Jangan menilai query sendiri; tool menolak berdasarkan `author`.
- Jangan menambah kandidat pool dari luar pool.
- Jangan mengubah `docs.jsonl`, `passages.jsonl`, `split.json`, atau index A.
- `benchmark/` tidak boleh diakses pipeline agent/training.

## Catatan terbuka

| ID | Isu | Dampak |
| --- | --- | --- |
| Q1 | Approval dosen Use Case C | Benchmark tetap jalan; konfirmasi sebelum freeze final |
| Q3 | Single index + split metadata | Pool dan gold dibatasi `split=test` |
| Q8 | Gate 5.605 vs 5.600 | 5 near-duplicate dikeluarkan dari index; tidak ada doc test yang ter-dedup |

## Verifikasi cepat

```powershell
uv run python tools/validate_benchmark.py --strict
uv run pytest -q
uv run ruff check src tests tools
Get-Content benchmark/queries.sha256
```
