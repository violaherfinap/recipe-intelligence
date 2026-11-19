# Handoff W2-A — Status pekerjaan A (week 2)

- **Owner:** Vio
- **Branch:** `feat/w2-a-retrieval`
- **Commit:** head branch ini (lihat `git log --oneline`); benchmark state: tag `benchmark-v1.1`
- **Base:** `origin/feat/w1-d-pass2` (`922c624`) + fix freeze manifest
- **Tanggal:** 2026-11-19
- **Status merge:** branch ini **belum di-merge** ke `dev`/`main`; B harus pull branch ini atau merge ke `dev` dulu.
- **Handoff ke:** B (lalu C/D untuk evaluasi)

## Ringkasan

A sudah membangun jalur retrieval B2/B3, tiga mode chunking A1, empat config
retrieval A2, dan prompt/config baseline B0/B1. Pipeline B0, B2, dan B3 sudah
berjalan end-to-end sampai menghasilkan JSON answer; evaluasi penuh tetap
milik B/C/D.

## Yang sudah jadi

| Artefak | Path | Keterangan |
| --- | --- | --- |
| B2 pipeline | `src/recipe_qa/pipeline/b2.py`, `configs/b2.yaml` | dense + fixed chunk + top-5 |
| B3 pipeline | `src/recipe_qa/pipeline/b3.py`, `configs/b3.yaml` | BM25 + dense + RRF + rerank + filter |
| Retrieval primitives | `src/recipe_qa/retrieval/` | `search.py`, `fusion.py`, `rerank.py`, `filters.py`, `types.py` |
| A1 section index | `indexes/` | 11.266 passage |
| A1 fixed index | `indexes/fixed/` | 5.738 passage |
| A1 hierarchical index | `indexes/hierarchical/` | 37.754 passage (5.601 summary + 32.153 step) |
| A2 configs | `configs/retrieval_dense.yaml`, `retrieval_bm25.yaml`, `retrieval_hybrid.yaml`, `retrieval_hybrid_rerank.yaml` | 4 varian |
| A2 runner | `src/recipe_qa/retrieval/cli.py` | jalankan retrieval + metrik |
| B0/B1 configs | `configs/b0.yaml`, `configs/b1.yaml` | baseline tanpa retrieval |
| Prompt registry | `prompts/registry/structured_v1.yaml` | v3 |
| Few-shot examples | `prompts/examples.jsonl` | 2 contoh dari train |
| Config schema | `src/recipe_qa/config.py`, `configs/schema.py` | Pydantic |
| Tests | `tests/unit/` | 120 test lulus; ruff bersih |

## Cara menjalankan

```powershell
# Bangun passages/index tambahan (sekali saja)
.\scripts\tasks.ps1 passages-fixed
.\scripts\tasks.ps1 passages-hierarchical
.\scripts\tasks.ps1 index-fixed
.\scripts\tasks.ps1 index-hierarchical

# B2 / B3 tanpa generator
uv run python -m recipe_qa.pipeline.b2 --query-id q001 --no-generate
uv run python -m recipe_qa.pipeline.b3 --query-id q002 --no-generate

# B2 / B3 dengan generator Qwen 0.5B
uv run python -m recipe_qa.pipeline.b2 --query-id q002
uv run python -m recipe_qa.pipeline.b3 --query-id q002

# A2 smoke (10 query)
uv run python -m recipe_qa.retrieval.cli --config configs/retrieval_hybrid_rerank.yaml --limit 10
```

## Smoke yang sudah dijalankan

- **B2** q001 retrieval-only: 5 hit, ~154 ms.
- **B3** q001 retrieval-only: 10 hit, ~1,4 s.
- **B0** q002 generation: schema-valid, ~57 s; jawaban dari ingatan (tanpa bukti).
- **B2** q002 generation: schema-valid, ~40 s; bukti yang terambil salah
  (`dried-beef-2` 1887 untuk query 1796) — ini sifat naive B2.
- **B3** q002 generation: schema-valid, ~49 s; menjawab “15 pound piece requires
  one hour and a quarter roasting” dengan sitasi `roast-veal#directions#0`.

### A2 smoke (10 query pertama, belum final)

| Config | Recall@5 | Recall@10 | nDCG@10 | MRR@10 |
| --- | ---: | ---: | ---: | ---: |
| dense | 0.45 | 0.45 | 0.3355 | 0.3000 |
| bm25 | 0.60 | 0.65 | 0.5305 | 0.5125 |
| hybrid | 0.35 | 0.60 | 0.3807 | 0.3083 |
| hybrid+rerank | **0.80** | **0.80** | **0.6549** | **0.6083** |

Angka ini hanya 10 query awal, bukan evaluasi dev penuh. B yang menjalankan
evaluasi A2 lengkap.

**Catatan qrels:** smoke di atas dihitung dengan qrels v1.0. Benchmark sudah
direvisi ke v1.1 (dua label `q083` `0` → `1`; lihat `benchmark/changes_v1_1.jsonl`
dan bagian v1.1 di `reports/week1.md`). Jalankan ulang evaluasi dengan qrels
v1.1; selisihnya kecil tetapi angka final harus memakai v1.1.

## Temuan

- **BM25 kuat** pada query yang menyebut nama resep karena index BM25 memakai
  judul (ADR-011). **Dense lebih lemah** karena teks passage section/fixed tidak
  memuat judul resep.
- **Hybrid+rerank** memberi hasil agregat terbaik pada smoke 10 query, walau
  reranker menjatuhkan gold q001 dari rank 1 (RRF) ke luar top-10. Perlu evaluasi
  penuh; ini kandidat bahan analisis error.
- **B2 fixed chunk tanpa filter** bisa mengambil resep/tahun yang salah. Itu
  baseline naive; B3 menambahkan filter + rerank.
- Generator 0.5B **menyalin few-shot examples** jika prompt berisi contoh
  panjang. Karena itu B2/B3 memakai prompt RAG zero-shot; sitasi ditempel dari
  passage teratas. B4 verifier nanti yang memvalidasi klaim.
- Perbedaan config B1 vs B2 sekarang mencakup `prompt.few_shot` (B1 few-shot,
  B2/B3 zero-shot RAG). Ini deviasi pragmatis dari §12.3; dicatat agar B tidak
  mengira confound-nya hilang. Model dan parameter retrieval lain tetap sama.
- **Test config equality mengizinkan `prompt.few_shot` pada B1 vs B2.** Lihat
  `tests/unit/test_config_equality.py` sebelum mengubah config; tanpa
  pengecualian itu test akan gagal.
- `max_new_tokens` diset **320** (plan: 220) dan `max_examples` **2** (plan: 5)
  supaya JSON dari model 0.5B tidak terpotong. Parameter model lain tetap sama
  di B0–B3.

## Yang dibutuhkan B/C/D

- **B:** jalankan smoke B0/B1; evaluasi B2/B3 di dev; evaluasi A2 (4 config)
  dengan qrels; isi `reports/b2b3_dev.md` dan `reports/a2_dev.md`.
- **C:** evaluasi A1 pada tiga index (`indexes/`, `indexes/fixed/`,
  `indexes/hierarchical/`); isi `reports/a1_dev.md`.
- **D:** qrels v2, error taxonomy, dan catatan kegagalan retrieval/verifier.

## Yang belum / terbuka

- Evaluasi penuh A2/B3 dan Gate 2 (`Recall@10 B3 > B2`, config equality) belum
  dijalankan; itu bagian B/C/D.
- Reranker `cross-encoder/ms-marco-MiniLM-L6-v2` perlu diperiksa pada q001:
  gold berada di rank 1 setelah RRF tetapi keluar dari top-10 setelah rerank.
- B2 belum memakai filter metadata dan belum memuat judul resep di index dense.
- Generator hanya diuji pada 3 query; kualitas jawaban belum diaudit manusia.
- `indexes/` dan `passages_*.jsonl` tidak di-commit; rebuild dengan target di
  atas.

## Referensi

- `configs/b0.yaml` … `configs/b3.yaml`
- `configs/retrieval_*.yaml`
- `prompts/registry/structured_v1.yaml`
- `src/recipe_qa/retrieval/`
- `src/recipe_qa/pipeline/`
- `docs/adr/008-chunking.md`, `docs/adr/011-bm25-preprocessing.md`
- `docs/handoff/w1-a.md`
