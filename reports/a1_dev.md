# Week 2 - A1 chunking evaluation

- **Owner:** C (v1.1); D (v2 rerun)
- **Tanggal:** 2026-11-22 (v1.1); 2026-11-24 (v2)
- **Branch:** `feat/w2-d-finalize-qrels-v2`
- **Base commit:** `a7491cb`
- **Status:** selesai untuk qrels v2; passage hierarchical tidak terukur
- **Handoff ke:** A/B

## Ringkasan

Tiga index A1 dijalankan dengan **dense retrieval yang sama** (tanpa BM25,
reranker, atau filter metadata) pada 115 query beku. Satu-satunya variabel yang
berubah adalah `chunking`: fixed, section, hierarchical. Rerun v2 memakai
`benchmark/qrels.jsonl` final 2.237 baris setelah adjudikasi A/C/D.

Hasil utama:

- **Hierarchical doc recall@10 tertinggi: 0,5778**, terutama temporal
  **0,7833**; tetapi konteks top-10 sangat pendek (rata-rata **278 token**).
- **Fixed 0,3889**, di atas section **0,3500**, tetapi konteksnya paling mahal:
  rata-rata **1.822 token**, p95 **2.740**, dan **38/115** query melewati budget
  2.000 token.
- **Fixed passage R@10 0,1515**; angka ini sejalan dengan B2 pada qrels v2.
- **Section passage R@10 0,1633**, berbeda dari laporan v1.1 karena population
  qrels v2 lebih besar; bukan penurunan performa retrieval.
- Passage hierarchical **tidak valid** karena qrels v2 tidak memuat passage ID
  hierarchical. Dokumen-level recall adalah metrik utama A1.
- Tidak ada varian yang jelas menang di semua metrik: hierarchical unggul
  recall dokumen, section paling hemat konteks, fixed index paling kecil.

## Setup

| Item | Nilai |
| --- | --- |
| Query | 115 (35 easy / 25 multi-hop / 30 temporal / 25 no-evidence) |
| Query dinilai doc recall | 90 answerable; 25 no-evidence tidak punya qrels relevan |
| Qrels | `benchmark/qrels.jsonl` v2 final, SHA-256 `8ed07e8ebcbefdea332a6a1555b320d0d8c6553f6bffd978cd22894338171926` |
| Query hash | `d5128e484131...` |
| Retrieval | dense, `BAAI/bge-small-en-v1.5`, `top_k_dense=50` |
| Reranker | tidak aktif |
| Filter metadata | tidak aktif |
| `final_k` / `retain_k` | 10 / 10 |
| Seed | retrieval deterministik |

Index yang dibandingkan:

| Mode | Passage | Path |
| --- | ---: | --- |
| fixed | 5.738 | `indexes/fixed/` |
| section | 11.266 | `indexes/` |
| hierarchical | 37.754 | `indexes/hierarchical/` |

Artifact:

| Run | Artifact |
| --- | --- |
| fixed | `artifacts/runs/a1_fixed_full.json` |
| section | `artifacts/runs/a1_section_full.json` |
| hierarchical | `artifacts/runs/a1_hierarchical_full.json` |
| context/index stats | `artifacts/runs/a1_context_stats_v2.json` |
| config | `configs/a1_fixed.yaml`, `a1_section.yaml`, `a1_hierarchical.yaml` |

## Overall - qrels v2

| Run | Passage R@5 | Passage R@10 | nDCG@10 | MRR@10 | Doc recall@10 | Judged@10 | Test split | p50 ms | p95 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| fixed | 0,1052 | 0,1515 | 0,1385 | 0,2187 | 0,3889 | 0,1843 | 0,1843 | 26,6 | 36,4 |
| section | 0,1183 | 0,1633 | 0,1432 | **0,2271** | 0,3500 | 0,1870 | 0,1870 | 24,6 | 33,1 |
| hierarchical | n/a* | n/a* | n/a* | n/a* | **0,5778** | n/a* | 0,2217 | 28,3 | 45,9 |

\* Qrels v2 tidak punya passage ID hierarchical. Angka passage/nDCG/MRR/judged
hierarchical secara struktural 0 karena tidak ada passage ID yang cocok, bukan
karena retrieval gagal. Doc recall memakai `doc_id`, sehingga tetap valid lintas
chunking.

Passage fixed dan section memakai population label yang berbeda karena qrels v2
menambahkan 448 kandidat baru; bandingkan angka passage antar-mode dengan
hati-hati. Doc recall memakai dokumen gold yang sama dan tetap comparable.

## Per slice - doc recall@10

| Slice | n | fixed | section | hierarchical |
| --- | ---: | ---: | ---: | ---: |
| easy | 35 | 0,6000 | 0,6143 | **0,7143** |
| multi-hop | 25 | **0,1600** | 0,0800 | 0,1400 |
| temporal | 30 | 0,3333 | 0,2667 | **0,7833** |
| no-evidence | 25 | 0,0000 | 0,0000 | 0,0000 |
| **Overall** | **90** | **0,3889** | **0,3500** | **0,5778** |

## Index dan context length

Context length = total `token_count` dari 10 passage teratas per query.
`dense.npy` dipakai untuk perbandingan ukuran index yang adil; total direktori
section juga memuat index BM25 yang tidak dipakai pada A1.

| Mode | Passage | `dense.npy` | Total direktori | Context mean | p50 | p95 | max | >2.000 token | Mean hit token | Unique doc/query |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| fixed | 5.738 | 8,81 MB | 11,46 MB | 1.822 | 1.747 | 2.740 | 3.267 | 38/115 | 182,2 | 9,89 |
| section | 11.266 | 17,30 MB | 94,35 MB | 722 | 576 | 1.645 | 2.866 | 4/115 | 72,2 | 9,54 |
| hierarchical | 37.754 | 57,99 MB | 62,35 MB | **278** | 272 | 454 | 559 | **0/115** | 27,8 | 9,71 |

## Temuan

1. **Chunking mengubah doc recall secara besar.** Hierarchical menemukan
   dokumen gold 65% lebih sering daripada section (0,5778 vs 0,3500), terutama
   pada temporal (0,7833 vs 0,2667). Summary dan step chunk tampaknya membawa
   sinyal tahun/judul yang tidak ada di passage section yang lebih panjang.
2. **Hierarchical paling murah untuk context budget, tetapi paling banyak
   passage.** 10 hasil hierarchical hanya memakai rata-rata 278 token dan tidak
   pernah melewati 2.000 token, tetapi index-nya 37.754 passage dan `dense.npy`
   57,99 MB. Apakah konteks sependek itu cukup untuk generation belum diuji.
3. **Fixed memberi recall lebih tinggi dari section dengan biaya konteks.**
   Doc recall 0,3889 vs 0,3500, tetapi rata-rata 1.822 token dan 38/115 query
   melewati 2.000 token. Untuk budget 2.000 token, fixed berisiko terpotong.
4. **Fixed passage R@10 0,1515 sejalan dengan B2.** Qrels v2 akhirnya memuat
   passage fixed, sehingga fixed passage-level dapat diukur; hasilnya sama
   dengan retrieval B2 yang memakai index fixed.
5. **Section passage R@10 0,1633 tidak sebanding dengan v1.1 (0,3019).**
   Population qrels v2 bertambah dari 1.789 menjadi 2.237 judgment, sehingga
   denominator passage berubah. Konfigurasi retrieval tidak berubah.
6. **Latency ketiga mode sebanding.** p50 24-28 ms tanpa reranker; perbedaan
   index size tidak diterjemahkan ke latency besar pada 115 query. Biaya
   terbesar tetap reranker/generation, bukan chunking retrieval dense.

## Batasan

- Qrels v2 tidak menilai passage hierarchical. Passage recall, nDCG, MRR, dan
  judged rate hierarchical **tidak boleh** dibandingkan; gunakan doc recall
  untuk klaim lintas chunking.
- Passage fixed dan section memakai population label yang berbeda; jangan
  membandingkan passage R@10 fixed vs section sebagai perbedaan performa murni.
- A1 ini retrieval-only. **Groundedness dan kualitas jawaban belum diukur**;
  itu membutuhkan pipeline generation B2/B3 dan penilaian klaim.
- Hasil v1.1 dipertahankan sebagai riwayat, bukan angka final. Gunakan tabel
  qrels v2 untuk laporan Week 2.
- Tidak ada dev query set terpisah; 115 query ini adalah benchmark test (Q10),
  jadi hasil dipakai untuk evaluasi, bukan tuning.
- Latency diukur CPU secara sekuensial; model load tidak termasuk timing per
  query.
- Hierarchical menghasilkan beberapa passage dari dokumen yang sama (summary +
  step); unique doc/query tetap 9,71 dari 10, tetapi redundancy perlu
  dipertimbangkan saat memilih konteks generation.

## Riwayat v1.1

Angka di bawah adalah hasil sebelum qrels v2 freeze; hanya untuk jejak historis.

| Run | Passage R@10 | nDCG@10 | MRR@10 | Doc recall@10 | p50 ms | p95 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| fixed | n/a* | n/a* | n/a* | 0,3889 | 37,0 | 69,3 |
| section | 0,3019 | 0,2134 | 0,2271 | 0,3500 | 39,8 | 60,2 |
| hierarchical | n/a* | n/a* | n/a* | 0,5778 | 46,2 | 69,9 |

## Perintah reproduksi

```powershell
uv run python -m recipe_qa.corpus.cli passages --mode hierarchical --out data/processed/passages_hierarchical.jsonl
uv run python -m recipe_qa.index.cli all --passages data/processed/passages_hierarchical.jsonl --out indexes/hierarchical
uv run python tools/eval_retrieval.py --config configs/a1_fixed.yaml --limit 0 --out artifacts/runs/a1_fixed_full.json
uv run python tools/eval_retrieval.py --config configs/a1_section.yaml --limit 0 --out artifacts/runs/a1_section_full.json
uv run python tools/eval_retrieval.py --config configs/a1_hierarchical.yaml --limit 0 --out artifacts/runs/a1_hierarchical_full.json
uv run python tools/a1_context_stats.py --runs artifacts/runs --out artifacts/runs/a1_context_stats_v2.json
```

## Laporan terkait

- [`a2_dev.md`](a2_dev.md) - A2 retrieval; section dense menjadi baseline A1.
- [`b2b3_dev.md`](b2b3_dev.md) - B2/B3 dan pool v2.
- [`../docs/handoff/w2-d.md`](../docs/handoff/w2-d.md) - closeout D dan qrels v2.
- [`../docs/adr/008-chunking.md`](../docs/adr/008-chunking.md) - keputusan chunking.
