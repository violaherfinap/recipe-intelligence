# Sufficiency tau calibration - train-65

- **Tanggal:** 2026-11-26
- **Owner:** A (Lois)
- **Config run:** `configs/b4_calib.yaml`
- **Data:** `benchmark/queries_train.jsonl` (65 query)
- **Label:** `benchmark/qrels.jsonl` v2, `relevance >= 1` dianggap answerable
- **Artefak angka:** `artifacts/runs/b4-calib-train65/tau.json` (lokal)

## Hasil

| Item | Nilai |
| --- | ---: |
| Threshold terpilih (tau) | **0,17** |
| Balanced accuracy | **0,8305** |
| Query dinilai | 65 |
| Answerable (`relevance >= 1`) | 51 |
| No-evidence | 14 |
| n = 65 | 51 / 14 |

Balanced accuracy dihitung sebagai rata-rata true-positive rate pada query
answerable dan true-negative rate pada no-evidence. Tau 0,17 dipilih karena
memberi balanced accuracy tertinggi pada sweep 0,00-1,00 (step 0,01); nilai
lama 0,35 hanya mencapai 0,6800.

## Ringkasan run kalibrasi

`configs/b4_calib.yaml` dijalankan pada 65 query train (tanpa test-50):

| Item | Nilai |
| --- | ---: |
| Query | 65 |
| Schema valid | 63 (0,9692) |
| Abstain end-to-end (tau 0,35 saat run) | 58 (0,8923) |
| Latency p50 | 30.689,3 ms |
| Latency p95 | 80.269,3 ms |

Per slice:

| Slice | n | Schema valid | Abstain |
| --- | ---: | ---: | ---: |
| easy | 20 | 20 | 14 |
| multi-hop | 14 | 13 | 14 |
| no-evidence | 14 | 13 | 14 |
| temporal | 17 | 17 | 16 |

## Keputusan freeze

`configs/b4.yaml` di-freeze dengan:

- `verification.premise_context: true` (rekomendasi B; balanced accuracy NLI
  0,8676 vs 0,6225 tanpa konteks).
- `verification.nli_threshold: 0.5` (dataran tertinggi 0,30-0,50).
- `abstain.sufficiency: true`, `abstain.sufficiency_threshold: 0.17`.
- `abstain.citations: true`, `abstain.temporal: true`.
- `retry.min_sufficiency` tetap 0,35 (parameter retry terpisah dari tau abstain).

## Reproduksi

```powershell
uv run python tools/run_config.py --config configs/b4_calib.yaml `
  --queries benchmark/queries_train.jsonl --limit 0 `
  --out-dir artifacts/runs/b4-calib-train65

uv run python tools/calibrate_sufficiency.py `
  --results artifacts/runs/b4-calib-train65/results.jsonl `
  --qrels benchmark/qrels.jsonl `
  --out artifacts/runs/b4-calib-train65/tau.json
```

## Batasan

- Label answerable memakai `relevance >= 1`, bukan verdict klaim.
- 51 answerable vs 14 no-evidence membuat balanced accuracy lebih sensitif
  pada 14 query no-evidence.
- Tau dipilih di train-65; angka final B4 tetap dari test-50 setelah freeze.
