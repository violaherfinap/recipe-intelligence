# Error Taxonomy

**Status: final untuk Week 2; re-check post-P0 2026-11-25.** Memakai qrels v2 frozen (`benchmark/qrels.jsonl`, 2.237 baris, SHA-256 `8ed07e8e...`) dan run final `artifacts/runs/retrieval_b3_v2.json`.

## Definisi

| Kode | Arti | Status |
| :--- | :--- | :--- |
| E1 | Retrieval miss: bukti relevan ada tetapi tidak masuk top-k | Evaluated |
| E2 | Wrong passage: peringkat 1 berasal dari dokumen tanpa passage relevan | Evaluated |
| E3 | Reasoning error: bukti benar, penalaran atau pemilihan entitas salah | Evaluated |
| E4 | Temporal error: memakai bukti di luar `as_of` | Evaluated |
| E5 | Overclaim: klaim melebihi isi bukti, termasuk halusinasi no-evidence | Evaluated |
| E6 | Tool misuse | Not Evaluated |
| E7 | Format error: JSON/schema tidak valid | Not Evaluated |
| E8 | Abstain wrong | Not Evaluated |

E6–E8 sengaja tidak dilaporkan sebagai nol; statusnya **Not Evaluated**. Satu format error (`q060`) ditemukan pada audit generation dan dicatat sebagai NE, bukan E3/E5.

## Metode

- Retrieval: B3 final top-10 terhadap qrels v2; E1/E2/E4 dihasilkan oleh `tools/analyze_retrieval_errors.py`.
- Generation: 24 query stratified (6 easy, 6 multi-hop, 6 temporal, 6 no-evidence) dari `artifacts/runs/error_b3_generation/results.jsonl`, direview manual.
- Satu baris = satu kegagalan. Satu query dapat menghasilkan beberapa baris E1.
- Qrels v2 menggabungkan majority A/C/D; satu tie `q013` diputuskan final `1`.

## Hasil Final

| Kode | Jumlah baris |
| :--- | ---: |
| E1 | 134 |
| E2 | 6 |
| E3 | 14 |
| E4 | 0 |
| E5 | 8 |
| E6–E8 | Not Evaluated |
| **Total** | **162** |

- Unique query dengan kegagalan: **83**.
- Distribusi slice: temporal 77, easy 51, multi-hop 28, no-evidence 6.
- Generation audit: 24 query, 22 error, 1 benar (`q021`), 1 NE (`q060`).
- Target minimal 50 kegagalan terpenuhi: 83 query unik dan 162 baris kegagalan.

## Artefak

- `error_analysis.csv`: gabungan final 162 baris, ID `ERR0001`–`ERR0162`.
- `benchmark/work/w2-d/error_analysis_retrieval_final.csv`: 140 baris E1/E2/E4.
- `benchmark/work/w2-d/error_retrieval_provisional.csv`: artefak provisional, bukan hasil final.
- `benchmark/work/w2-d/error_generation_review.csv`: review 24 query generation.
- `benchmark/work/w2-d/error_analysis_generation.csv`: 22 error E3/E5.
- `artifacts/runs/retrieval_b3_v2.json`: run retrieval final.
- `artifacts/runs/retrieval_b2_v2.json`: run B2 final untuk Gate 2.

## Gate 2

| Metrik | B2 | B3 |
| :--- | ---: | ---: |
| Recall@5 | 0.1052 | 0.3844 |
| Recall@10 | 0.1515 | 0.5369 |
| nDCG@10 | 0.1385 | 0.4531 |
| MRR@10 | 0.2187 | 0.5627 |
| Doc recall | 0.3889 | 0.7833 |

B2 memakai `final_k=5`; evaluasi memakai `--eval-k 10` agar perbandingan passage-level adil. B3 mengalahkan B2 pada seluruh metrik.

## Re-check post-P0 (2026-11-25)

P0 grounding gate (verifier NLI + abstain + repair) sudah diimplementasikan;
lihat `reports/a3_verify_dev.md`. Re-check ini **tidak mengubah angka final
Week 2**, hanya menambahkan pembacaan ulang dan hasil setelah mitigasi.

### Retrieval (dihitung ulang)

`tools/analyze_retrieval_errors.py` mereproduksi **140 baris identik**:

| Kode | Baris |
| --- | ---: |
| E1 | 134 |
| E2 | 6 |
| E4 | 0 |

Rincian E1:

| Pecahan | Baris |
| --- | ---: |
| Label relevansi 2 / 1 | 106 / 28 |
| Gold `#fixed#` (struktural untuk B3 section) | 50 |
| Gold section (`#ingredients#` + `#directions#`) | 84 |
| E1 genuine: temporal / easy / multi-hop | 49 / 19 / 16 |

**50 E1 `#fixed#` tidak boleh dihitung sebagai kegagalan yang bisa
"diperbaiki"** tanpa mengganti chunking; target perbaikan riil adalah 84 E1
section.

### Generation (24 query audit, post-P0)

| Item | Baseline | Setelah P0 |
| --- | ---: | ---: |
| Error E3/E5 | 22 | **1 residual** (`q071`) |
| Error diblokir (abstain) | 0 | **21 / 22** |
| Jawaban benar (`q021`) | dijawab | tetap dijawab |
| NE `q060` (format) | NE | abstain `format_error` |
| No-evidence abstain | 0 / 6 | **6 / 6** |
| Latency p50 / p95 | - | 29,2 s / 55,2 s |

`q071` residual adalah entity swap (brandy vs soda) yang tidak terdeteksi NLI;
ini batas verifier, bukan E5. Angka generation ini hanya sample 24 query, bukan
115 query.

### Artefak re-check

- `artifacts/runs/error_taxonomy_recheck.csv` (140 baris retrieval, identik).
- `artifacts/runs/error_taxonomy_recheck_summary.json` (ringkasan gabungan).
- `artifacts/runs/a3_verify_sample14_v2/`, `a3_verify_generation_rest/`,
  `a3_verify_check2/` (hasil generation post-P0).
- `reports/a3_verify_dev.md` (detail implementasi dan batasan).
