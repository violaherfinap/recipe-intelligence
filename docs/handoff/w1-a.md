# Handoff W1-A — Status pekerjaan A

- **Owner:** Vio
- **Branch:** `feat/w1-a-corpus-index`
- **Commit kode:** `0940e32`
- **Tag:** `w1-a-ok`
- **Tanggal:** 2026-11-14
- **Handoff ke:** B

## Ringkasan

A sudah menyelesaikan fondasi data: korpus dibekukan, dokumen dibersihkan,
passage dibentuk, split dibagi, dan dua index retrieval dibuat. B tidak perlu
membangun ulang kecuali ingin memverifikasi atau memakai mesin lain.

## Yang sudah jadi

| Artefak | Path | Angka |
| --- | --- | ---: |
| Dokumen bersih | `data/processed/docs.jsonl` | 5.605 |
| Passage | `data/processed/passages.jsonl` | 11.266 |
| Dokumen yang diindeks | 5.600 kanonik (5 near-duplicate dikeluarkan dari index) | 5.600 |
| Source register | `data/processed/source_register.csv` | 5.605 baris |
| Split | `data/processed/split.json` | train 3.921 / dev 838 / test 846 |
| Manifest | `data/processed/manifest.json` | counts + hashes |
| Hash artefak | `data/processed/manifest.sha256` | 5 file |
| Log dedup | `data/processed/dedup_log.jsonl` | 5 entri |
| Index BM25 | `indexes/bm25/` | 11.266 passage |
| Index dense | `indexes/dense.npy` | 11.266 x 384 |
| Metadata dense | `indexes/dense_meta.parquet` | 11.266 baris |
| Manifest index | `indexes/manifest.json` | model, dim, count |
| Bukti smoke | `docs/w1-a-smoke.md` + `.json` | 10 query |

## Konvensi yang sudah dipakai

- `doc_id = "ye-old-american:<slug>"`; slug duplikat diberi suffix `-2`, `-3`
  (di data ini tidak ada).
- `passage_id = "<doc_id>#<section>#<idx>"`, section `ingredients` atau
  `directions`.
- Passage maksimal **350 token**, overlap **40**, tokenizer
  `BAAI/bge-small-en-v1.5`.
- Split **70/15/15** stratified per `source_year`, seed **42**.
- Dedup hanya **di dalam buku yang sama** (`source_title`), exact hash +
  SimHash (Hamming ≤ 3). Duplikat antar-buku dipertahankan.
- `docs.jsonl` tetap 5.605 baris; 5 near-duplicate dicatat dan dikeluarkan dari
  index, sehingga `docs_indexed = 5.600`.
- BM25: judul resep + teks passage, English stopwords, tanpa stemming,
  `k1=1.5`, `b=0.75`.
- Dense: `BAAI/bge-small-en-v1.5`, 384 dimensi, L2-normalized, dot product.

## Verifikasi cepat

```powershell
.\scripts\tasks.ps1 test
.\scripts\tasks.ps1 smoke
uv run python -m recipe_qa.index.cli smoke --query "clam soup"
Get-Content data/processed/manifest.json
Get-Content data/processed/manifest.sha256
```

Status verifikasi terakhir: **22 unit test lulus**, **ruff bersih**,
**10/10 smoke query mengembalikan hasil**, **5/5 hash manifest cocok**.
Coverage modul corpus: **70%**.

## Yang belum / masih terbuka

- **Q1:** konfirmasi dosen untuk Use Case C (ADR-002) — belum final.
- **Q3:** index tunggal dengan metadata `split` atau index terpisah per split.
- **Q4:** cara B/C/D mengakses file besar yang tidak di-commit.
- **Gate 5.605 vs 5.600:** `docs.jsonl` 5.605, index 5.600 setelah dedup;
  perlu keputusan redaksi gate.
- **Passage 11.266 vs target 15k–20k** dan dense 11.266 vs estimasi ~17k:
  dijelaskan di `ADR-008`.
- **PR `feat/w1-a-corpus-index` → `dev`** belum di-merge.

## Titik mulai B

File yang sudah siap dibaca:

1. `data/processed/passages.jsonl`
2. `data/processed/source_register.csv`
3. `data/processed/split.json`
4. `data/processed/manifest.json`

Kalau perlu mengecek retrieval, index ada di `indexes/bm25/` dan
`indexes/dense.npy`.

Tugas B tidak diulang di sini; ikuti `RENCANA_MINGGUAN.md` blok 2.

## Batas kerja A

- A tidak menulis query, qrels, atau metrik evaluasi.
- Jangan mengubah passage, split, atau hash tanpa menjalankan ulang build dan
  memperbarui `manifest.json` / `manifest.sha256`.
- File besar tidak di-commit. Di mesin lain, rebuild dengan
  `.\scripts\tasks.ps1 corpus` lalu `.\scripts\tasks.ps1 index`.

## Referensi

- `docs/adr/001-corpus.md`
- `docs/adr/002-use-case-mapping.md`
- `docs/adr/008-chunking.md`
- `docs/adr/011-bm25-preprocessing.md`
- `docs/open_questions.md`
- `docs/contribution_matrix.md`
- `docs/handoff_log.md`
