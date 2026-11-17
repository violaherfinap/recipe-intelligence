# Week 1 — Block D report

**Owner:** D (dengan bantuan assistant)
**Tanggal:** 2026-11-18
**Branch:** `feat/w1-d-pass2`
**Status:** selesai; commit `f0a436d`

## Ringkasan

Pass 2 relevance dan verdict selesai, konflik C/D sudah diadjudikasi, dan
benchmark Week 1 sudah dibekukan.

- Relevance pass 2: **1.789 judgment / 115 query**.
- Verdict pass 2: **145 klaim / 90 query answerable**.
- Relevance κ: **0.9607** (observed 0.9927, expected 0.8153).
- Verdict κ: **0.4983** (observed 0.9931, expected 0.9863).
- Konflik relevance: **13**; konflik verdict: **1**; total **14**, semuanya
  selesai diadjudikasi.
- Final qrels: **1.789 baris** (`0=1608, 1=13, 2=168`).
- Final verdict: **145 baris** (`SUPPORTED=144, REFUTED=1,
  NOT_ENOUGH_EVIDENCE=0`).
- Annotation log: **14 baris** di `benchmark/annotation_log.csv`.
- No-evidence: 25/25 query terverifikasi, plus spot-check 5/5.
- `validate_benchmark.py --strict`: **valid**.
- Test: **100 lulus**; `ruff check src tests tools`: **bersih**.

## Gate 1

| Kriteria | Hasil | Bukti |
| --- | --- | --- |
| Korpus dan index | 5.605 dokumen diparse; 5.600 indexed; 11.266 passage; 846 dokumen test | `data/processed/manifest.json`, `indexes/manifest.json` |
| Query | 115 query beku (35 easy / 25 multi-hop / 30 temporal / 25 no-evidence) | `benchmark/queries.jsonl`, `benchmark/queries.sha256` |
| Qrels | 1.789 judgment; 100% query; 168 relevance-2 | `benchmark/qrels.jsonl` |
| Verdict | 145 klaim; 144 SUPPORTED / 1 REFUTED / 0 NEI | `benchmark/verdict_qrels.jsonl` |
| Agreement | relevance κ 0.9607; verdict κ 0.4983 | `benchmark/kappa.json` |
| Konflik | 14/14 selesai; 0 open | `benchmark/conflicts.jsonl`, `benchmark/adjudication.jsonl`, `benchmark/annotation_log.csv` |
| No-evidence | 25/25 absent; spot-check 5/5 | `benchmark/no_evidence_check.csv` |
| Freeze | 4 hash query/qrels/verdict/test docs | `benchmark/manifest.sha256` |
| Validasi | strict valid; 100 test; ruff bersih | `tools/validate_benchmark.py`, `pytest`, `ruff` |

**Status Gate 1:** PASS untuk data dan freeze, dengan catatan: pass 2
AI-assisted, `q048` partial multi-hop, dan verdict κ rendah karena satu
perbedaan label langka. Detail ada di bagian **Catatan anotasi D** dan
**Known issues**.

## Agreement C vs D

| Jenis | n | Observed | Expected | κ | Konflik |
| --- | ---: | ---: | ---: | ---: | ---: |
| Relevance | 1.789 | 0.9927 | 0.8153 | 0.9607 | 13 |
| Verdict | 145 | 0.9931 | 0.9863 | 0.4983 | 1 |

Verdict κ turun dari `1.0000` karena C dan D sebelumnya sama-sama memberi
`NOT_ENOUGH_EVIDENCE` pada `q048 c2`. Setelah koreksi guideline, D memberi
`REFUTED`. Raw agreement tetap tinggi (`0.9931`), tetapi κ sangat sensitif
terhadap satu perbedaan pada label langka.

## Adjudikasi

- **10 × C=2 / D=1**: passage `directions` multi-hop menyebut kedua bahan
  target secara eksplisit. Final **2**.
- **1 × C=2 / D=1**: `q076` item
  `ye-old-american:lobster-croquettes-2#ingredients#0` hanya mendaftar
  `bread crumbs` tanpa menyatakan perannya sebagai binder. Final **1**;
  passage `directions` 1887 dan passage 1896 tetap **2**.
- **2 × C=0 / D=1**: `q083` menanyakan cara mengaduk cream; passage
  `ingredients` hanya memuat bahan dan tidak menjawab metode. Final **0**.
- **1 × verdict**: `q048 c2` C=`NOT_ENOUGH_EVIDENCE`, D=`REFUTED`. Final
  **REFUTED**.

Koreksi `q048 c2` mengikuti `benchmark/guidelines.md` bagian 10: klaim
komparatif “both chocolate and cream” harus `REFUTED` jika salah satu resep
tidak memakai cream. Passage Marbled Cake 1871 memakai `cream-tartar` dan
`sweet milk`, bukan cream.

## Annotation log

`benchmark/annotation_log.csv` berisi 14 baris konflik:

- 13 konflik relevance;
- 1 konflik verdict;
- kolom `kind,query_id,item_id,label_c,label_d,reason,decision`;
- tidak ada konflik yang masih terbuka.

## Spot-check no-evidence

| Query | Topik | Final qrels | `no_evidence_check` | Spot-check |
| --- | --- | --- | --- | --- |
| `q091` | gas oven 1796 | semua `0` (15) | absent | 1796 scope tidak menyebut gas oven/range |
| `q093` | calorie count 1796 | semua `0` (15) | absent | tidak ada istilah kalori/nutrisi |
| `q097` | protein 1824 rice bread | semua `0` (15) | absent | tidak ada istilah protein |
| `q103` | oven temperature 1871 | semua `0` (15) | absent | kandidat “even temperature” adalah 1887, di luar scope 1871 |
| `q115` | sous vide 1896 | semua `0` (15) | absent | tidak ada istilah sous vide |

Hasil: **5/5 sesuai**; tidak ada label final yang perlu diubah.

## Catatan anotasi D

- Relevance D dikerjakan dengan bantuan AI: 44 passage multi-hop dinaikkan ke
  `2` setelah membaca teks passage. Tiga perubahan terakhir: q048, q087, q088.
- Verdict D juga disusun dengan bantuan AI berdasarkan evidence; verdict C
  tidak dipakai. Backup sheet sebelum verdict AI:
  `benchmark/verdict_answer_sheet_d.pre_ai_verdict.csv`.
- Koreksi setelah audit: `q048 c2` NEI → REFUTED; `q076` ingredients → `1`;
  backup sebelum koreksi q048:
  `benchmark/verdict_answer_sheet_d.pre_q048_refuted.csv`.
- Ini adalah deviasi metodologis yang harus dicatat di laporan/tugas: pass 2 D
  bukan anotasi manusia independen sepenuhnya.
- Blind pass 2 tidak murni: agregat relevance C sudah terlihat saat diagnosis
  multi-hop. Label per-item C tidak dipakai untuk 44 upgrade tersebut.
- Verdict C baru dibuka setelah verdict D selesai dan di-import; handoff C
  dibaca setelah itu.
- Jika rubrik membutuhkan human inter-annotator κ, pass 2 perlu diulang oleh
  manusia; artefak saat ini adalah AI-assisted dengan audit.

## Known issues

- **q048 partial multi-hop.** Query meminta dua resep 1871 dengan chocolate +
  cream. Hanya `chocolate-ice-cream#ingredients#0` yang relevance `2`.
  `marbled-cake#ingredients#0` ada di pool tetapi `0` karena memakai
  cream-tartar/sweet milk, bukan cream. `chocolate-charlotte-russe` tidak ada
  di pool. Jangan menambah label `2` tanpa bukti; q048 diterima sebagai
  partial multi-hop.
- **q048 c2 sekarang REFUTED**, bukan `NOT_ENOUGH_EVIDENCE`. C handoff
  historis menyebut Marbled Cake “absent”; inspeksi pool menunjukkan kandidat
  itu ada dengan relevance `0`. Koreksi dicatat di Q9.
- **q076 correction.** Ingredients-only passage tidak cukup eksplisit untuk
  binder; final `1` sesuai aturan ragu 1-vs-2.
- **q050 judgment call.** `cream-sauce-2` dihitung memakai almond melalui
  “extract of bitter almonds”.
- **q087/q088.** Passage 1851 `snowball-custard#ingredients#0` dinaikkan ke `2`
  karena memuat boiled custard, putih telur, dan oil of lemon; temporal coverage
  menjadi 30/30.
- **Actual hours D tidak dilacak**; `docs/contribution_matrix.md` memakai
  “— (tidak dilacak)”.
- `data/processed/split.json` tidak diubah dan tidak di-stage.

## Manifest final

```text
d5128e48413125b1383e4946580a08f133964fbb8e0d1a7e988f0a143a27b2ac  benchmark/queries.jsonl
bdddf48e165b3f3ce9a8d34381e4ef60058c38d790a86d69ae01fd87c1907401  benchmark/qrels.jsonl
6e6b549911f2b185d35d432aeb05666c46774e2b3fab7ea45fd82dd39d32e739  benchmark/verdict_qrels.jsonl
d7e0a7c96a83de702222e8d5f17c1a5cf18f7c989726aca89c7fec5146b97f96  benchmark/test_docs.txt
```

## Artefak final

| Artefak | Isi |
| --- | --- |
| `benchmark/qrels_d.jsonl` | 1.789 qrels D |
| `benchmark/verdict_qrels_d.jsonl` | 145 verdict D |
| `benchmark/kappa.json` | laporan agreement lengkap |
| `benchmark/conflicts.jsonl` | 14 konflik |
| `benchmark/adjudication.jsonl` | 14 keputusan adjudikasi |
| `benchmark/annotation_log.csv` | 14 baris log konflik |
| `benchmark/qrels.jsonl` | 1.789 qrels final |
| `benchmark/verdict_qrels.jsonl` | 145 verdict final |
| `benchmark/test_docs.txt` | 846 dokumen test |
| `benchmark/manifest.sha256` | 4 entry hash |

## Reproduksi

Sheet jawaban D bersifat lokal dan tidak di-commit. Final qrels/verdict dapat
direproduksi dari artefak adjudikasi yang sudah di-commit.

```powershell
uv run python tools/import_answer_sheet.py verdict `
  --input benchmark/verdict_answer_sheet_d.csv --force

uv run python tools/compute_agreement.py
uv run python tools/adjudicate.py list
uv run python tools/adjudicate.py status
uv run python tools/finalize_benchmark.py --dry-run
uv run python tools/finalize_benchmark.py
uv run python tools/validate_benchmark.py --strict
uv run pytest -q
uv run ruff check src tests tools
```
