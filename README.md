# Recipe Intelligence

Tanya-jawab berbasis bukti atas **5.605 resep historis Amerika** dari
[`open-recipe-archive`](https://github.com/AdamBouhmad/open-recipe-archive)
(koleksi `ye-old-american`, public domain). Proyek ini mempelajari apakah
retrieval, verifikasi, fine-tuning parameter-efficient, dan penggunaan tool
yang dijaga dapat meningkatkan jawaban faktual dengan sitasi dibanding LLM biasa.

Repo ini mengikuti `RENCANA_LENGKAP.md` dan `RENCANA_MINGGUAN.md`.
Week 1 blok A membangun fondasi data: korpus, passage, split, dan index retrieval.
Indeks dokumentasi: [`docs/README.md`](docs/README.md).

## Kebutuhan

- Windows 11 (atau Linux/macOS), Python 3.11
- [`uv`](https://docs.astral.sh/uv/) untuk manajemen environment
- Ruang disk sekitar 2 GB untuk environment dan index

## Mulai cepat

```powershell
# Setup environment sekali saja
uv sync --extra dev

# Unduh korpus dan checkout commit yang sudah dipin
git clone https://github.com/AdamBouhmad/open-recipe-archive.git data/raw/open-recipe-archive
$sha = Get-Content data/corpus_commit.txt
git -C data/raw/open-recipe-archive checkout $sha

# Bangun docs.jsonl, passages.jsonl, source_register.csv, split.json, manifest
uv run python -m recipe_qa.corpus.cli build

# Bangun index BM25 dan dense
uv run python -m recipe_qa.index.cli all

# Verifikasi
uv run pytest
uv run ruff check src tests
uv run python -m recipe_qa.index.cli smoke --query "tomato soup"
```

Di Windows, `make` opsional. Target yang sama tersedia lewat
`.\scripts\tasks.ps1`:

```powershell
.\scripts\tasks.ps1 setup
.\scripts\tasks.ps1 corpus
.\scripts\tasks.ps1 index
.\scripts\tasks.ps1 test
.\scripts\tasks.ps1 smoke
```

Linux/macOS bisa memakai `Makefile` langsung.

## Struktur data

| Path | Isi |
| --- | --- |
| `data/raw/open-recipe-archive/` | Clone korpus mentah (gitignored) |
| `data/corpus_commit.txt` | Commit SHA korpus yang sudah dipin |
| `data/processed/docs.jsonl` | Satu dokumen bersih per resep |
| `data/processed/passages.jsonl` | Passage retrieval section-aware |
| `data/processed/source_register.csv` | Sumber, lisensi, hash, dan split per dokumen |
| `data/processed/split.json` | Split 70/15/15 deterministik (seed 42) |
| `data/processed/manifest.json` | Korpus, chunking, jumlah, dan hash file |
| `data/processed/manifest.sha256` | SHA-256 artefak yang dibekukan |
| `indexes/bm25/` | Index BM25 dan metadata |
| `indexes/dense.npy` | Embedding BGE yang sudah L2-normalized (N x 384) |
| `indexes/dense_meta.parquet` | Metadata untuk menyelaraskan baris matriks dense |
| `indexes/manifest.json` | Model embedding, dimensi, jumlah, dan hash korpus |

File besar (`docs.jsonl`, `passages.jsonl`, index) tidak di-commit. Bangun ulang
dengan perintah di atas; manifest dan file split tetap di-commit supaya hasil
build bisa diverifikasi.

## Status proyek

- **Week 1, blok A:** selesai — 5.605 resep dibersihkan, 11.266 passage
  (5.600 dokumen kanonik), split 70/15/15 (seed 42), index BM25 dan dense 384d,
  22 unit test lulus, ruff bersih.
- **Week 1, blok B:** selesai — guideline anotasi, tool anotasi blind, 115 query
  (35 easy / 25 multi-hop / 30 temporal / 25 no-evidence), gold evidence
  test-only, verifikasi no-evidence 25/25, hash query di
  `benchmark/queries.sha256`.
- **Week 1, blok C:** selesai — qrels relevance pass 1 (1.789 baris), verdict
  pass 1 (145/145 klaim), metrics library, 75 unit test lulus, ruff bersih,
  actual 11,47 jam.
- **Handoff A → B:** lihat [`docs/handoff/w1-a.md`](docs/handoff/w1-a.md).
- **Handoff B → C:** lihat [`docs/handoff/w1-b.md`](docs/handoff/w1-b.md).
- **Handoff C → D:** lihat [`docs/handoff/w1-c.md`](docs/handoff/w1-c.md).
- **Laporan Week 1:** lihat [`reports/week1.md`](reports/week1.md).
- **Week 1, blok D:** selesai — relevance pass 2 (1.789 baris), verdict pass 2
  (145 klaim), κ relevance 0.9607 / verdict 0.4983, 14 konflik diadjudikasi,
  annotation log 14 baris, benchmark frozen, 100 test lulus, ruff bersih.
  Laporan: [`reports/week1.md`](reports/week1.md).

## Benchmark

```powershell
# validasi 115 query + gold + no-evidence
uv run python tools/validate_benchmark.py --strict

# bangun pool anotasi test-only (C)
uv run python tools/build_pool.py

# anotasi relevance (C atau D)
uv run python tools/annotate.py relevance --annotator C --out benchmark/qrels_c.jsonl

# hitung agreement, adjudikasi, lalu freeze
uv run python tools/compute_agreement.py
uv run python tools/adjudicate.py status
uv run python tools/finalize_benchmark.py --dry-run
uv run python tools/finalize_benchmark.py
uv run python tools/validate_benchmark.py --strict
```

Aturan anotasi ada di [`benchmark/guidelines.md`](benchmark/guidelines.md).
File `benchmark/` tidak boleh dibaca oleh pipeline agent/training.

## Lisensi

Korpus sumber adalah public domain (Unlicense). Metadata sumber disimpan di
`source_register.csv`. Repo ini tidak mendistribusikan ulang korpus mentah.
