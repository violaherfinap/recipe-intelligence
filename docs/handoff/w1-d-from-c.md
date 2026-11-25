# Handoff C → D: mulai dari branch C

Branch: `feat/w1-c-qrels-metrics` (sudah di-push, tanpa PR).

C selesai. D melanjutkan dari branch ini.

## Peringatan blind

Branch ini berisi label C. Sebelum pass 2 selesai, **jangan buka**:

- `benchmark/qrels_c.jsonl`
- `benchmark/verdict_qrels_c.jsonl`
- `benchmark/qrels_c_reviewed.jsonl`
- `benchmark/qrels_c_pass1_2026-11-14.jsonl`
- `benchmark/qrels_c_draft.jsonl`
- `benchmark/verdict_c_answers.txt`
- `benchmark/work/w1-c-audit-2026-11-14/`
- `docs/handoff/w1-c.md`
- diff/commit yang menampilkan isi qrels C

Jangan buka `benchmark/gold_candidates.jsonl` dan
`benchmark/pool_v1_meta.jsonl`.

Kalau tidak bisa menjamin blind, mulai dari
`origin/feat/w1-b-benchmark`, bukan branch C.

## Preflight

```powershell
git switch -c feat/w1-d-pass2
```

Pastikan ada:

- `benchmark/queries.jsonl`
- `benchmark/pool_v1.jsonl`
- `data/processed/passages.jsonl`
- `data/corpus_commit.txt`
- `tools/annotate.py`

Kalau `pool_v1.jsonl` tidak ada, minta C. Jangan rebuild sendiri.

Jangan ubah `queries.jsonl`, `passages.jsonl`, `split.json`, atau index.
Jangan stage `data/processed/split.json` atau file untracked lain.

## 1. Relevance pass 2

```powershell
uv run python tools/annotate.py relevance --annotator D `
  --queries benchmark/queries.jsonl `
  --pool benchmark/pool_v1.jsonl `
  --passages data/processed/passages.jsonl `
  --out benchmark/qrels_d.jsonl
```

Cek progres:

```powershell
uv run python tools/annotate.py status --annotator D `
  --out benchmark/qrels_d.jsonl `
  --pool benchmark/pool_v1.jsonl
```

Target: 1.789 judgment, semua query selesai.

## 2. Verdict pass 2

Gunakan `qrels_d.jsonl`, bukan qrels C:

```powershell
uv run python tools/annotate.py verdict --annotator D `
  --queries benchmark/queries.jsonl `
  --qrels benchmark/qrels_d.jsonl `
  --passages data/processed/passages.jsonl `
  --out benchmark/verdict_qrels_d.jsonl
```

Cek progres:

```powershell
uv run python tools/annotate.py status --annotator D `
  --out benchmark/verdict_qrels_d.jsonl
```

Target: 145 klaim.

## 3. Setelah pass 2 selesai

- Jangan commit dulu.
- Kabari C dengan: jumlah `qrels_d`, jumlah `verdict_qrels_d`,
  timestamp selesai, dan konfirmasi bahwa label C tidak dibuka.
- Setelah itu baru boleh buka label C untuk κ, adjudikasi, dan freeze.
