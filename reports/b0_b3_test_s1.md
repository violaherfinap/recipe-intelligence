# Baseline B0-B3 - test seed 1

- **Tanggal:** 2026-11-25
- **Config:** `configs/b0.yaml` sampai `configs/b3.yaml`
- **Data:** `benchmark/queries.jsonl` (115 query), `benchmark/qrels.jsonl` v2
- **Split:** development evaluation (115 query); tidak ada tuning pada run ini
- **Artefak:** `artifacts/runs/b0-test-s1/` sampai `artifacts/runs/b3-test-s1/`
  (lokal, gitignored)

> Sejak split 65/50 (Week 3), angka test final hanya dihitung dari
> `benchmark/queries_test.jsonl` (50 query). Laporan ini dipertahankan sebagai
> evaluasi pengembangan 115 query, bukan test final.

## Ringkasan

| Config | n | Schema valid | Schema rate | Abstain | p50 ms | p95 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| B0 | 115 | 107 | 0.9304 | 10 | 14.691,8 | 24.140,7 |
| B1 | 115 | 108 | 0.9391 | 7 | 13.924,6 | 18.195,5 |
| B2 | 115 | 113 | 0.9826 | 2 | 20.932,6 | 29.846,3 |
| B3 | 115 | 103 | 0.8957 | 12 | 20.915,2 | 39.326,0 |

## Catatan

- B3 dijalankan ulang penuh setelah run sebelumnya terhenti; artefak final
  berasal dari satu run 115 query dengan `exit=0`.
- B3 unggul retrieval di Gate 2, tetapi schema validity lebih rendah dari B2
  pada run generation ini. Jangan menyimpulkan kualitas jawaban dari schema
  validity saja; evaluasi claim/verdict tetap diperlukan.
- Baseline ini memakai kode P0+A dengan planner/retry **disabled** untuk
  B0-B3, sehingga jalur retrieval/generation lama tidak berubah.
- Metrik retrieval B2/B3 ada di `artifacts/runs/retrieval_b2_v2.json` dan
  `retrieval_b3_v2.json`; laporan ini fokus pada run end-to-end.
