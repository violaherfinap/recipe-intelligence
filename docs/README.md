# Documentation index

Dokumen sumber (tidak diubah): [`spek.md`](../spek.md),
[`RENCANA_LENGKAP.md`](../RENCANA_LENGKAP.md),
[`RENCANA_MINGGUAN.md`](../RENCANA_MINGGUAN.md).

## Week 3 (aktif)

| Kebutuhan | Dokumen |
| --- | --- |
| Handoff A/B/C/D | [`handoff/w3.md`](handoff/w3.md) |
| Peringatan dan urutan kerja | [`handoff/w3-notes.md`](handoff/w3-notes.md) |
| Handoff B (split 65/50) | [`handoff/w3-b.md`](handoff/w3-b.md) |
| Laporan P0 grounding gate | [`../reports/a3_verify_dev.md`](../reports/a3_verify_dev.md) |

Base W3 aktif: tag **`w3-base-a3`** (split + verifier + fix kalibrasi). Mulai
branch baru dari tag ini, bukan dari branch W3 lama.

Split query Week 3 (tag data `w3-query-split`): `benchmark/query_split.json`,
`benchmark/queries_train.jsonl` (65 train, kalibrasi),
`benchmark/queries_test.jsonl` (50 test, angka final). Angka 115 query adalah
development evaluation.

## Week 2 (aktif)

| Kebutuhan | Dokumen |
| --- | --- |
| Handoff A → B | [`handoff/w2-a.md`](handoff/w2-a.md) |
| Handoff B → C/D | [`handoff/w2-b.md`](handoff/w2-b.md) |
| Handoff C → D | [`handoff/w2-c.md`](handoff/w2-c.md) |
| Closeout D | [`handoff/w2-d.md`](handoff/w2-d.md) |
| Indeks laporan | [`../reports/README.md`](../reports/README.md) |
| Laporan A2 | [`../reports/a2_dev.md`](../reports/a2_dev.md) |
| Laporan B2/B3 + pool | [`../reports/b2b3_dev.md`](../reports/b2b3_dev.md) |
| Aturan anotasi | [`../benchmark/guidelines.md`](../benchmark/guidelines.md) |

## Week 1 (arsip)

| Kebutuhan | Dokumen |
| --- | --- |
| Handoff A → B | [`handoff/w1-a.md`](handoff/w1-a.md) |
| Handoff B → C | [`handoff/w1-b.md`](handoff/w1-b.md) |
| Handoff C → D | [`handoff/w1-c.md`](handoff/w1-c.md) |
| Catatan D dari C | [`handoff/w1-d-from-c.md`](handoff/w1-d-from-c.md) |
| Laporan Week 1 | [`../reports/week1.md`](../reports/week1.md) |
| Bukti smoke retrieval A | [`w1-a-smoke.md`](w1-a-smoke.md) |

## Status dan keputusan

| Kebutuhan | Dokumen |
| --- | --- |
| Status 3 baris per blok | [`handoff_log.md`](handoff_log.md) |
| Pembagian kerja | [`contribution_matrix.md`](contribution_matrix.md) |
| Pertanyaan/keputusan terbuka | [`open_questions.md`](open_questions.md) |
| ADR | [`adr/`](adr/) |

## Benchmark

- Query: `benchmark/queries.jsonl` + `benchmark/queries.sha256`
- Split query Week 3: `benchmark/query_split.json`, `benchmark/queries_train.jsonl`
  (65), `benchmark/queries_test.jsonl` (50)
- Gold evidence: `benchmark/gold_candidates.jsonl`
- Verifikasi no-evidence: `benchmark/no_evidence_check.csv`
- Spot-check no-evidence v2: `benchmark/no_evidence_spotcheck_v2.csv`
- Qrels relevance pass 1 v2: `benchmark/qrels_v2_c.jsonl` + `benchmark/qrels_v2_c.sha256`
- Qrels relevance pass 2 v2: `benchmark/qrels_v2_d.jsonl` (lokal, gitignored)
- Qrels relevance A v2: `benchmark/qrels_v2_a.jsonl` (lokal, gitignored)
- Verdict pass 1/2: `benchmark/verdict_qrels_c.jsonl`, `benchmark/verdict_qrels_d.jsonl`
- Final qrels: `benchmark/qrels.jsonl` + `benchmark/manifest.sha256`
- Final verdict: `benchmark/verdict_qrels.jsonl`
- Pool v2: `benchmark/pool_v2.jsonl` + `benchmark/pool_v2.sha256`;
  provenance `benchmark/pool_v2_meta.jsonl` (tidak di-commit)
- Agreement/adjudikasi v2: `benchmark/kappa.json`, `benchmark/kappa_v2.json`,
  `benchmark/adjudication_v2.jsonl`
- Log konflik final: `benchmark/conflicts.jsonl`, `benchmark/annotation_log.csv`;
  arsip v1.1 di `benchmark/archive/`

## Tool

| Kebutuhan | Tool |
| --- | --- |
| Anotasi relevance/verdict | `tools/annotate.py` |
| Pool v1 / pool v2 | `tools/build_pool.py`, `tools/build_pool_v2.py` |
| Validasi benchmark | `tools/validate_benchmark.py` |
| Split query train/test | `tools/split_queries.py` |
| Evaluasi retrieval | `tools/eval_retrieval.py` |
| Smoke/batch config | `tools/run_config.py` |
| Tabel ringkas run | `tools/summarize_runs.py` |

## Data dan index

File besar tidak di-commit. Bangun ulang dengan `.\scripts\tasks.ps1 corpus`
dan `.\scripts\tasks.ps1 index`; hash acuan ada di
`data/processed/manifest.sha256`. Index tambahan: `indexes/fixed/` dan
`indexes/hierarchical/` dibangun dengan target `passages-fixed` /
`passages-hierarchical` lalu `index-fixed` / `index-hierarchical`.
