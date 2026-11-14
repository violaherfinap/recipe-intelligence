# W1-B bootstrap — rebuild dan verifikasi

**Tanggal:** 2026-11-14
**Branch:** `feat/w1-b-benchmark`
**Mesin:** Windows, Python 3.11.15, `uv` 0.10.8
**Tujuan:** memastikan B dapat membangun ulang korpus dan index yang identik dengan artefak A sebelum menulis query.

## Perintah

```powershell
uv sync --extra dev

git clone https://github.com/AdamBouhmad/open-recipe-archive.git data/raw/open-recipe-archive
$sha = (Get-Content data/corpus_commit.txt).Trim()
git -C data/raw/open-recipe-archive checkout $sha

uv run python -m recipe_qa.corpus.cli build
uv run python -m recipe_qa.index.cli all
```

Commit korpus: `ae3bd2c009a8899dfe63b9166fa98ae3fa8041a8`.

## Hasil build korpus

| Artefak | Jumlah | Hash |
| --- | ---: | --- |
| `docs.jsonl` | 5.605 | `32e485b41fffba635dbd935754ca5d6c38accf18db4ee6c15dac586053c2d13b` |
| `passages.jsonl` | 11.266 | `df561b669e3cf5f33a81075cfdd85d737a0fcc07c04671e647980233ba46e63b` |
| `source_register.csv` | 5.605 | `cb662530a06758c8fe1034d819bd44fc7010251c95ea53daae632b3bda0aaaba` |
| `split.json` | 5.605 assignment | `b7875a733c2ca54db0be72835ff5318dd705e6251ae7e8e37a7ccd1f6e3b6611` |
| `dedup_log.jsonl` | 5 | `b821c22469699f6e8c2e93b70a8538d64071f32cfcf85112b5137bd0c2835ba2` |

**Semua hash cocok dengan `data/processed/manifest.sha256` milik A.**

Split:

```text
train=3921  dev=838  test=846
by_year: 1796=122, 1824=445, 1851=835, 1871=928, 1887=1499, 1896=1776
```

## Hasil build index

| Index | Jumlah | Catatan |
| --- | ---: | --- |
| BM25 | 11.266 passage | `indexes/bm25/` |
| Dense | 11.266 × 384 | `indexes/dense.npy` + `dense_meta.parquet` |

Manifest index:

```json
{
  "embedding_model": "BAAI/bge-small-en-v1.5",
  "dim": 384,
  "passage_count": 11266,
  "normalized": true
}
```

## Verifikasi tambahan

- 22 unit test A lulus (`uv run pytest -q`).
- `uv run ruff check src tests` lulus.
- Smoke retrieval `tomato soup` mengembalikan hasil BM25 dan dense.
- 5 dokumen yang tercatat di `dedup_log.jsonl` semuanya `train`/`dev`; tidak ada dokumen `test` yang dikeluarkan dari index.
- Test per tahun: 1796=19, 1824=68, 1851=126, 1871=140, 1887=226, 1896=267.

## Catatan

- `manifest.json` hasil rebuild hanya berbeda pada `created_at`; hash isi file identik, sehingga file manifest yang di-commit milik A dikembalikan (`git checkout -- data/processed/...`) agar tidak ada perubahan artefak A.
- File besar (`docs.jsonl`, `passages.jsonl`, `indexes/`) tetap gitignored; B membangunnya lokal.
- Q4 di `docs/open_questions.md` diselesaikan dengan opsi rebuild di mesin B.

## Konsekuensi untuk benchmark

- Gold passage hanya boleh berasal dari `split=test` (846 dokumen).
- Pool anotasi juga dibatasi ke `split=test` agar qrels tidak mencampur train/dev.
- Semua gold passage berada di index (tidak ada dokumen test yang ter-dedup).
