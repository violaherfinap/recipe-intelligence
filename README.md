# Recipe Intelligence

Tanya-jawab berbasis bukti atas **5.605 resep historis Amerika** dari
[`open-recipe-archive`](https://github.com/AdamBouhmad/open-recipe-archive)
(koleksi `ye-old-american`, public domain). Proyek ini mempelajari apakah
retrieval, verifikasi, fine-tuning parameter-efficient, dan penggunaan tool
yang dijaga dapat meningkatkan jawaban faktual dengan sitasi dibanding LLM biasa.

Repo ini mengikuti `RENCANA_LENGKAP.md` dan `RENCANA_MINGGUAN.md`.
Week 1 blok A membangun fondasi data: korpus, passage, split, dan index retrieval.

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
- **Handoff A → B:** lihat [`docs/handoff/w1-a.md`](docs/handoff/w1-a.md) untuk
  status, artefak, dan keputusan yang masih terbuka.
- **Week 1, blok B:** guideline anotasi dan 115 query benchmark.
- **Week 1, blok C/D:** qrels blind, adjudikasi, dan benchmark frozen.

## Lisensi

Korpus sumber adalah public domain (Unlicense). Metadata sumber disimpan di
`source_register.csv`. Repo ini tidak mendistribusikan ulang korpus mentah.
