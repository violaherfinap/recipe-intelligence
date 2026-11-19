# Documentation index

Dokumen sumber (tidak diubah): [`spek.md`](../spek.md),
[`RENCANA_LENGKAP.md`](../RENCANA_LENGKAP.md),
[`RENCANA_MINGGUAN.md`](../RENCANA_MINGGUAN.md).

## Mulai dari sini

| Kebutuhan | Dokumen |
| --- | --- |
| Aturan anotasi benchmark | [`../benchmark/guidelines.md`](../benchmark/guidelines.md) |
| Handoff B → C | [`handoff/w1-b.md`](handoff/w1-b.md) |
| Handoff C → D | [`handoff/w1-c.md`](handoff/w1-c.md) |
| Handoff A → B (Week 2) | [`handoff/w2-a.md`](handoff/w2-a.md) |
| Handoff B → C/D (Week 2) | [`handoff/w2-b.md`](handoff/w2-b.md) |
| Laporan Week 1 (block D) | [`../reports/week1.md`](../reports/week1.md) |
| Laporan A2 Week 2 | [`../reports/a2_dev.md`](../reports/a2_dev.md) |
| Laporan B2/B3 + pool Week 2 | [`../reports/b2b3_dev.md`](../reports/b2b3_dev.md) |
| Status 3 baris per blok | [`handoff_log.md`](handoff_log.md) |
| Pembagian kerja dan jam | [`contribution_matrix.md`](contribution_matrix.md) |
| Pertanyaan/keputusan terbuka | [`open_questions.md`](open_questions.md) |
| Handoff A → B | [`handoff/w1-a.md`](handoff/w1-a.md) |
| Bukti smoke retrieval A | [`w1-a-smoke.md`](w1-a-smoke.md) |
| ADR | [`adr/`](adr/) |

## Benchmark

- Query: `benchmark/queries.jsonl` + `benchmark/queries.sha256`
- Gold evidence: `benchmark/gold_candidates.jsonl`
- Verifikasi no-evidence: `benchmark/no_evidence_check.csv`
- Qrels relevance pass 1: `benchmark/qrels_c.jsonl` + `benchmark/qrels_c.sha256`
- Verdict pass 1: `benchmark/verdict_qrels_c.jsonl`
- Final qrels: `benchmark/qrels.jsonl` + `benchmark/manifest.sha256`
- Final verdict: `benchmark/verdict_qrels.jsonl`
- Pool v2 (Week 2): `benchmark/pool_v2.jsonl` + `benchmark/pool_v2.sha256`;
  provenance `benchmark/pool_v2_meta.jsonl` (tidak di-commit)
- Agreement/adjudikasi: `benchmark/kappa.json`, `benchmark/conflicts.jsonl`,
  `benchmark/adjudication.jsonl`, `benchmark/annotation_log.csv`
- Tool: `tools/annotate.py`, `tools/build_pool.py`, `tools/validate_benchmark.py`,
  `tools/review_preannotation.py`, `tools/finalize_qrels.py`,
  `tools/review_verdicts.py`, `tools/compute_agreement.py`, `tools/adjudicate.py`,
  `tools/finalize_benchmark.py`
- Aturan lengkap: `benchmark/guidelines.md`

## Data dan index

File besar tidak di-commit. Bangun ulang dengan `.\scripts\tasks.ps1 corpus`
dan `.\scripts\tasks.ps1 index`; hash acuan ada di
`data/processed/manifest.sha256`.
