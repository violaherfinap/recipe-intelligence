# B4 final - test-50 seed 1

- **Tanggal:** 2026-11-26
- **Owner:** A (Lois)
- **Config:** `configs/b4.yaml`
- **Config freeze:** commit `a6b7a26`, tag `w3-config-frozen`
- **Data:** `benchmark/queries_test.jsonl` (50 query), qrels v2
- **Seed:** 1
- **Artefak:** `artifacts/runs/b4-test50-s1/` (lokal, gitignored)

## Freeze yang diuji

| Parameter | Nilai |
| --- | --- |
| Retrieval | `hybrid_rerank`, section, final_k 10, filter aktif |
| Planner | `llm`, maks. 3 subquery |
| Retry | maks. 2, `min_sufficiency` 0,35 |
| NLI | `cross-encoder/nli-deberta-v3-base`, threshold 0,5, `premise_context: true` |
| Sufficiency | aktif, tau **0,17** |
| Citation/temporal gate | aktif |
| `keep_refuted` | false |

## Ringkasan overall

| Item | Nilai |
| --- | ---: |
| Query | 50 |
| Schema valid | 49 (0,9800) |
| Abstain | 39 (0,7800) |
| Latency p50 | 43.441,1 ms |
| Latency p95 | 82.027,8 ms |
| Latency mean | 45.565,9 ms |

Verifikasi:

| Item | Nilai |
| --- | ---: |
| Query dengan metadata verification | 31 |
| Klaim SUPPORTED | 14 |
| Klaim REFUTED | 9 |
| Klaim dropped | 24 |
| Query abstain karena verifikasi | 20 |

## Per slice

| Slice | n | Schema valid | Abstain | p50 ms | p95 ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| easy | 15 | 15 | 10 (0,6667) | 39.596,6 | 68.094,6 |
| multi-hop | 11 | 10 | 8 (0,7273) | 45.173,4 | 130.330,9 |
| no-evidence | 11 | 11 | 10 (0,9091) | 22.563,8 | 169.964,3 |
| temporal | 13 | 13 | 11 (0,8462) | 50.074,6 | 59.289,9 |

## Kenapa abstain

| Sumber abstain | Jumlah |
| --- | ---: |
| Sufficiency `abstained=true` | 17 |
| Upstream/verifikasi (trigger `upstream_abstain`) | 39 total |
| `abstain_reason = not_specified` | 38 |
| `abstain_reason = format_error` | 1 |

Hanya 17 dari 39 abstain berasal dari tau sufficiency; sisanya dipicu
verifikasi NLI (`abstain_on_unsupported`) dan pembuangan klaim tanpa dukungan.
Artinya abstain tinggi di test-50 bukan efek tau saja.

## Jawaban yang tidak abstain

11 query menghasilkan jawaban: `q008`, `q012`, `q017`, `q031`, `q035`, `q051`,
`q057`, `q059`, `q062`, `q085`, `q099`.

- Klaim yang lolos semuanya `SUPPORTED` (14 klaim); tidak ada `REFUTED` yang
  dipertahankan karena `keep_refuted=false`.
- **Temuan penting:** `q099` (no-evidence) menghasilkan 3 klaim `SUPPORTED`.
  Ini false confident verdict pada slice no-evidence dan harus masuk audit E5/E7.
- `q062` (temporal, 1851 vs 1871 baked apples) dijawab "both ... peel the
  apples" padahal passage 1871 menyebut "wash, but do not pare them". Verifier
  tidak menangkap perbedaan ini; ini residual E3/E4 yang perlu diperiksa di A3.

## Perbandingan dengan baseline test-50

| Config | Schema rate | Abstain | p50 ms | p95 ms |
| --- | ---: | ---: | ---: | ---: |
| B3 | 0,8600 | 7 (0,1400) | 20.168,5 | 57.353,4 |
| B4 | 0,9800 | 39 (0,7800) | 43.441,1 | 82.027,8 |

B4 menaikkan schema validity tetapi jauh lebih konservatif (abstain 78%).
Jangan menyimpulkan kualitas akhir hanya dari schema validity; lihat juga
macro-F1 klaim, false refusal, dan false confident verdict.

## Guardrail

- Test-50 dijalankan **setelah** `w3-config-frozen`; tidak ada parameter yang
  dipilih dari hasil test ini.
- Tau 0,17 dan threshold NLI 0,5 berasal dari train-65 saja.
- Angka final ini dibekukan untuk perbandingan berikutnya; perubahan config
  setelah titik ini memerlukan tag baru.

## Reproduksi

```powershell
git switch -c feat/w3-a-calibration w3-config-frozen

uv run python tools/run_config.py --config configs/b4.yaml `
  --queries benchmark/queries_test.jsonl --limit 0 `
  --out-dir artifacts/runs/b4-test50-s1
```
