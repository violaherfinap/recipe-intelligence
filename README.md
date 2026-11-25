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
- **Revisi v1.1 (Week 1):** adjudikasi ulang 14 konflik oleh A (12 sama, 2
  berubah), audit 183 item non-zero (181 dipertahankan), klarifikasi relevance
  per passage/per klaim di `benchmark/guidelines.md`. κ pada 183 item penentu:
  0.6333, bukan 0.9607 (pool penuh).
- **Week 2, blok A:** selesai — B2/B3 pipeline, tiga index A1 (section 11.266 /
  fixed 5.738 / hierarchical 37.754 passage), empat config retrieval A2,
  prompt registry B0/B1, 120 test lulus, ruff bersih. Branch
  `feat/w2-a-retrieval` **belum di-merge** ke `dev`/`main`.
  Handoff: [`docs/handoff/w2-a.md`](docs/handoff/w2-a.md).

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

## Week 2 — Retrieval

```powershell
# Bangun passage + index untuk A1 (sekali saja)
.\scripts\tasks.ps1 passages-fixed
.\scripts\tasks.ps1 passages-hierarchical
.\scripts\tasks.ps1 index-fixed
.\scripts\tasks.ps1 index-hierarchical

# B2 (dense + fixed chunk + top-5) / B3 (hybrid + rerank)
uv run python -m recipe_qa.pipeline.b2 --query-id q002 --no-generate
uv run python -m recipe_qa.pipeline.b3 --query-id q002 --no-generate

# A2 smoke: dense / bm25 / hybrid / hybrid+rerank
uv run python -m recipe_qa.retrieval.cli --config configs/retrieval_hybrid_rerank.yaml --limit 10
```

Detail pipeline, config, dan temuan ada di
[`docs/handoff/w2-a.md`](docs/handoff/w2-a.md).

## Lisensi

Korpus sumber adalah public domain (Unlicense). Metadata sumber disimpan di
`source_register.csv`. Repo ini tidak mendistribusikan ulang korpus mentah.
