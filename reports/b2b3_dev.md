# Week 2 - B2/B3 evaluation, qrels v2, dan Gate 2

- **Owner:** B (evaluasi), C/D (anotasi dan freeze)
- **Tanggal final:** 2026-11-24
- **Branch:** `feat/w2-d-finalize-qrels-v2`
- **Status:** qrels v2 frozen; B2/B3 final; Gate 2 lulus
- **Handoff ke:** A (test B0-B3)

## Ringkasan

- Qrels v2 frozen: **2.237 baris**, 115 query, label final `0=1955`, `1=38`, `2=244`.
- Agreement relevance: C/D **kappa 0.9629** (6 konflik); Fleiss A/C/D **0.9223**; 1 tie `q013` diputuskan final `1`.
- Verdict: **145 klaim**, C/D kappa **0.4983** (1 konflik, `q048` final `REFUTED`); label final `SUPPORTED=144`, `REFUTED=1`.
- B3 final Recall@10 **0.5369**; B2 final Recall@10 **0.1515**. Gate 2 lulus.
- B3 tetap jauh lebih baik pada doc recall: **0.7833** vs **0.3889**.
- Error taxonomy final memuat **162 kegagalan/83 query**; lihat `docs/error_taxonomy.md`.

## Setup

| Item | Nilai |
| --- | --- |
| Query | 115 (35 easy / 25 multi-hop / 30 temporal / 25 no-evidence) |
| Qrels | v2 frozen, 2.237 baris, SHA-256 `8ed07e8ebcbefdea332a6a1555b320d0d8c6553f6bffd978cd22894338171926` |
| Query hash | `d5128e48413125b1383e4946580a08f133964fbb8e0d1a7e988f0a143a27b2ac` |
| B2 index | fixed, 5.738 passage |
| B3 index | section, 11.266 passage |
| B2 output | top-5, dense, tanpa filter |
| B3 output | top-10, hybrid RRF + rerank, filter tahun/buku |
| Artifact B2 | `artifacts/runs/retrieval_b2_v2.json` |
| Artifact B3 | `artifacts/runs/retrieval_b3_v2.json` |
| Evaluasi | `--eval-k 10 --retain-k 10 --limit 0` |

B2 memakai `final_k=5` sesuai config. `--eval-k 10` dipakai agar Recall@10 B2 dan B3 dibandingkan pada cutoff yang sama; tanpa flag ini, B2 hanya dievaluasi pada top-5.

## B2 vs B3

| Run | n | R@5 | R@10 | nDCG@10 | MRR@10 | Doc recall | Judged | Test split | p50 ms | p95 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| B2 fixed top-5 | 90 | 0,1052 | 0,1515 | 0,1385 | 0,2187 | 0,3889 | 0,1843 | 0,1843 | 29,4 | 55,1 |
| B3 section top-10 | 90 | 0,3844 | 0,5369 | 0,4531 | 0,5627 | 0,7833 | 0,2539 | 0,2539 | 1.698,6 | 2.509,8 |

### Recall@10 per slice

| Slice | B2 | B3 |
| --- | ---: | ---: |
| easy | 0,2238 | 0,5571 |
| multi-hop | 0,0627 | 0,7060 |
| temporal | 0,1411 | 0,3722 |
| no-evidence | 0,0000 | 0,0000 |

Slice no-evidence tidak punya passage relevan; Recall@10 selalu 0 secara desain dan bukan ukuran kegagalan retrieval.

## Agreement dan freeze qrels v2

| Item | Nilai |
| --- | --- |
| Relevance C/D | n=448, kappa=0.9629, conflicts=6 |
| Relevance Fleiss A/C/D | n=448, kappa=0.9223 |
| Verdict C/D | n=145, kappa=0.4983, conflicts=1 |
| Majority relevance | 18 item |
| Tie | 1 (`q013`, final `1`) |
| Missing labels | A=0, C=0, D=0 |

`q013 / ye-old-american:a-boiled-bread-pudding#fixed#1` memiliki `A=2, C=0, D=1`. Passage masih dalam resep yang sama dan memberi konteks proses memasak, tetapi tidak menyebut durasi `steep`; label partial `1` dipilih.

Finalisasi memakai `benchmark/pool_v2.jsonl` (2.237 key), bukan `pool_v1.jsonl` (1.789 key), agar seluruh kandidat baru ikut masuk.

## Smoke B0/B1

20 query stratifikasi: q001-q005 (easy), q036-q040 (multi-hop), q061-q065 (temporal), q091-q095 (no-evidence).

| Config | n | Schema valid | Abstain | p50 | p95 |
| --- | ---: | ---: | ---: | ---: | ---: |
| B0 zero-shot, tanpa retrieval | 20 | 20/20 (1,00) | 1 | 59,8 s | 147,7 s |
| B1 few-shot, tanpa retrieval | 20 | 18/20 (0,90) | 1 | 50,3 s | 181,4 s |

Artifact: `artifacts/runs/smoke/b0/`, `artifacts/runs/smoke/b1/`.

Temuan kualitatif:

- B0 dan B1 mengarang jawaban untuk topik yang tidak ada di korpus: gas oven, aluminium foil, microwave, food processor, dan kalori.
- B1 gagal schema pada `q001` dan `q005`: model menyalin header contoh dan menulis `schema_valid: false`.
- B0 menjawab `q001` "about 1 hour" padahal gold "one and a half hours"; `q005` "20 eggs" padahal gold "four eggs".
- B0/B1 tidak menghasilkan claims/sitasi; itu desain baseline.

## Gate 2

| Kriteria | Status | Bukti |
| --- | --- | --- |
| qrels v2 frozen | **pass** | `benchmark/qrels.jsonl`, 2.237 baris; manifest ter-regenerate |
| Recall@10 B3 > B2 (passage) | **pass** | 0,5369 > 0,1515 |
| Recall@10 B3 > B2 (doc-level) | **pass** | 0,7833 > 0,3889 |
| Config equality B0-B3 | **pass** | `tests/unit/test_config_equality.py` |

Gate 2 ditutup. Perbandingan final memakai qrels v2 yang sudah memuat label passage `#fixed#`.

## Reproduksi

```powershell
uv run python tools/eval_retrieval.py --config configs/b2.yaml --qrels benchmark/qrels.jsonl --eval-k 10 --retain-k 10 --limit 0 --out artifacts/runs/retrieval_b2_v2.json
uv run python tools/eval_retrieval.py --config configs/b3.yaml --qrels benchmark/qrels.jsonl --eval-k 10 --retain-k 10 --limit 0 --out artifacts/runs/retrieval_b3_v2.json
```

Finalisasi qrels:

```powershell
uv run python tools/finalize_benchmark.py --qrels-a benchmark/qrels_v2_a.jsonl --a-keys benchmark/work/w2-d/keys.jsonl --qrels-c benchmark/qrels_v2_c.jsonl --qrels-d benchmark/qrels_v2_d.jsonl --verdict-c benchmark/verdict_qrels_c.jsonl --verdict-d benchmark/verdict_qrels_d.jsonl --decisions benchmark/adjudication_v2.jsonl --pool benchmark/pool_v2.jsonl --annotator consensus
```

## Pool v2

Dibangun dari pool v1 + top-10 B2 (fixed) + top-10 B3 (section) + top-10 A2 dense/BM25/hybrid (section). Semua kandidat wajib `split=test`.

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

- `benchmark/pool_v2.jsonl`: blinded, hanya `query_id`, `passage_id`, `doc_id`.
- `benchmark/pool_v2_meta.jsonl`: provenance; tidak boleh dibuka anotator.
- `benchmark/pool_v2.sha256`.

## Temuan

1. **B3 jauh lebih baik dari B2** pada passage-level: R@10 0,5369 vs 0,1515, sekitar 3,5x.
2. **Filter metadata adalah faktor utama.** B3 memakai filter tahun/buku; B2 tidak.
3. **B2 masih retrieve lintas split dan lintas tahun.** Hanya 18,43% hasil B2 dari test split; B3 25,39%.
4. **Few-shot bukan otomatis lebih baik.** B1 menurunkan schema validity dari 100% ke 90% pada model 0,5B.
5. **Tanpa retrieval, model berhalusinasi anachronistically** (microwave, aluminium foil, food processor). Slice no-evidence adalah ujian langsung untuk abstain; B0/B1 gagal abstain di 5/5 query no-evidence.
6. **Generation tetap bermasalah meski retrieval B3 membaik.** Audit 24 query menemukan 22 error E3/E5; lihat `docs/error_taxonomy.md`.

## Batasan

- B2 dan B3 berbeda pada chunking, mode retrieval, filter, dan `final_k`. Perbandingan ini system-level, bukan ablasi satu variabel.
- B2 top-5 dievaluasi pada cutoff 10; angka R@10-nya bergantung pada perilaku ranking setelah top-5.
- Smoke B0/B1 hanya 20 query; schema validity belum diuji pada 115 query.
- Qrels v2 tetap memiliki 1 tie yang diputuskan manual; label A ditulis dengan notes, bukan anotasi human murni tanpa bantuan.
- E6-E8 tidak dievaluasi pada taxonomy; statusnya Not Evaluated.

## Laporan terkait

- [`a2_dev.md`](a2_dev.md): evaluasi A2 dense/BM25/hybrid/rerank.
- [`../docs/error_taxonomy.md`](../docs/error_taxonomy.md): taxonomy final.
- [`../docs/handoff/w2-b.md`](../docs/handoff/w2-b.md): handoff B ke C/D.
- [`README.md`](README.md): indeks laporan.
