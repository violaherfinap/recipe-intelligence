# Handoff W3-B — verifier, citation/temporal, dan abstain

- **Owner:** B (Anin)
- **Branch:** `feat/w3-b-verifier-dev`
- **Base:** tag `w3-base-a2` (`ba9574d`)
- **Tanggal:** 2026-11-26
- **Status:** modul, tool, dan kalibrasi NLI selesai; `reports/b4_dev.md` menunggu run B4 milik A

## 1. Yang ditambahkan

| File | Isi |
| --- | --- |
| `src/recipe_qa/verify/citations.py` | `check_citations`: sitasi ke passage yang tidak ada di hasil retrieval, span bukti yang tidak ada di passage, klaim tanpa bukti |
| `src/recipe_qa/verify/temporal.py` | `check_temporal`: tahun klaim > `as_of`, tahun bukti > `as_of`, ketidakcocokan tahun klaim vs bukti |
| `src/recipe_qa/verify/premise.py` | `premise_text`: judul resep dari `doc_id` + buku + tahun + teks passage untuk premise NLI |
| `src/recipe_qa/pipeline/abstain.py` | `AbstainPolicy`, `decide_abstain`: alasan `no_recipe`, `format_error`, `citation_failure`, `temporal_violation`, `not_specified` |
| `src/recipe_qa/eval/nli_calibration.py` | `build_probe`, `sweep_thresholds`, `select_threshold`, `calibrate` |
| `tools/calibrate_nli.py` | CLI probe + sweep NLI |
| `configs/b4_verify.yaml` | B4 + citation/temporal + `premise_context: true` (eksperimen B, bukan pengganti `configs/b4.yaml`) |
| `reports/verifier_calibration.md` | Hasil kalibrasi, ablasi konteks, analisis error |

Perubahan aditif:

- `AbstainConfig`: `citations`, `temporal`, `require_evidence` (default `false`; config lama tidak berubah).
- `VerificationConfig`: `premise_context` (default `false`; B0-B3 dan `b4.yaml` tidak berubah).
- `AbstainReason`: tambah `citation_failure` dan `temporal_violation`.
- `pipeline/common.py`: metadata `citations`, `temporal`, `abstain` hanya ditulis bila flag aktif; output B0–B3 tidak berubah.

## 2. Perilaku

- `config.abstain.citations` → klaim yang menyitir passage di luar retrieved set memicu abstain `citation_failure`.
- `config.abstain.temporal` → klaim/bukti melewati `as_of` memicu abstain `temporal_violation`.
- `config.abstain.require_evidence` → klaim tanpa bukti ikut memicu `citation_failure`.
- Semua default mati; A3/A6 tetap memakai `configs/a3_verify.yaml` sampai kalibrasi selesai.

## 3. Kalibrasi NLI (selesai di train-65)

Hasil lengkap: `reports/verifier_calibration.md`. Ringkas:

| Item | Nilai |
| --- | ---: |
| Threshold | **0,5** |
| Precision | **0,8824** |
| Recall | **0,8571** |
| F1 | **0,8696** |
| Balanced accuracy | **0,9042** |
| Pasangan | 117 (35 gold easy + 82 negatif sintetis) |

Ablasi premise:

| Setup | Threshold | Precision | Recall | BA |
| --- | ---: | ---: | ---: | ---: |
| Tanpa konteks | 0,85 | 0,9000 | 0,2571 | 0,6225 |
| Dengan konteks resep/buku/tahun | **0,50** | **0,8824** | **0,8571** | **0,9042** |

Cakupan positif per slice (konteks aktif, threshold 0,5): easy 30/35, multi-hop 49/90, temporal 50/110. Klaim agregat multi-hop/temporal tidak bisa diverifikasi oleh satu passage; dekomposisi planner tetap diperlukan.

Reproduksi:

```powershell
uv run python tools/calibrate_nli.py `
  --queries benchmark/queries_train.jsonl --qrels benchmark/qrels.jsonl `
  --slices easy --premise-context `
  --probe-out benchmark/nli_probe_train.jsonl `
  --out reports/verifier_calibration.json `
  --markdown reports/verifier_calibration_table.md
```

- Positif: gold claim easy × gold passage (klaim atomik).
- Negatif: klaim yang sama × passage dokumen lain dengan overlap token tertinggi (hard synthetic negative); kandidat `split=test`, dokumen gold dikecualikan.
- Ambang dipilih dari balanced accuracy; tie-break F1 lalu threshold lebih tinggi.
- Negatif sintetis, bukan label manusia; 4 negatif di atas threshold adalah label noise (resep lain dengan prosedur hampir sama).

## 4. Yang belum selesai

- `reports/b4_dev.md`: menunggu run B4 milik A di train-65.
- Evaluasi citation/temporal end-to-end: jalankan `configs/b4_verify.yaml` di train-65 setelah config freeze.
- Keputusan A: apakah `premise_context: true` masuk `configs/b4.yaml`; sementara ini hanya di `b4_verify.yaml`.
- `docs/open_questions.md` Q13: protokol negatif sintetis perlu ACC A.

## 5. Verifikasi

- `uv run pytest -q`: lulus (222 test).
- `uv run ruff check .`: bersih.
- Tidak ada perubahan pada `benchmark/queries.jsonl`, `qrels.jsonl`, `verdict_qrels.jsonl`, `manifest.sha256`, atau config A.
