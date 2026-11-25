# Error Taxonomy

**Status: final.** Memakai qrels v2 frozen (`benchmark/qrels.jsonl`, 2.237 baris, SHA-256 `8ed07e8e...`) dan run final `artifacts/runs/retrieval_b3_v2.json`.

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
