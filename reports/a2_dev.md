# Week 2 — A2 retrieval evaluation

- **Owner:** B
- **Tanggal:** 2026-11-19
- **Branch:** `feat/w2-b-eval-pool`
- **Base commit:** `75942de` (`feat/w2-a-retrieval`)
- **Status:** selesai untuk qrels v1.1; angka final menunggu qrels v2
- **Handoff ke:** C/D

## Ringkasan

Empat varian A2 dijalankan pada 115 query beku dengan qrels v1.1. Retrieval
dibatasi ke 10 hasil per query dan dinilai dengan Recall@5/10, nDCG@10, MRR@10.

Hasil utama:

- **Hybrid + rerank + filter metadata** terbaik: Recall@10 **0,7120**.
- **Hybrid tanpa filter/rerank** 0,4324; **BM25** 0,3917; **dense** 0,3019.
- **Filter metadata adalah sumber gain terbesar.** Rerank tanpa filter hanya
  0,4102, lebih rendah dari hybrid tanpa rerank (0,4324).
- Smoker A pada 10 query pertama berhasil direproduksi persis.

## Setup

| Item | Nilai |
| --- | --- |
| Query | 115 (35 easy / 25 multi-hop / 30 temporal / 25 no-evidence) |
| Query dinilai retrieval | 90 answerable; 25 no-evidence tidak punya qrels relevan |
| Qrels | `benchmark/qrels.jsonl` v1.1, SHA-256 `e11ca2cbf56b...` |
| Query hash | `d5128e484131...` |
| Index | section, 11.266 passage |
| Embedding | `BAAI/bge-small-en-v1.5` |
| Reranker | `cross-encoder/ms-marco-MiniLM-L6-v2` |
| Seed | retrieval deterministik |

Artifact:

| Run | Artifact |
| --- | --- |
| dense | `artifacts/runs/a2_dense_full.json` |
| bm25 | `artifacts/runs/a2_bm25_full.json` |
| hybrid | `artifacts/runs/a2_hybrid_full.json` |
| hybrid+rerank+filter | `artifacts/runs/a2_hybrid_rerank_full.json` |
| hybrid+rerank tanpa filter | `artifacts/runs/a2_hybrid_rerank_nofilter_full.json` |
| sanity 10 query dense | `artifacts/runs/a2_dense_smoke10.json` |
| sanity 10 query rerank | `artifacts/runs/a2_hybrid_rerank_smoke10.json` |
| tabel mentah | `artifacts/runs/a2_tables.md`, `artifacts/runs/a2_slices.md` |

## Overall

| Run | n | R@5 | R@10 | nDCG@10 | MRR@10 | Doc recall | Judged | Test split | p50 ms | p95 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| dense | 90 | 0,2222 | 0,3019 | 0,2134 | 0,2271 | 0,3500 | 0,1870 | 0,1870 | 248,1 | 680,1 |
| bm25 | 90 | 0,3389 | 0,3917 | 0,2810 | 0,2878 | 0,5333 | 0,1096 | 0,2478 | 0,5 | 0,8 |
| hybrid | 90 | 0,3046 | 0,4324 | 0,2955 | 0,3199 | 0,4889 | 0,1826 | 0,2209 | 61,0 | 214,8 |
| hybrid+rerank+filter | 90 | **0,5426** | **0,7120** | **0,5270** | **0,5228** | **0,7833** | 0,1791 | 0,2539 | 1.948,9 | 2.653,8 |
| hybrid+rerank tanpa filter | 90 | 0,3287 | 0,4102 | 0,3125 | 0,3266 | 0,4944 | 0,1739 | 0,2017 | 1.847,0 | 3.060,2 |

`Judged` = proporsi hasil top-10 yang ada di qrels. `Test split` = proporsi
hasil top-10 yang berasal dari `split=test`.

## Per slice

### Hybrid tanpa filter/rerank

| Slice | n | R@5 | R@10 | nDCG@10 | MRR@10 | Doc recall | Test split |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| easy | 35 | 0,5000 | 0,6429 | 0,4349 | 0,3858 | 0,6857 | 0,2600 |
| multi-hop | 25 | 0,0800 | 0,1700 | 0,0982 | 0,1014 | 0,2000 | 0,1320 |
| no-evidence | 25 | 0,0000 | 0,0000 | 0,0000 | 0,0000 | 0,0000 | 0,2200 |
| temporal | 30 | 0,2639 | 0,4056 | 0,2974 | 0,4250 | 0,5000 | 0,2500 |

### Hybrid + rerank + filter

| Slice | n | R@5 | R@10 | nDCG@10 | MRR@10 | Doc recall | Test split |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| easy | 35 | 0,7714 | 0,8714 | 0,6727 | 0,6182 | 0,9429 | 0,2457 |
| multi-hop | 25 | 0,4467 | 0,7267 | 0,4852 | 0,4624 | 0,7600 | 0,2480 |
| no-evidence | 25 | 0,0000 | 0,0000 | 0,0000 | 0,0000 | 0,0000 | 0,2080 |
| temporal | 30 | 0,3556 | 0,5139 | 0,3918 | 0,4619 | 0,6167 | 0,3067 |

## Sanity check terhadap smoke A

Smoke A hanya memakai q001–q010 (easy) dan dijalankan sebelum evaluasi penuh.
Hasil tool B mereproduksi angka A persis:

| Config | n | R@5 | R@10 | nDCG@10 | MRR@10 |
| --- | ---: | ---: | ---: | ---: | ---: |
| dense, q001–q010 | 10 | 0,4500 | 0,4500 | 0,3355 | 0,3000 |
| hybrid+rerank, q001–q010 | 10 | 0,8000 | 0,8000 | 0,6549 | 0,6083 |

Angka A di `docs/handoff/w2-a.md`: dense 0,45 / 0,45 / 0,3355 / 0,3000 dan
hybrid+rerank 0,80 / 0,80 / 0,6549 / 0,6083. **Cocok.**

## Temuan

1. **Filter metadata mendominasi gain.** Hybrid+rerank+filter 0,7120, tetapi
   hybrid+rerank tanpa filter hanya 0,4102. Bahkan hybrid tanpa rerank (0,4324)
   lebih baik daripada rerank tanpa filter. Jadi klaim “reranker membantu”
   tidak boleh dibuat dari perbandingan A2 yang ada; yang membantu adalah
   kombinasi filter tahun/buku + rerank.
2. **BM25 kuat di easy, lemah di multi-hop.** Recall@10 easy 0,5429, multi-hop
   0,1267. Ini konsisten dengan ADR-011: BM25 memakai judul resep, sehingga
   query yang menyebut nama resep mudah; multi-hop butuh dua dokumen dan
   penalaran lintas resep.
3. **Dense paling lemah.** Recall@10 0,3019. Dense tidak memuat judul resep di
   teks passage dan tidak memakai filter metadata.
4. **Hybrid+rerank+filter terbaik di semua slice**, termasuk multi-hop
   (0,7267) dan temporal (0,5139).
5. **Coverage masih rendah.** Hanya 10,96%–18,70% hasil top-10 yang sudah
   dinilai di qrels, dan hanya 18,61%–25,39% hasil yang berasal dari test split.
   Artinya 75–81% hasil retrieval adalah passage train/dev yang tidak masuk
   qrels, dihitung 0 sesuai aturan “unjudged = non-relevan”. Angka di atas
   adalah **lower bound**, bukan kualitas retrieval sebenarnya.
6. **Latency** (CPU, tanpa proses lain): BM25 < 1 ms; hybrid 61 ms; dense 248 ms;
   rerank ±1,9 s p50. Rerank ±30× lebih mahal daripada hybrid.

## Batasan

- Tidak ada dev query set terpisah; 115 query ini adalah test benchmark
  (Q10). Angka dipakai untuk evaluasi, bukan tuning.
- qrels v1.1 dibangun dari pool v1 (gold + dense section top-10 + negatif),
  sehingga kandidat BM25/hybrid belum sepenuhnya dinilai (Q11). Pool v2
  menambahkan 448 kandidat baru; angka final menunggu qrels v2.
- Config `hybrid_rerank` mengaktifkan `filters`, sedangkan dense/bm25/hybrid
  tidak. Perbandingan 4 varian karena itu bukan ablasi murni. Diagnostik
  `hybrid_rerank_nofilter` memisahkan efek filter.
- Latency diukur pada laptop CPU dengan model lain tidak aktif; angka dapat
  berubah jika generation berjalan bersamaan.

## Perintah reproduksi

```powershell
uv run python tools/eval_retrieval.py --config configs/retrieval_dense.yaml --limit 0 --out artifacts/runs/a2_dense_full.json
uv run python tools/eval_retrieval.py --config configs/retrieval_bm25.yaml --limit 0 --out artifacts/runs/a2_bm25_full.json
uv run python tools/eval_retrieval.py --config configs/retrieval_hybrid.yaml --limit 0 --out artifacts/runs/a2_hybrid_full.json
uv run python tools/eval_retrieval.py --config configs/retrieval_hybrid_rerank.yaml --limit 0 --out artifacts/runs/a2_hybrid_rerank_full.json
uv run python tools/eval_retrieval.py --config configs/retrieval_hybrid_rerank_nofilter.yaml --limit 0 --out artifacts/runs/a2_hybrid_rerank_nofilter_full.json
```
