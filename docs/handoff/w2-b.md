# Handoff W2-B — eksekusi retrieval dan pool v2

- **Owner:** B
- **Branch:** `feat/w2-b-eval-pool`
- **Base:** `origin/feat/w2-a-retrieval` (`75942de`)
- **Tanggal:** 2026-11-19
- **Status:** selesai untuk qrels v1.1; Gate 2 passage-level menunggu qrels v2
- **Handoff ke:** C (anotasi pool v2), lalu D (qrels v2 + Gate 2)

## Ringkasan

B menjalankan bagian eksekusi Week 2: smoke B0/B1, evaluasi A2 penuh, evaluasi
B2/B3, dan pembangunan pool v2. Semua angka berasal dari artifact di
`artifacts/runs/`; tidak ada angka yang ditulis tanpa run.

## Angka kunci

| Item | Nilai |
| --- | ---: |
| Query dievaluasi | 115 (90 answerable) |
| B0 schema valid | 20/20 (smoke 20 query) |
| B1 schema valid | 18/20 (smoke 20 query) |
| A2 dense R@10 | 0,3019 |
| A2 BM25 R@10 | 0,3917 |
| A2 hybrid R@10 | 0,4324 |
| A2 hybrid+rerank+filter R@10 | **0,7120** |
| A2 hybrid+rerank tanpa filter R@10 | 0,4102 |
| B2 passage R@10 | 0,0000 (struktural; belum ada qrels fixed) |
| B2 doc recall | 0,2889 |
| B3 passage R@10 | **0,7120** |
| B3 doc recall | **0,7833** |
| Pool v2 kandidat | 2.237 |
| Pool v2 kandidat baru | 448 |
| Pool v2 median/query | 19 |

## Artefak

| Artefak | Path |
| --- | --- |
| Laporan A2 | `reports/a2_dev.md` |
| Laporan B2/B3 + smoke + pool | `reports/b2b3_dev.md` |
| Tool evaluasi retrieval | `tools/eval_retrieval.py` |
| Tool smoke/batch | `tools/run_config.py` |
| Pool v2 builder | `tools/build_pool_v2.py`, `src/recipe_qa/benchmark/pool_v2.py` |
| Coverage metrics | `src/recipe_qa/eval/metrics/coverage.py` |
| Pool v2 blinded | `benchmark/pool_v2.jsonl`, `benchmark/pool_v2.sha256` |
| Pool v2 provenance | `benchmark/pool_v2_meta.jsonl` (jangan dibuka anotator) |
| Smoke B0/B1 | `artifacts/runs/smoke/b0/`, `artifacts/runs/smoke/b1/` |
| Run A2 | `artifacts/runs/a2_*_full.json` |
| Run B2/B3 | `artifacts/runs/retrieval_b2_full.json`, `retrieval_b3_full.json` |

## Temuan penting

1. **Filter metadata adalah sumber gain terbesar.** Hybrid+rerank+filter 0,7120;
   hybrid+rerank tanpa filter hanya 0,4102. Jangan klaim “reranker memberi gain”
   tanpa memisahkan efek filter.
2. **B2 passage-level tidak terukur.** qrels v1.1 tidak memuat `#fixed#`; semua
   Recall B2 = 0 secara struktural. Gunakan doc-level (0,2889) sampai qrels v2.
3. **Sebagian besar hasil retrieval adalah train/dev.** Pool v2 membuang 4.492
   kandidat non-test. Test split rate A2 hanya 18,6%–25,4%. Angka qrels v1.1
   adalah lower bound.
4. **B1 few-shot menurunkan schema validity** dari 100% (B0) ke 90% (B1) pada
   20 query; model menyalin header contoh dan menulis `schema_valid: false`.
5. **B0/B1 berhalusinasi** pada query no-evidence: microwave, aluminium foil,
   food processor, kalori. Tidak ada abstain di 5/5 query no-evidence.

## Verifikasi

```powershell
uv run pytest -q
uv run ruff check src tests tools
uv run python tools/validate_benchmark.py --strict
uv run python tools/audit_qrels.py compare
```

- `pytest`: **127 test lulus**.
- `ruff`: bersih.
- `validate_benchmark.py --strict`: valid.
- `audit_qrels.py compare`: 181 confirm, 2 change, 0 mismatch.
- Query hash dan qrels hash tidak berubah.

## Instruksi untuk C

Baca `benchmark/guidelines.md` §7 (Pool v2) dan §9. Anotasi **hanya kandidat
baru** dengan seed qrels v1.1:

```powershell
Copy-Item benchmark/qrels.jsonl benchmark/qrels_v2_c.jsonl

uv run python tools/annotate.py relevance --annotator C `
  --queries benchmark/queries.jsonl `
  --pool benchmark/pool_v2.jsonl `
  --passages data/processed/passages.jsonl data/processed/passages_fixed.jsonl `
  --out benchmark/qrels_v2_c.jsonl
```

- Jangan membuka `benchmark/pool_v2_meta.jsonl`.
- Jangan mengubah `benchmark/queries.jsonl`.
- Passage `#fixed#` dinilai dengan skala 0/1/2 yang sama.
- Target: 448 item baru selesai; item lama otomatis dilewati karena sudah ada
  di seed qrels.

## Instruksi untuk D

1. Seed qrels v1.1 ke `benchmark/qrels_v2_d.jsonl`.
2. Anotasi pass 2 blind pada 448 item baru; jangan melihat label C.
3. Hitung κ relevance pada item baru; adjudikasi konflik.
4. Tulis `benchmark/qrels.jsonl` v2 dan regenerate
   `benchmark/manifest.sha256`.
5. Jalankan ulang B2/B3 dan tutup Gate 2:

```powershell
uv run python tools/eval_retrieval.py --config configs/b2.yaml `
  --limit 0 --retain-k 10 --out artifacts/runs/retrieval_b2_v2.json
uv run python tools/eval_retrieval.py --config configs/b3.yaml `
  --limit 0 --out artifacts/runs/retrieval_b3_v2.json
```

6. Spot-check 5 query no-evidence di pool v2.

## Catatan terbuka

| ID | Isu | Dampak |
| --- | --- | --- |
| Q10 | Tidak ada dev query set | W2 memakai 115 query beku sebagai evaluation set tanpa tuning; dev murni dibutuhkan untuk kalibrasi B4 |
| Q11 | qrels v1.1 tidak punya passage fixed | B2 passage-level dan Gate 2 menunggu qrels v2 |
| Q12 | 2 atau 3 anotator untuk qrels v2? | Tool sudah menerima `--annotator A`; putuskan sebelum C mulai |

## Batasan yang harus ikut ditulis

- B2 vs B3 berbeda pada chunking, mode, filter, dan `final_k`; ini perbandingan
  system-level, bukan ablasi satu variabel.
- B1 vs B2 berbeda pada `prompt.few_shot` (deviasi A).
- Angka A2/B3 adalah lower bound karena pool qrels belum lengkap.
- Latency diukur di CPU tanpa generation bersamaan; rerank ±1,9 s p50,
  hybrid ±61 ms, dense ±248 ms, BM25 <1 ms.
