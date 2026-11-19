# Documentation index

Dokumen sumber (tidak diubah): [`spek.md`](../spek.md),
[`RENCANA_LENGKAP.md`](../RENCANA_LENGKAP.md),
[`RENCANA_MINGGUAN.md`](../RENCANA_MINGGUAN.md).

## Week 2 (aktif)

| Kebutuhan | Dokumen |
| --- | --- |
| Handoff A → B | [`handoff/w2-a.md`](handoff/w2-a.md) |
| Handoff B → C/D | [`handoff/w2-b.md`](handoff/w2-b.md) |
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
- Gold evidence: `benchmark/gold_candidates.jsonl`
- Verifikasi no-evidence: `benchmark/no_evidence_check.csv`
- Qrels relevance pass 1: `benchmark/qrels_c.jsonl` + `benchmark/qrels_c.sha256`
- Verdict pass 1: `benchmark/verdict_qrels_c.jsonl`
- Final qrels: `benchmark/qrels.jsonl` + `benchmark/manifest.sha256`
- Final verdict: `benchmark/verdict_qrels.jsonl`
- Pool v2: `benchmark/pool_v2.jsonl` + `benchmark/pool_v2.sha256`;
  provenance `benchmark/pool_v2_meta.jsonl` (tidak di-commit)
- Agreement/adjudikasi: `benchmark/kappa.json`, `benchmark/conflicts.jsonl`,
  `benchmark/adjudication.jsonl`, `benchmark/annotation_log.csv`

## Tool

| Kebutuhan | Tool |
| --- | --- |
| Anotasi relevance/verdict | `tools/annotate.py` |
| Pool v1 / pool v2 | `tools/build_pool.py`, `tools/build_pool_v2.py` |
| Validasi benchmark | `tools/validate_benchmark.py` |
| Evaluasi retrieval | `tools/eval_retrieval.py` |
| Smoke/batch config | `tools/run_config.py` |
| Tabel ringkas run | `tools/summarize_runs.py` |

## Data dan index

File besar tidak di-commit. Bangun ulang dengan `.\scripts\tasks.ps1 corpus`
dan `.\scripts\tasks.ps1 index`; hash acuan ada di
`data/processed/manifest.sha256`. Index tambahan: `indexes/fixed/` dan
`indexes/hierarchical/` dibangun dengan target `passages-fixed` /
`passages-hierarchical` lalu `index-fixed` / `index-hierarchical`.
