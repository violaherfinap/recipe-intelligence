# B4 final - train-65 seed 1

- **Tanggal:** 2026-11-28
- **Owner report:** B (Anin)
- **Owner run:** A (Lois), 2026-11-28
- **Config:** `configs/b4.yaml` (frozen)
- **Config freeze:** commit `a6b7a26`, tag `w3-config-frozen`
- **Config SHA-256:** `57339e7b6b4a9d06630f26d7485d80d7fc2e5469c1fe5ab35831b240029c6a44`
- **Data:** `benchmark/queries_train.jsonl` (65 query), qrels v2
- **Seed:** 1
- **Artefak:** `artifacts/runs/b4-train65-s1/` (lokal, gitignored)
  - `results.jsonl` SHA-256: `8db0f7dc3132dacceb1ee7dbdaf429e92a06e329617e60024d49cb99d28a299c`
  - `summary.json` SHA-256: `07bfe0fa9a455f842b673f31a7eaeecf552082a9eb4acceb3e6f1e8012e64fee`

Report ini ditulis dari artefak run A; tidak ada run duplikat. Angka train-65
adalah angka split kalibrasi, bukan angka final test.

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
| Query | 65 |
| Schema valid | 61 (0,9385) |
| Abstain | 48 (0,7385) |
| Latency p50 | 40.081,7 ms |
| Latency p95 | 128.439,7 ms |
| Latency mean | 45.914,2 ms |

Verifikasi:

| Item | Nilai |
| --- | ---: |
| Query dengan metadata verification | 38 |
| Klaim SUPPORTED | 17 |
| Klaim REFUTED | 12 |
| Klaim dropped | 33 |
| Query abstain karena verifikasi | 21 |

## Per slice

| Slice | n | Schema valid | Abstain | p50 ms | p95 ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| easy | 20 | 20 | 8 (0,4000) | 42.588,6 | 72.420,5 |
| multi-hop | 14 | 11 | 13 (0,9286) | 42.716,0 | 128.911,9 |
| no-evidence | 14 | 13 | 14 (1,0000) | 20.795,9 | 43.636,3 |
| temporal | 17 | 17 | 13 (0,7647) | 41.809,3 | 64.147,5 |

## Sumber abstain

| Sumber | Jumlah |
| --- | ---: |
| Sufficiency `abstained=true` | 22 |
| Verifikasi NLI (`abstained`) | 21 |
| `format_error` | 4 |
| Generator abstain sendiri | 1 |
| **Total** | **48** |

Rincian per slice:

| Slice | Dijawab | Sufficiency | Verifikasi | format_error | Generator |
| --- | ---: | ---: | ---: | ---: | ---: |
| easy | 12 | 1 | 6 | 0 | 1 |
| multi-hop | 1 | 2 | 8 | 3 | 0 |
| no-evidence | 0 | 12 | 1 | 1 | 0 |
| temporal | 4 | 7 | 6 | 0 | 0 |

Di train-65 sufficiency menangkap 12 dari 14 query no-evidence. Satu query
abstain karena generator sendiri (`q014`), tanpa verifikasi.

## Jawaban yang tidak abstain

17 query: `q003`, `q009`, `q010`, `q013`, `q016`, `q020`, `q021`, `q023`,
`q024`, `q029`, `q032`, `q034`, `q044`, `q070`, `q083`, `q086`, `q090`.

## False refusal (proxy)

Label answerable memakai `qrels.jsonl` `relevance >= 1`, bukan verdict klaim.

| Slice | Answerable | Abstain | Proporsi |
| --- | ---: | ---: | ---: |
| easy | 20 | 8 | 0,4000 |
| multi-hop | 14 | 13 | 0,9286 |
| temporal | 17 | 13 | 0,7647 |
| **Total answerable** | **51** | **34** | **0,6667** |

Semua 14 query no-evidence abstain (1,0000). Jadi 34 dari 51 query yang punya
passage relevan tetap tidak dijawab. Ini batas atas false refusal, karena
`relevance >= 1` tidak menjamin jawaban numerik tersedia untuk pertanyaan.

## Perbandingan train-65 vs test-50

Kedua kolom adalah hasil `configs/b4.yaml` pada dua split berbeda. Train-65
dipakai untuk kalibrasi tau/NLI; test-50 tidak dipakai memilih parameter.

| Metrik | Train-65 (n=65) | Test-50 (n=50) |
| --- | ---: | ---: |
| Schema valid | 0,9385 | 0,9800 |
| Abstain | 0,7385 | 0,7800 |
| Abstain dari sufficiency | 22 dari 48 | 17 dari 39 |
| Latency p50 | 40.081,7 ms | 43.441,1 ms |

Selisih abstain +4,2 poin dan schema valid +4,2 poin. Over-abstain muncul di
kedua split, jadi bukan efek test-50.

## Batasan

- `relevance >= 1` adalah proxy answerable, bukan label verdict klaim.
- 4 `format_error` tidak dianalisis lebih jauh di report ini.
- Angka train-65 tidak boleh dipakai sebagai angka final atau untuk memilih
  parameter test-50.
- Analisis penyebab abstain ada di `reports/verifier_audit.md`, bukan di sini.

## Reproduksi

```powershell
git switch -c feat/w3-b-b4-train65 w3-config-frozen

uv run python tools/run_config.py --config configs/b4.yaml `
  --queries benchmark/queries_train.jsonl --limit 0 `
  --out-dir artifacts/runs/b4-train65-s1
```

Verifikasi artefak:

```powershell
Get-FileHash artifacts/runs/b4-train65-s1/results.jsonl -Algorithm SHA256
Get-FileHash artifacts/runs/b4-train65-s1/summary.json -Algorithm SHA256
```

## Guardrail

- Tidak ada parameter yang dipilih dari angka di report ini.
- Config, thresholds, dan seed sama dengan `w3-config-frozen`.
- Passage test tidak dipakai; report ini hanya membaca query train-65.
