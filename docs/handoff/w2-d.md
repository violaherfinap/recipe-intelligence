# Handoff W2-D - finalisasi qrels v2, Gate 2, dan error taxonomy

- **Owner:** D
- **Branch:** `feat/w2-d-finalize-qrels-v2`
- **Base:** `a7491cb` (`feat/w2-c-qrels-v2-a1`)
- **Tanggal:** 2026-11-24
- **Status:** closeout Week 2 selesai; qrels v2 frozen; Gate 2 lulus
- **Handoff ke:** A (test B0-B3), lalu B/C untuk verifier dan evaluasi

## Ringkasan

D menyelesaikan pass 2 anotasi 448 kandidat baru pool v2, menghitung agreement
tiga anotator, mengadjudikasi konflik, memfreeze qrels v2, dan menutup Gate 2.
D juga menjalankan ulang A1 dengan qrels v2 serta menyusun error taxonomy final.
Tidak ada label C yang dibuka sebelum pass 2 selesai.

Hasil utama:

- Qrels v2 frozen **2.237 baris** / 115 query; label `0=1955`, `1=38`, `2=244`.
- C/D relevance **kappa 0.9629** (6 konflik); Fleiss A/C/D **0.9223**; 1 tie
  `q013` diputuskan final `1`.
- Verdict final **145 klaim**; C/D kappa **0.4983** (1 konflik); `q048 c2`
  diputuskan `REFUTED`.
- Gate 2 lulus: B3 Recall@10 **0.5369** vs B2 **0.1515**; doc recall
  **0.7833** vs **0.3889**.
- Error taxonomy final: **162 kegagalan / 83 query**; E6-E8 sengaja
  **Not Evaluated**.

## Angka kunci

| Item | Nilai |
| --- | ---: |
| Pool v2 | 2.237 kandidat |
| Kandidat baru | 448 / 113 query |
| D pass 2 | 448/448 |
| A labels | 448/448 |
| Relevance C/D | n=448, kappa=0.9629, conflicts=6 |
| Relevance Fleiss A/C/D | n=448, kappa=0.9223 |
| Verdict C/D | n=145, kappa=0.4983, conflicts=1 |
| Majority relevance | 18 item |
| Tie relevance | 1 (`q013`, final `1`) |
| Missing A/C/D | 0 / 0 / 0 |
| Qrels final | 2.237 baris |
| Verdict final | 145 klaim |
| B2 Recall@10 / doc recall | 0.1515 / 0.3889 |
| B3 Recall@10 / doc recall | **0.5369** / **0.7833** |
| Error taxonomy | 162 baris / 83 query unik |
| Unit test | 139 lulus |

Hash final:

| Artefak | SHA-256 |
| --- | --- |
| `benchmark/qrels.jsonl` | `8ed07e8ebcbefdea332a6a1555b320d0d8c6553f6bffd978cd22894338171926` |
| `benchmark/verdict_qrels.jsonl` | `b86d1d393c4737d7d17c2591e17dd82547d90ad5284085b2b8c674d845b4fdcf` |
| `benchmark/queries.jsonl` | `d5128e48413125b1383e4946580a08f133964fbb8e0d1a7e988f0a143a27b2ac` |
| `benchmark/test_docs.txt` | `d7e0a7c96a83de702222e8d5f17c1a5cf18f7c989726aca89c7fec5146b97f96` |

## Artefak

| Artefak | Path | Status |
| --- | --- | --- |
| Final qrels | `benchmark/qrels.jsonl` | commit |
| Final verdict | `benchmark/verdict_qrels.jsonl` | commit |
| Manifest final | `benchmark/manifest.sha256` | commit |
| Agreement v2 | `benchmark/kappa_v2.json` | commit |
| Keputusan adjudikasi v2 | `benchmark/adjudication_v2.jsonl` | commit |
| Log konflik final | `benchmark/conflicts.jsonl` | commit |
| Annotation log final | `benchmark/annotation_log.csv` | commit |
| Spot-check no-evidence | `benchmark/no_evidence_spotcheck_v2.csv` | commit |
| Arsip v1.1 | `benchmark/archive/` | commit |
| Error taxonomy | `docs/error_taxonomy.md`, `error_analysis.csv` | commit |
| Tool taxonomy | `tools/analyze_retrieval_errors.py` | commit |
| Laporan A1 v2 | `reports/a1_dev.md` | commit |
| Laporan B2/B3 + Gate 2 | `reports/b2b3_dev.md` | commit |
| Qrels C pass 1 | `benchmark/qrels_v2_c.jsonl` | commit dari C |
| Qrels A/D | `benchmark/qrels_v2_a.jsonl`, `benchmark/qrels_v2_d.jsonl` | lokal, gitignored |
| Pool v2 | `benchmark/pool_v2.jsonl`, `pool_v2.sha256` | commit |
| Passage hierarchical | `data/processed/passages_hierarchical.jsonl` | lokal, gitignored |
| Index hierarchical | `indexes/hierarchical/` | lokal, gitignored |
| Run A1 v2 | `artifacts/runs/a1_*_full.json`, `a1_context_stats_v2.json` | lokal, gitignored |
| Run B2/B3 v2 | `artifacts/runs/retrieval_b2_v2.json`, `retrieval_b3_v2.json` | lokal, gitignored |

Jangan commit `benchmark/qrels_v2_d.jsonl.bak`; itu backup lokal.

## Keputusan dan interpretasi

- **Q12 resolved dengan 3 anotator A/C/D.** Label relevance final memakai
  majority 2 dari 3; hanya tie `q013` yang diputuskan D.
- **`q013` final `1`.** Passage
  `ye-old-american:a-boiled-bread-pudding#fixed#1` memberi konteks proses
  memasak, tetapi tidak menyebut durasi `steep`; label partial dipilih.
- **`q048 c2` final `REFUTED`.** Marbled Cake 1871 memakai cream-tartar dan
  sweet milk, bukan cream; ini sesuai guidelines §10. q048 tetap known
  partial multi-hop gap, bukan alasan menambah label tanpa bukti.
- **Finalisasi wajib memakai `benchmark/pool_v2.jsonl`.** `pool_v1.jsonl` hanya
  1.789 key; keputusan relevance lama di `benchmark/adjudication.jsonl` tidak
  dipakai lagi setelah majority A/C/D.
- **A1 hierarchical sudah tersedia.** Rebuild menghasilkan 37.754 passage
  (5.601 summary + 32.153 step). Passage hierarchical tidak dinilai qrels v2,
  jadi passage/nDCG/MRR hierarchical **tidak boleh** dibandingkan; gunakan
  doc recall.
- **Section passage R@10 v2 = 0.1633.** Angka v1.1 (`0.3019`) memakai
  population qrels lebih kecil; perbedaannya bukan penurunan retrieval.
- **E6-E8 Not Evaluated.** E6 tool misuse, E7 format error, dan E8 abstain
  salah tidak dipaksakan menjadi nol. Satu format error (`q060`) dicatat NE.
- **E3/E5 hanya dari audit generation 24 query.** Jangan klaim cakupan seluruh
  115 query untuk error generation.
- **Provenance anotasi.** C pass 1 memakai LLM preannotation + review manusia
  100%; D pass 2 tetap AI-assisted dan bukan human inter-annotator murni.
  Tulis batasan ini di laporan, jangan mengklaim human-only.

## Verifikasi

```powershell
uv run python tools/finalize_benchmark.py `
  --qrels-a benchmark/qrels_v2_a.jsonl `
  --qrels-c benchmark/qrels_v2_c.jsonl `
  --qrels-d benchmark/qrels_v2_d.jsonl `
  --a-keys benchmark/qrels_v2_a.jsonl `
  --verdict-c benchmark/verdict_qrels_c.jsonl `
  --verdict-d benchmark/verdict_qrels_d.jsonl `
  --decisions benchmark/adjudication_v2.jsonl `
  --pool benchmark/pool_v2.jsonl `
  --annotator consensus `
  --dry-run

uv run pytest -q
uv run ruff check src tests tools
uv run python tools/validate_benchmark.py --strict
```

Hasil finalization dry-run:

```text
relevance: n=448 kappa=0.9629 conflicts=6 only_c=0 only_d=0
verdict: n=145 kappa=0.4983 conflicts=1 only_c=0 only_d=0
final: qrels=2237 verdicts=145
resolved: 2/2 ties=1 majority=18
missing: A=0 C=0 D=0
relevance labels: 0=1955, 1=38, 2=244
verdict labels: REFUTED=1, SUPPORTED=144
dry-run: no file written
```

Validasi lain:

- `pytest`: **139 test lulus**.
- `ruff`: bersih.
- `validate_benchmark.py --strict`: benchmark v2 valid.
- `qrels.jsonl`: 2.237 baris, 115 query, tanpa duplikat key.
- `verdict_qrels.jsonl`: 145 klaim, `SUPPORTED=144`, `REFUTED=1`.

## Instruksi untuk A

1. Pakai `benchmark/qrels.jsonl` v2 dan `benchmark/verdict_qrels.jsonl` final;
   jangan memakai qrels v1.1 atau `qrels_v2_c.jsonl`.
2. Jalankan B0-B3 di 115 query test untuk angka final Week 2/Week 3.
3. Jangan tuning threshold/config memakai 115 query test; untuk kalibrasi B4
   tetap butuh dev query set terpisah (Q10).
4. Gunakan run B2/B3 v2 sebagai pembanding Gate 2:
   `artifacts/runs/retrieval_b2_v2.json` dan `retrieval_b3_v2.json`.
5. Jangan mengubah query/qrels tanpa versi baru dan regenerate manifest.

## Catatan terbuka

| ID | Isu | Dampak |
| --- | --- | --- |
| Q1 | Approval dosen Use Case C | Perlu dikonfirmasi sebelum laporan final |
| Q3 | Satu index dengan metadata split atau index terpisah? | Belum memblokir evaluasi; jelaskan di laporan |
| Q5 | Ingredient search/nutrition masuk scope? | Korpus tidak punya data nutrisi |
| Q8 | Gate 1 memakai 5.605 atau 5.600 dokumen? | 5.605 parsed; 5.600 canonical; tidak ada test doc hilang |
| Q10 | Tidak ada dev query set terpisah | Week 2 memakai test sebagai evaluation tanpa tuning; B4 butuh dev murni |
| q048 | Hanya satu dokumen gold | Diterima sebagai known partial multi-hop; jangan backfill tanpa bukti |
| Audit C | Verdict C 145 klaim belum diaudit provenance | C-owned; optional +3-4 jam |
| E6-E8 | Not Evaluated | Perlu acceptance jika rubrik menuntut semua kode |

## Status merge

Branch ini belum di-merge ke `dev`/`main`. Jangan push tanpa permintaan.
Commit closeout D ada di branch `feat/w2-d-finalize-qrels-v2`:

- `0497de8` - finalisasi qrels v2 dan agreement tooling.
- `c674d28` - error taxonomy dan A1 v2.
- commit dokumentasi - HEAD branch setelah handoff ini.
