# Baseline B0-B3 - test-50 seed 1

- **Tanggal:** 2026-11-26
- **Owner:** A (Lois)
- **Config:** `configs/b0.yaml` sampai `configs/b3.yaml`
- **Data:** `benchmark/queries_test.jsonl` (50 query), qrels v2
- **Split:** test-50 (angka final), seed 1
- **Artefak:** `artifacts/runs/b0-test50-s1/` sampai `b3-test50-s1/` (lokal, gitignored)

## Metode

Baseline test-50 diturunkan dari run beku 115 query seed 1 (`artifacts/runs/b0-test-s1/`
sampai `b3-test-s1/`) dengan memfilter `query_id` yang ada di
`benchmark/queries_test.jsonl`. Ini sah karena:

1. Konfigurasi B0-B3 tidak berubah sejak run 115 query.
2. Generator memakai `torch.manual_seed(seed)` pada setiap panggilan, sehingga
   output per query deterministik dan tidak bergantung pada urutan query.
3. Probe ulang `q002` dan `q004` pada B0 menghasilkan `answer` dan `claims`
   yang identik dengan run 115 query.

Dengan demikian angka di bawah setara dengan menjalankan ulang 50 query,
tanpa membakar compute untuk generasi yang sama.

Script reproduksi:

```powershell
uv run python -c @"
import json
from pathlib import Path
from tools.run_config import summarize

test_ids = [json.loads(l)['query_id'] for l in open('benchmark/queries_test.jsonl', encoding='utf-8')]
test_set = set(test_ids)
for cfg in ['b0', 'b1', 'b2', 'b3']:
    src = Path('artifacts/runs') / f'{cfg}-test-s1' / 'results.jsonl'
    rows = [json.loads(l) for l in open(src, encoding='utf-8')]
    subset = [r for r in rows if r['query_id'] in test_set]
    assert len(subset) == len(test_ids)
    out = Path('artifacts/runs') / f'{cfg}-test50-s1'
    out.mkdir(parents=True, exist_ok=True)
    with open(out / 'results.jsonl', 'w', encoding='utf-8') as h:
        for r in subset:
            h.write(json.dumps(r, ensure_ascii=False) + '\n')
    summary = {'config': cfg, 'config_path': f'configs/{cfg}.yaml', 'queries': len(subset), **summarize(subset)}
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
"@
```

## Ringkasan overall

| Config | n | Schema valid | Schema rate | Abstain | Abstain rate | p50 ms | p95 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| B0 | 50 | 47 | 0.9400 | 4 | 0.0800 | 15.131,9 | 24.214,2 |
| B1 | 50 | 47 | 0.9400 | 4 | 0.0800 | 13.025,6 | 18.700,0 |
| B2 | 50 | 50 | 1.0000 | 0 | 0.0000 | 20.259,2 | 32.843,1 |
| B3 | 50 | 43 | 0.8600 | 7 | 0.1400 | 20.168,5 | 57.353,4 |

## Per slice

| Config | Slice | n | Schema valid | Abstain | p50 ms | p95 ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| B0 | easy | 15 | 15 | 0 | 11.847,2 | 14.541,0 |
| B0 | multi-hop | 11 | 8 | 3 | 18.803,2 | 29.201,9 |
| B0 | no-evidence | 11 | 11 | 0 | 14.737,2 | 16.286,2 |
| B0 | temporal | 13 | 13 | 1 | 17.046,7 | 19.359,1 |
| B1 | easy | 15 | 12 | 1 | 10.548,5 | 14.474,1 |
| B1 | multi-hop | 11 | 11 | 0 | 17.413,8 | 18.735,4 |
| B1 | no-evidence | 11 | 11 | 1 | 11.641,8 | 16.617,1 |
| B1 | temporal | 13 | 13 | 2 | 15.649,4 | 17.506,6 |
| B2 | easy | 15 | 15 | 0 | 17.440,1 | 22.776,1 |
| B2 | multi-hop | 11 | 11 | 0 | 22.003,1 | 25.547,3 |
| B2 | no-evidence | 11 | 11 | 0 | 21.006,1 | 29.846,3 |
| B2 | temporal | 13 | 13 | 0 | 23.539,8 | 32.843,1 |
| B3 | easy | 15 | 14 | 1 | 20.087,1 | 26.622,2 |
| B3 | multi-hop | 11 | 6 | 5 | 24.625,6 | 59.229,8 |
| B3 | no-evidence | 11 | 10 | 1 | 18.912,9 | 62.007,5 |
| B3 | temporal | 13 | 13 | 0 | 20.123,5 | 25.602,2 |

## Catatan

- B2 paling stabil di test-50 (schema 50/50), tetapi B3 tetap unggul retrieval
  (Gate 2); schema validity bukan ukuran kualitas jawaban.
- B3 punya ekor latency tinggi di multi-hop/no-evidence (p95 > 59 s), sejalan
  dengan catatan Week 3 tentang biaya retry/repair.
- Test-50 tidak dipakai untuk memilih parameter apa pun. Baseline ini dibekukan
  sebelum config freeze dan hanya menjadi pembanding.
