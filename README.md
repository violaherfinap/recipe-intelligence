# Recipe Intelligence

Evidence-grounded question answering over **5,605 historical American recipes**
from [`open-recipe-archive`](https://github.com/AdamBouhmad/open-recipe-archive)
(`ye-old-american`, public domain). The project studies whether retrieval,
verification, parameter-efficient fine-tuning, and guarded tool use improve
factual answers with citations over a plain LLM.

This repository follows `RENCANA_LENGKAP.md` and `RENCANA_MINGGUAN.md`.
Week 1, block A builds the data foundation: corpus, passages, split, and
retrieval indexes.

## Requirements

- Windows 11 (or Linux/macOS), Python 3.11
- [`uv`](https://docs.astral.sh/uv/) for environment management
- ~2 GB free disk for the environment and indexes

## Quick start

```powershell
# One-time environment setup
uv sync --extra dev

# Download and pin the corpus (public domain)
git clone --depth 1 https://github.com/AdamBouhmad/open-recipe-archive.git data/raw/open-recipe-archive
git -C data/raw/open-recipe-archive rev-parse HEAD | Set-Content -Encoding ascii data/corpus_commit.txt

# Build docs.jsonl, passages.jsonl, source_register.csv, split.json, manifests
uv run python -m recipe_qa.corpus.cli build

# Build BM25 + dense indexes
uv run python -m recipe_qa.index.cli all

# Verify
uv run pytest
uv run ruff check src tests
uv run python -m recipe_qa.index.cli smoke --query "tomato soup"
```

On Windows, `make` is optional. The same targets are available through
`.\scripts\tasks.ps1`:

```powershell
.\scripts\tasks.ps1 setup
.\scripts\tasks.ps1 corpus
.\scripts\tasks.ps1 index
.\scripts\tasks.ps1 test
.\scripts\tasks.ps1 smoke
```

Linux/macOS can use the `Makefile` directly.

## Data layout

| Path | Contents |
| --- | --- |
| `data/raw/open-recipe-archive/` | Raw corpus clone (gitignored) |
| `data/corpus_commit.txt` | Pinned corpus commit SHA |
| `data/processed/docs.jsonl` | One cleaned document per recipe |
| `data/processed/passages.jsonl` | Section-aware retrieval passages |
| `data/processed/source_register.csv` | Source, licence, hash, split per document |
| `data/processed/split.json` | Deterministic 70/15/15 split (seed 42) |
| `data/processed/manifest.json` | Corpus, chunking, counts, file hashes |
| `data/processed/manifest.sha256` | SHA-256 of frozen artefacts |
| `indexes/bm25/` | BM25 index and metadata |
| `indexes/dense.npy` | L2-normalised BGE embeddings (N x 384) |
| `indexes/dense_meta.parquet` | Row alignment for the dense matrix |
| `indexes/manifest.json` | Embedding model, dimension, count, corpus hash |

Large files (`docs.jsonl`, `passages.jsonl`, indexes) are not committed. Rebuild
them with the commands above; the manifests and split file are committed so the
build can be verified.

## Project status

- **Week 1, block A:** done — 5,605 recipes cleaned, 11,266 passages (5,600
  canonical docs), 70/15/15 split (seed 42), BM25 and 384d dense indexes,
  20 unit tests passing, ruff clean.
- **Week 1, block B:** annotation guideline and 115 benchmark queries.
- **Week 1, block C/D:** blind qrels, adjudication, frozen benchmark.

## Licence

The source corpus is public domain (Unlicense). Source metadata is preserved in
`source_register.csv`. This repository does not redistribute the raw corpus.
