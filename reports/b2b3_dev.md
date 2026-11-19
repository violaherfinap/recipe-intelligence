# Week 2 — B2/B3 evaluation, smoke B0/B1, dan pool v2

- **Owner:** B
- **Tanggal:** 2026-11-19
- **Branch:** `feat/w2-b-eval-pool`
- **Base commit:** `75942de` (`feat/w2-a-retrieval`)
- **Status:** B3 dan pool v2 selesai; B2 passage-level menunggu qrels v2
- **Handoff ke:** C (anotasi pool v2), lalu D (qrels v2 + Gate 2)

## Ringkasan

- B3 (hybrid + rerank + filter, section) mencapai Recall@10 **0,7120**.
- B2 (dense + fixed, top-5) tidak bisa diukur passage-level dengan qrels v1.1;
  semua passage `#fixed#` belum punya label. Doc-level B2 = **0,2889**.
- Smoke B0 20/20 schema-valid; B1 18/20 (2 gagal parse karena few-shot).
- Pool v2 selesai: **2.237 kandidat**, **448 kandidat baru**, median
  **19 kandidat/query**, semua `split=test`.

## Setup

| Item | Nilai |
| --- | --- |
| Query | 115 (35 easy / 25 multi-hop / 30 temporal / 25 no-evidence) |
| Qrels | v1.1, SHA-256 `e11ca2cbf56b...` |
| Query hash | `d5128e484131...` |
| B2 index | fixed, 5.738 passage |
| B3 index | section, 11.266 passage |
| B2 output | top-5, tanpa filter |
| B3 output | top-10, filter tahun/buku + rerank |
| Artifact B2 | `artifacts/runs/retrieval_b2_full.json` |
| Artifact B3 | `artifacts/runs/retrieval_b3_full.json` |

## B2 vs B3

| Run | n | R@5 | R@10 | nDCG@10 | MRR@10 | Doc recall | Judged | Test split | p50 ms | p95 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| B2 fixed top-5 | 90 | 0,0000 | 0,0000 | 0,0000 | 0,0000 | 0,2889 | 0,0000 | 0,1861 | 211,9 | 559,2 |
| B3 section top-10 | 90 | 0,5426 | 0,7120 | 0,5270 | 0,5228 | 0,7833 | 0,1791 | 0,2539 | 1.984,8 | 2.820,4 |

**B2 passage-level = 0 bukan karena B2 tidak menemukan apa pun.** qrels v1.1
hanya berisi passage section (`#ingredients#`, `#directions#`), sedangkan B2
mengembalikan passage fixed (`#fixed#`). Tidak ada satu pun ID B2 yang cocok
dengan qrels, sehingga `judged=0` dan seluruh Recall dihitung 0.

Doc-level recall memetakan passage ke `doc_id`; dengan cara ini B2 = 0,2889
dan B3 = 0,7833. Perbandingan doc-level sudah menunjukkan B3 jauh lebih baik,
tetapi belum bisa menggantikan Recall@10 passage-level.

## Smoke B0/B1

20 query stratifikasi: q001–q005 (easy), q036–q040 (multi-hop), q061–q065
(temporal), q091–q095 (no-evidence).

| Config | n | Schema valid | Abstain | p50 | p95 |
| --- | ---: | ---: | ---: | ---: | ---: |
| B0 zero-shot, tanpa retrieval | 20 | 20/20 (1,00) | 1 | 59,8 s | 147,7 s |
| B1 few-shot, tanpa retrieval | 20 | 18/20 (0,90) | 1 | 50,3 s | 181,4 s |

Artifact: `artifacts/runs/smoke/b0/`, `artifacts/runs/smoke/b1/`.

Temuan kualitatif:

- B0 dan B1 **mengarang** jawaban untuk topik yang tidak ada di korpus:
  gas oven, aluminium foil, microwave, food processor, dan kalori. Contoh:
  `q094` dijawab “microwave-safe container, 10 minutes”; `q095` dijawab
  “food processor”.
- B1 gagal schema pada `q001` dan `q005`: model menyalin header contoh
  (`query_id: ex_003`) dan menulis `schema_valid: false`, satu di antaranya
  dibungkus markdown fence. Ini bukti bahwa few-shot pada model 0,5B justru
  menurunkan kepatuhan format.
- B0 menjawab `q001` “about 1 hour” padahal gold “one and a half hours”;
  `q005` “20 eggs” padahal gold “four eggs”. Tanpa retrieval, jawaban tidak
  dapat dipercaya.
- B0/B1 tidak menghasilkan claims/sitasi; itu memang desain baseline.

## Gate 2

| Kriteria | Status | Bukti |
| --- | --- | --- |
| qrels v2 frozen | **belum** | milik C/D |
| Recall@10 B3 > B2 (passage) | **provisional pass** 0,7120 > 0,0000, tetapi B2 tidak terukur | qrels v1.1 tidak punya `#fixed#` |
| Recall@10 B3 > B2 (doc-level) | **pass** 0,7833 > 0,2889 | artifact B2/B3 |
| Config equality B0–B3 | **pass** | `tests/unit/test_config_equality.py` |

Gate 2 belum boleh ditutup sebagai “B3 mengalahkan B2” sampai qrels v2 memuat
label passage fixed. Setelah qrels v2, jalankan ulang:

```powershell
uv run python tools/eval_retrieval.py --config configs/b2.yaml --limit 0 --retain-k 10 --out artifacts/runs/retrieval_b2_v2.json
uv run python tools/eval_retrieval.py --config configs/b3.yaml --limit 0 --out artifacts/runs/retrieval_b3_v2.json
```

## Pool v2

Dibangun dari pool v1 + top-10 B2 (fixed) + top-10 B3 (section) + top-10
A2 dense/BM25/hybrid (section). Semua kandidat wajib `split=test`.

| Item | Nilai |
| --- | ---: |
| Query | 115 |
| Kandidat total | 2.237 |
| Kandidat baru (belum di qrels v1.1) | 448 |
| Kandidat per query | min 15 / median 19 / max 28 |
| Passage fixed | 212 |
| Passage section | 2.025 |
| Gold passage | 145 (semua ada) |
| Kandidat retrieval dibuang karena train/dev | 4.492 |
| Query tanpa kandidat | 0 |
| SHA-256 pool | `567d21545b86...` |

Artifact:

- `benchmark/pool_v2.jsonl` — blinded, hanya `query_id`, `passage_id`, `doc_id`.
- `benchmark/pool_v2_meta.jsonl` — provenance; **jangan dibuka anotator**.
- `benchmark/pool_v2.sha256`.

**4.492 kandidat dibuang karena bukan test.** Ini angka penting: sebagian besar
hasil retrieval lintas split adalah passage train/dev. Pool v2 hanya
mengizinkan kandidat test agar qrels tetap test-only.

## Temuan

1. **B3 jauh lebih baik dari B2**, tetapi perbandingan passage-level belum sah
   sampai qrels v2 ada. Doc-level sudah jelas: 0,7833 vs 0,2889.
2. **Filter metadata adalah faktor utama.** B3 memakai filter tahun/buku;
   B2 tidak. Ini konsisten dengan A2: hybrid+rerank tanpa filter hanya 0,4102.
3. **B2 retrieve lintas split dan lintas tahun.** Hanya 18,61% hasil B2 yang
   berasal dari test split. Baseline naive memang begini; ini alasan B3 ada.
4. **Few-shot bukan otomatis lebih baik.** B1 menurunkan schema validity dari
   100% ke 90% pada model 0,5B.
5. **Tanpa retrieval, model berhalusinasi anachronistically** (microwave,
   aluminium foil, food processor). Slice no-evidence adalah ujian langsung
   untuk abstain; B0/B1 gagal abstain di 5/5 query no-evidence.

## Batasan

- qrels v1.1 belum mencakup passage fixed; B2 passage-level = 0 secara
  struktural, bukan kualitas retrieval sebenarnya.
- Pool v2 menambah 448 kandidat baru; angka B3/A2 final dapat berubah setelah
  qrels v2.
- B2 dan B3 berbeda pada chunking, mode retrieval, filter, dan `final_k`.
  Perbandingan ini system-level, bukan ablasi satu variabel.
- Smoke B0/B1 hanya 20 query; schema validity belum diuji pada 115 query.

## Instruksi untuk C

Seed qrels v1.1, lalu anotasi hanya kandidat baru:

```powershell
Copy-Item benchmark/qrels.jsonl benchmark/qrels_v2_c.jsonl

uv run python tools/annotate.py relevance --annotator C `
  --queries benchmark/queries.jsonl `
  --pool benchmark/pool_v2.jsonl `
  --passages data/processed/passages.jsonl data/processed/passages_fixed.jsonl `
  --out benchmark/qrels_v2_c.jsonl
```

`pool_v2_meta.jsonl` tidak boleh dibuka. Passage `#fixed#` dinilai dengan skala
0/1/2 yang sama; nilailah passage terhadap klaim, bukan berdasarkan chunking.

## Instruksi untuk D

1. Seed qrels v1.1, anotasi pass 2 blind ke `qrels_v2_d.jsonl`.
2. Hitung κ pada 448 item baru (relevance).
3. Adjudikasi, tulis `benchmark/qrels.jsonl` v2.
4. Regenerate `benchmark/manifest.sha256`.
5. Jalankan ulang B2/B3 dengan qrels v2, lalu tutup Gate 2.
6. Spot-check 5 query no-evidence di pool v2.
