# Documentation index

Dokumen sumber (tidak diubah): [`spek.md`](../spek.md),
[`RENCANA_LENGKAP.md`](../RENCANA_LENGKAP.md),
[`RENCANA_MINGGUAN.md`](../RENCANA_MINGGUAN.md).

## Mulai dari sini

| Kebutuhan | Dokumen |
| --- | --- |
| Aturan anotasi benchmark | [`../benchmark/guidelines.md`](../benchmark/guidelines.md) |
| Handoff B → C/D | [`handoff/w1-b.md`](handoff/w1-b.md) |
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
- Tool: `tools/annotate.py`, `tools/build_pool.py`, `tools/validate_benchmark.py`
- Aturan lengkap: `benchmark/guidelines.md`

## Data dan index

File besar tidak di-commit. Bangun ulang dengan `.\scripts\tasks.ps1 corpus`
dan `.\scripts\tasks.ps1 index`; hash acuan ada di
`data/processed/manifest.sha256`.
