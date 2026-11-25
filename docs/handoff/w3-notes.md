# Week 3 - catatan peringatan dan urutan kerja

- **Tanggal:** 2026-11-25
- **Status:** P0 (grounding gate), A (planner/retry/B4), dan baseline B0-B3 test
  sudah selesai; kalibrasi dev masih blocker
- **Basis:** `benchmark/qrels.jsonl` v2 frozen, tag `benchmark-v2`
- **Laporan P0:** `reports/a3_verify_dev.md`
- **Laporan baseline:** `reports/b0_b3_test_s1.md`
- **Branch A:** `feat/w3-a-planner-b4` (di atas `feat/w3-p0-grounding`)

## Prioritas error (dari taxonomy Week 2)

| Prioritas | Kode | Bukti | Fokus |
| --- | --- | --- | --- |
| P0 | E5, E7, E8 | 6/6 no-evidence berhalusinasi di sample audit | verifier, abstain, repair; **sudah ada** |
| P1 | E1 genuine (84) | temporal 49, easy 19, multi-hop 16 | planner dekomposisi + retry |
| P1 | E3 (14) | multi-hop 5, temporal 6, easy 3 | planner, verifier, LoRA residual |
| P2 | E1 easy (19) | ranking/coverage | tuning retrieval di dev |
| P3 | E2 (6) | rank-1 tanpa gold | rerank/filter/planner |
| Maintain | E4 (0) | tidak ada pelanggaran `as_of` | regression test |
| Jangan dikejar | 50 E1 `#fixed#` | beda chunking, struktural | laporkan per-chunking |

Catatan: 50 dari 134 E1 adalah gold `#fixed#` yang tidak mungkin muncul di B3
section. Jangan klaim sebagai kegagalan yang bisa "diperbaiki" tanpa mengganti
chunking.

## Peringatan wajib Week 3

### Blocker

1. **Dev set belum ada (Q10).** Jangan kalibrasi threshold NLI, τ sufficiency,
   atau parameter planner di 115 query test. Buat dev query + label dev lebih
   dulu; freeze hash.
2. **Bekukan baseline B0-B3 test seed 1** dengan qrels v2 sebelum mengubah kode.
   Tanpa baseline, klaim perbaikan tidak sah.
3. **Jangan ubah query/qrels test** tanpa versi baru dan regenerate manifest.

### Metodologi

4. **A3 harus ablation bersih.** `configs/a3_verify.yaml` = B3 + verifier.
   Sufficiency ada di `configs/a3_verify_suff.yaml`; jangan campur dalam klaim
   A3.
5. **Sufficiency belum terkalibrasi.** Proxy 115 query: abstain easy 17/35,
   multi-hop 23/25, temporal 27/30, no-evidence 25/25. Terlalu agresif; jangan
   aktifkan di test sebelum dev.
6. **Error taxonomy harus chunking-aware.** Rerun setelah B4 dengan chunking
   yang sama; jangan membandingkan E1 lintas chunking.
7. **E3/E5 hanya sample 24 query generation.** Perluas audit sebelum klaim
   penurunan; laporkan n per slice.
8. **Jangan menaikkan `final_k` lalu mengklaim gain.** Evaluasi tetap `eval-k 10`;
   laporkan token/latency jika budget berubah.
9. **Laporkan n, mean, CI bootstrap (1.000 resample)** untuk metrik utama.

### Risiko teknis

10. **Label NLI bisa tertukar.** Mapping dibaca dari `id2label`; uji dengan
    pasangan known. Catat model hash/versi.
11. **Abstain dua arah.** Ukur abstain recall dan false refusal. `keep_refuted=false`
    membuang klaim REFUTED; ini bisa menjadi false refusal pada fact-checking.
12. **Verifier tidak memperbaiki entity swap.** `q071` residual membuktikan
    butuh planner/retrieval, bukan NLI.
13. **Temporal regression.** E4 = 0 sekarang; tambah test agar `as_of` filter
    tidak hilang saat planner/retry masuk.
14. **Budget/latency.** Sample P0 p50 29,2 s, p95 55,2 s. Retry dan repair
    memperpanjang tail; laporkan p50/p95 + token.
15. **LoRA:** hanya train split, tanpa passage test, base model sama, catat hash
    + resource + train-dev gap, 3 seed subset; mulai setelah B4 stabil.
16. **Tool misuse (E6)** belum diukur; butuh B6 controller + authorization.

### Urutan Week 3

1. A: baseline B0-B3 test (seed 1) -> planner -> sufficiency + kalibrasi τ di
   dev -> retry -> B4.
2. B: NLI verifier -> citation/temporal check -> abstain -> kalibrasi verifier
   -> evaluasi B4 dev.
3. C: dataset LoRA 600-800 (train only) -> training CPU -> evaluasi B5 dev +
   OOD -> resource.
4. D: A3/A4/A6 -> run B4/B5 test seed 1 -> 3 seed subset -> variance.
5. Gate 3: adapter + B5 eval + A3/A4/A6 + test B4/B5, semua artefak ber-hash.

## Status P0 saat ini

- Verifier, claim splitting, repair, dan abstain policy sudah terintegrasi.
- Bukti sample: 21/22 error generation diblokir; `q021` benar dipertahankan;
  `q060` NE menjadi abstain `format_error`; 6/6 no-evidence abstain.
- Sisa: kalibrasi dev, A3 penuh 115 query, planner untuk E1/E3.

## Status A saat ini

- `src/recipe_qa/pipeline/planner.py`: planner LLM (`planner_v1`) dengan
  fallback rule-based untuk dekomposisi tahun dan entitas `both ... and ...`.
- `src/recipe_qa/pipeline/retry.py`: maksimal 2 reformulasi, dipicu oleh
  `retry.min_sufficiency`; tidak melebihi budget.
- `src/recipe_qa/pipeline/common.py`: planner -> retrieve -> retry ->
  sufficiency -> generate -> verify; metadata `plan`/`retry` hanya ditulis
  saat fitur aktif agar output B0-B3 tidak berubah.
- `configs/b4.yaml`: B3 + planner LLM + retry 2 + verifier NLI + abstain.
  `abstain.sufficiency` tetap `false` sampai τ dikalibrasi di dev.
- `tools/calibrate_sufficiency.py` dan
  `src/recipe_qa/eval/sufficiency_calibration.py`: siap dipakai setelah dev
  query+label tersedia; jangan kalibrasi di 115 query test.
- Unit test baru mencakup planner rule/LLM/fallback, retry bound, integrasi
  pipeline, dan kalibrasi sintetis.
- Baseline B0-B3 test seed 1 selesai 115 query/config; ringkasan di
  `reports/b0_b3_test_s1.md`. Artefak: `artifacts/runs/b0-test-s1/` sampai
  `b3-test-s1/` (lokal).
- B4 smoke 2 query test (`q061`, `q036`): pipeline jalan, metadata `plan` dan
  `retry` terisi, tetapi keduanya abstain (satu `format_error`). Planner LLM
  0.5B sering menghasilkan subquery tidak layak, sehingga fallback rule-based
  yang dipakai. Ini smoke integrasi, bukan evaluasi kualitas.
- Selanjutnya: buat dev query+label, kalibrasi τ/NLI di dev, lalu jalankan B4
  20 query dev. Jangan memakai 115 query test untuk tuning.
