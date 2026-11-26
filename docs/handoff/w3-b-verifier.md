# Handoff W3-B — verifier, citation/temporal, dan abstain

- **Owner:** B (Anin)
- **Branch:** `feat/w3-b-verifier-dev`
- **Base:** tag `w3-base-a2` (`ba9574d`)
- **Tanggal:** 2026-11-26
- **Status:** modul dan tool siap; kalibrasi NLI dan `reports/verifier_calibration.md` menunggu split train-65

## 1. Yang ditambahkan

| File | Isi |
| --- | --- |
| `src/recipe_qa/verify/citations.py` | `check_citations`: sitasi ke passage yang tidak ada di hasil retrieval, span bukti yang tidak ada di passage, klaim tanpa bukti |
| `src/recipe_qa/verify/temporal.py` | `check_temporal`: tahun klaim > `as_of`, tahun bukti > `as_of`, ketidakcocokan tahun klaim vs bukti |
| `src/recipe_qa/pipeline/abstain.py` | `AbstainPolicy`, `decide_abstain`: alasan `no_recipe`, `format_error`, `citation_failure`, `temporal_violation`, `not_specified` |
| `src/recipe_qa/eval/nli_calibration.py` | `build_probe`, `sweep_thresholds`, `select_threshold`, `calibrate` |
| `tools/calibrate_nli.py` | CLI probe + sweep NLI |
| `configs/b4_verify.yaml` | B4 + `abstain.citations: true` + `abstain.temporal: true` (eksperimen B, bukan pengganti `configs/b4.yaml`) |

Perubahan aditif:

- `AbstainConfig`: `citations`, `temporal`, `require_evidence` (default `false`; config lama tidak berubah).
- `AbstainReason`: tambah `citation_failure` dan `temporal_violation`.
- `pipeline/common.py`: metadata `citations`, `temporal`, `abstain` hanya ditulis bila flag aktif; output B0–B3 tidak berubah.

## 2. Perilaku

- `config.abstain.citations` → klaim yang menyitir passage di luar retrieved set memicu abstain `citation_failure`.
- `config.abstain.temporal` → klaim/bukti melewati `as_of` memicu abstain `temporal_violation`.
- `config.abstain.require_evidence` → klaim tanpa bukti ikut memicu `citation_failure`.
- Semua default mati; A3/A6 tetap memakai `configs/a3_verify.yaml` sampai kalibrasi selesai.

## 3. Kalibrasi NLI (belum dijalankan)

Tool membutuhkan file split train-65 dari `feat/w3-b-dev`. Di branch ini file tersebut belum ada; jalankan setelah split di-tag/merge:

```powershell
uv run python tools/calibrate_nli.py `
  --queries benchmark/queries_train.jsonl `
  --qrels benchmark/qrels.jsonl `
  --probe-out benchmark/nli_probe_train.jsonl `
  --out reports/verifier_calibration.json `
  --markdown reports/verifier_calibration.md
```

- Positif: gold claim × gold passage.
- Negatif: klaim yang sama × passage dokumen lain dengan overlap token tertinggi (hard synthetic negative).
- Kandidat negatif dibatasi `split=test` agar domain sama; dokumen gold query dikecualikan.
- Ambang dipilih dari balanced accuracy; tie-break F1 lalu threshold lebih tinggi.
- Laporan wajib menyebut negatif sintetis; jangan klaim sebagai akurasi berlabel manusia.

Dry-run probe pada 115 query menghasilkan 569 pasangan (424 gold, 145 sintetis); train-65 akan lebih kecil.

## 4. Yang belum selesai

- `reports/verifier_calibration.md`: menunggu split train-65 + model NLI.
- `reports/b4_dev.md`: menunggu run B4 milik A di train-65.
- Evaluasi citation/temporal pada sample: jalankan `configs/b4_verify.yaml` di train-65 setelah config freeze.
- `docs/open_questions.md` Q13: protokol negatif sintetis perlu ACC A.

## 5. Verifikasi

- `uv run pytest -q`: lulus (215 test).
- `uv run ruff check .`: bersih.
- Tidak ada perubahan pada `benchmark/queries.jsonl`, `qrels.jsonl`, `verdict_qrels.jsonl`, `manifest.sha256`, atau config A.
