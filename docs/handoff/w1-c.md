# Week 1 — Block C handoff

**Owner:** C  
**Tanggal:** 2026-11-14  
**Branch:** `feat/w1-c-qrels-metrics`  
**Commit kode:** `79dd9fb`  
**Corpus commit:** `ae3bd2c009a8899dfe63b9166fa98ae3fa8041a8`

## Status

Relevance qrels pass 1, metrics library, dan verdict C pass 1 selesai.

- Pool v1: **1.789 kandidat** test-only.
- Qrels final: **1.789 baris, 115 query**.
- Distribusi label final: **1.608×0, 12×1, 169×2**.
- Semua qrels `annotator:"C"`, `doc_version` cocok dengan commit korpus.
- q091–q115 (no-evidence): semua label `0`.
- q001–q090 (answerable): setiap query punya minimal satu label `2`.
- q048: hanya satu label `2`; resep kedua tidak ada di pool (lihat Known issues).
- Verdict C: **145/145 klaim**, 144 SUPPORTED, 0 REFUTED, 1 NOT_ENOUGH_EVIDENCE (q048 c2).
- Actual hours: **11,47 jam** (2026-11-14T05:43:05.731Z sampai 2026-11-14T17:11:27Z).
- Test suite: **75 unit test lulus** (termasuk metrics dan batch verdict), `ruff check src tests tools` bersih.

## Artefak

| File | Isi |
| --- | --- |
| `benchmark/qrels_c.jsonl` | Qrels relevance pass 1 final, 1.789 baris q001–q115 |
| `benchmark/qrels_c.sha256` | SHA-256 qrels final |
| `benchmark/verdict_qrels_c.jsonl` | Verdict pass 1, 145 klaim dari 90 query answerable |
| `benchmark/verdict_c_answers.txt` | Answer sheet batch verdict q002–q090 (arsip lokal, tidak di-commit) |
| `benchmark/qrels_c_reviewed.jsonl` | Hasil review q009–q115, 1.666 baris (arsip lokal, tidak di-commit) |
| `benchmark/qrels_c_draft.jsonl` | Draft preannotator q009–q115, 1.666 baris (arsip lokal, LLM-assisted) |
| `benchmark/qrels_c_pass1_2026-11-14.jsonl` | Backup qrels manual q001–q008, 123 baris (arsip lokal) |
| `benchmark/work/w1-c-audit-2026-11-14/` | Arsip audit lengkap + `SHA256SUMS.txt` (gitignored) |
| `tools/review_preannotation.py` | CLI review draft: tampilkan semua kandidat per query, lalu isi keputusan |
| `tools/finalize_qrels.py` | Merge + validasi qrels manual dan reviewed |
| `tools/review_verdicts.py` | CLI batch verdict: tampilkan semua klaim + evidence per query, lalu isi verdict |
| `src/recipe_qa/benchmark/review.py` | Helper review: progress, catatan, parser keputusan |
| `src/recipe_qa/benchmark/finalize.py` | Validasi gabungan qrels |
| `src/recipe_qa/benchmark/verdict_review.py` | Parser keputusan batch verdict |
| `src/recipe_qa/eval/metrics/retrieval.py` | Recall@k, nDCG@k, MRR@k, evaluate_retrieval |
| `src/recipe_qa/eval/metrics/claims.py` | Macro-F1, citation precision/recall, unsupported claim rate |
| `tests/unit/test_review.py`, `test_finalize.py`, `test_verdict_review.py`, `test_metrics_retrieval.py`, `test_metrics_claims.py` | Test review, finalisasi, verdict parser, dan metrics |

Hash audit (final, committed):

```text
58c435dc0121f2654a2052b40542e1c4106166295781d2baf5ce9da4f11257cc  qrels_c.jsonl
0b5a97d5c71540d8907454d43a7740ac03d413aa6f11dd1592903c93189e5805  verdict_qrels_c.jsonl
```

Hash artefak lokal (review, draft, backup, prompt/answer) ada di
`benchmark/work/w1-c-audit-2026-11-14/SHA256SUMS.txt` (gitignored).

## Proses anotasi

1. q001–q008 dinilai manual: 123 baris, distribusi 112×0, 1×1, 10×2.
2. q009–q115 dibuat draft preannotator: 1.666 baris, distribusi 1.493×0, 13×1, 160×2.
3. Draft direview lewat `tools/review_preannotation.py`:
   - semua kandidat per query ditampilkan sekaligus;
   - keputusan diisi satu baris (`a`, `0/1/2`, `s`, `all`);
   - output append-only ke `qrels_c_reviewed.jsonl`.
4. Hasil review: 1.666/1.666 baris, 3 override, 0 skip.
5. qrels manual + reviewed digabung dan divalidasi dengan `tools/finalize_qrels.py`.

Override review:

| Query | Passage | Draft → final | Alasan |
| --- | --- | ---: | --- |
| q020 | `arrow-root-jelly#directions#0` | 1 → 0 | Tahun 1851 dan durasi bukan setelah mengental |
| q020 | `arrowroot-milk-porridge#directions#0` | 1 → 0 | Tahun 1887 dan tidak menjawab durasi setelah mengental |
| q024 | `blackberry-cordial-2#directions#0` | 2 → 0 | Tahun 1887, bukan resep 1871 |

## Verdict batch C

Verdict C selesai **145/145** klaim. Tool mendukung dua alur: interaktif per
query dan batch `dump` + `fill`.

Alur batch:

```powershell
uv run python tools/review_verdicts.py dump --annotator C
# buka benchmark/verdict_c_prompt.txt, salin seluruh isi ke AI
# tulis jawaban ke benchmark/verdict_c_answers.txt
uv run python tools/review_verdicts.py fill --annotator C --dry-run
uv run python tools/review_verdicts.py fill --annotator C
uv run python tools/review_verdicts.py status --annotator C
```

Hasil: **144 SUPPORTED, 0 REFUTED, 1 NOT_ENOUGH_EVIDENCE** (q048 c2).

Format answer file, satu baris per query:

```text
# komentar diabaikan
q001 c1=s
q002 c1=s c2=n
q003 all=n
```

Arti: `s=SUPPORTED`, `r=REFUTED`, `n=NOT_ENOUGH_EVIDENCE`. `fill` memvalidasi
seluruh claim pending, nilai verdict, duplikat, dan query yang tidak dikenal
sebelum menulis. Jika ada satu error, tidak ada baris yang ditulis. Output
append-only ke `benchmark/verdict_qrels_c.jsonl`.

Alur interaktif tetap tersedia:

```powershell
uv run python tools/review_verdicts.py review --annotator C
```

Untuk D, ganti `--annotator D`; tool memakai `benchmark/qrels_d.jsonl`,
`benchmark/verdict_d_prompt.txt`, `benchmark/verdict_d_answers.txt`, dan
`benchmark/verdict_qrels_d.jsonl` secara default.

## Validasi

```powershell
uv run python tools/finalize_qrels.py --dry-run
uv run python tools/validate_benchmark.py --strict
uv run python tools/review_verdicts.py status --annotator C
uv run pytest -q
uv run ruff check src tests tools
```

Hasil:

- Finalisasi: manual 123 + reviewed 1.666 = 1.789; 115 query; tanpa duplikat/overlap.
- `validate_benchmark.py --strict`: benchmark valid.
- Verdict C: 145/145 klaim; 90 query; 144 SUPPORTED, 0 REFUTED, 1 NOT_ENOUGH_EVIDENCE.
- `pytest -q`: 75 test lulus.
- `ruff check src tests tools`: bersih.

## Known issues

- **q048 pool gap:** query meminta dua resep 1871 dengan chocolate + cream. Pool hanya memuat `chocolate-ice-cream#ingredients#0`; `chocolate-charlotte-russe` tidak ada. Qrels q048 hanya punya satu label `2`. Jangan menambah label `2` pada kandidat yang tidak memenuhi; catat sebagai pool recall gap. Lihat `docs/open_questions.md` Q9.
- **q103:** no-evidence; “quick oven” tidak dianggap suhu. Semua kandidat `0`.
- **q048 c2:** verdict `NOT_ENOUGH_EVIDENCE` karena `Marbled Cake` tidak ada di evidence/pool; bukan `REFUTED`.

## Berikutnya untuk D

1. Kerjakan relevance pass 2 blind ke `benchmark/qrels_d.jsonl`.
2. Jangan membuka `benchmark/qrels_c.jsonl`, `benchmark/qrels_c_reviewed.jsonl`, `benchmark/work/w1-c-audit-2026-11-14/`, atau catatan C sebelum pass 2 selesai.
3. Verdict C sudah selesai (145/145); D mengerjakan verdict pass 2 blind dengan `tools/review_verdicts.py review --annotator D`.
4. Hitung Cohen's κ relevance dan verdict, catat disagreement, lalu adjudikasi.

## Reproduksi finalisasi

```powershell
uv run python tools/finalize_qrels.py --dry-run
uv run python tools/finalize_qrels.py
uv run python tools/validate_benchmark.py --strict
```

Perintah finalisasi membutuhkan `benchmark/qrels_c_reviewed.jsonl` dan
`benchmark/qrels_c_pass1_2026-11-14.jsonl`, yang tidak di-commit. Salinannya ada
di arsip lokal `benchmark/work/w1-c-audit-2026-11-14/`.
