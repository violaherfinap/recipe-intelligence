# Handoff W1-B — Benchmark 115 query

- **Owner:** B
- **Branch:** `feat/w1-b-benchmark`
- **Commit kode:** `6fde121`
- **Tanggal:** 2026-11-14
- **Handoff ke:** C

## Ringkasan

B menyelesaikan benchmark v1: guideline anotasi, tool anotasi blind, 115 query
frozen, gold candidate test-only, dan verifikasi 25/25 query no-evidence.
Query **tidak boleh diubah** setelah handoff ini.

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
| No-evidence terverifikasi | 25/25 `absent` |
| Query hash | lihat `benchmark/queries.sha256` |

Distribusi `as_of`/tahun (termasuk no-evidence): 1796=13, 1824=16, 1851=16,
1871=24, 1887=27, 1896=19.

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
| Schema | `src/recipe_qa/benchmark/schema.py` |
| Validasi | `src/recipe_qa/benchmark/validate.py` |
| Test | `tests/unit/test_annotate.py`, `tests/unit/test_benchmark_schema.py` |
| Bootstrap | `docs/w1-b-bootstrap.md` |

## Yang sudah diverifikasi

- `uv run python tools/validate_benchmark.py --strict` lulus tanpa warning.
- `uv run pytest -q` lulus (33 test).
- `uv run ruff check src tests tools` lulus.
- Semua gold passage `split=test` dan ada di `passages.jsonl`.
- Semua query `multi-hop` punya ≥2 dokumen berbeda; semua query `temporal`
  punya ≥2 tahun dan ≥2 buku.
- 25/25 no-evidence: tidak ada dokumen yang cocok dengan key term; BM25 top-20
  sudah dibaca dan tidak menjawab.
- Pool v1 diuji: 1.789 kandidat, 145 gold, 1.069 dense, 575 negatif.
- Tool anotasi diuji untuk relevance; output append-only dan resume.

## Yang belum

- `benchmark/pool_v1.jsonl` (C; gitignored; bangun ulang).
- `benchmark/qrels_c.jsonl` (C, pass 1).
- Metrics library (C).
- `benchmark/qrels_d.jsonl`, κ, adjudikasi, `benchmark/qrels.jsonl`,
  `benchmark/manifest.sha256` (D).
- Q1 approval dosen; Q8 gate 5.605 vs 5.600.

## Instruksi untuk C

1. Baca `benchmark/guidelines.md` sampai bagian adjudikasi.
2. Bangun pool test-only:

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

3. **Jangan membuka `benchmark/pool_v1_meta.jsonl` saat anotasi.**
4. Anotasi relevance pass 1:

```powershell
uv run python tools/annotate.py relevance `
  --annotator C `
  --queries benchmark/queries.jsonl `
  --pool benchmark/pool_v1.jsonl `
  --passages data/processed/passages.jsonl `
  --out benchmark/qrels_c.jsonl
```

5. Cek progres:

```powershell
uv run python tools/annotate.py status --annotator C --out benchmark/qrels_c.jsonl
```

6. Anotasi verdict:

```powershell
uv run python tools/annotate.py verdict `
  --annotator C `
  --queries benchmark/queries.jsonl `
  --qrels benchmark/qrels_c.jsonl `
  --passages data/processed/passages.jsonl `
  --out benchmark/verdict_qrels_c.jsonl
```

7. Jangan mengubah `benchmark/queries.jsonl`; `doc_version` diisi otomatis
   dari `data/corpus_commit.txt`.
8. Saat handoff ke D: pastikan tool tidak menampilkan label C; serahkan
   `qrels_c.jsonl` dan `verdict_qrels_c.jsonl` tanpa membuka file D.

## Instruksi untuk D

1. Ulangi anotasi relevance dan verdict dengan `--annotator D` dan output
   `qrels_d.jsonl` / `verdict_qrels_d.jsonl`.
2. Jangan membaca file C sebelum pass 2 selesai.
3. Hitung Cohen's κ relevance dan verdict.
4. Adjudikasi konflik, tulis `benchmark/qrels.jsonl` final.
5. Buat `benchmark/manifest.sha256` berisi hash query, qrels final, dan daftar
   `doc_id` test.
6. Verifikasi 5 query no-evidence secara spot-check.

## Aturan yang tidak boleh dilanggar

- Query frozen; jangan renumber atau mengubah teks.
- Jangan memakai gold test untuk few-shot/prompt/training.
- Jangan menilai query sendiri; tool menolak berdasarkan `author`.
- Jangan menambah kandidat pool dari luar pool; catat di notes jika menemukan.
- Jangan mengubah `docs.jsonl`, `passages.jsonl`, `split.json`, atau index A.
- `benchmark/` tidak boleh diakses pipeline agent/training.

## Catatan terbuka

| ID | Isu | Dampak |
| --- | --- | --- |
| Q1 | Approval dosen Use Case C | Benchmark tetap jalan; konfirmasi sebelum freeze final |
| Q3 | Single index + split metadata | Pool dan gold dibatasi `split=test`; evaluasi retrieval sebaiknya filter test |
| Q8 | Gate 5.605 vs 5.600 | 5 dokumen near-duplicate dikeluarkan dari index; tidak ada doc test yang ter-dedup |

## Verifikasi cepat

```powershell
uv run python tools/validate_benchmark.py --strict
uv run pytest -q
uv run ruff check src tests tools
Get-Content benchmark/queries.sha256
```
