# Verifier calibration — NLI threshold (Week 3, train-65)

- **Owner:** B (Anin)
- **Tanggal:** 2026-11-26
- **Branch:** `feat/w3-b-verifier-dev`
- **Split:** `benchmark/query_split.json` (commit `c812369`, di-vendor di `351f9a5`), seed 42
- **Model:** `cross-encoder/nli-deberta-v3-base`
- **Evaluasi:** hanya 65 train; 50 test tidak disentuh
- **Artefak angka:** `reports/verifier_calibration.json`, `reports/verifier_calibration_table.md`, `reports/verifier_calibration_nocontext.json`, `benchmark/nli_probe_train.jsonl`

## Ringkasan

Ambang NLI **0,5** dipertahankan, tetapi premise verifier harus menyertakan konteks resep/buku/tahun:

| Metrik | Nilai |
| --- | ---: |
| Threshold | **0,5** |
| Precision | **0,8824** |
| Recall | **0,8571** |
| F1 | **0,8696** |
| Balanced accuracy | **0,9042** |
| Pasangan kalibrasi | 117 (35 gold, 82 negatif sintetis) |

Tanpa konteks premise, model yang sama hanya mencapai balanced accuracy 0,6225 pada pasangan yang sama. Jadi perbaikan utama bukan pada threshold, melainkan pada **premise**.

## Setup

| Item | Nilai |
| --- | --- |
| Query train | 65 (20 easy, 14 multi-hop, 17 temporal, 14 no-evidence) |
| Query dengan gold claim | 51 |
| Gold pair probe | 317 (semua slice) |
| Pasangan kalibrasi | 35 positif (easy) + 82 negatif sintetis |
| Premise | `recipe title. book title (year). passage text` |
| Threshold grid | 0,30–0,90, langkah 0,05 |

Alasan pembatasan positif ke slice `easy`: klaim multi-hop dan temporal adalah klaim agregat lintas dokumen, sehingga satu passage tidak seharusnya meng-entail klaim tersebut. Positif dari slice itu tetap disimpan di probe sebagai diagnostik cakupan (lihat bawah), tetapi tidak dipakai memilih threshold.

Negatif sintetis: klaim yang sama dipasangkan dengan passage dari dokumen lain, dipilih berdasarkan overlap token tertinggi (hard negative), kandidat dibatasi `split=test`, dokumen gold query dikecualikan. Seed 42, satu negatif per klaim.

## Hasil sweep

Tabel lengkap ada di `reports/verifier_calibration_table.md`. Ringkas:

| Threshold | Precision | Recall | F1 | Balanced accuracy |
| ---: | ---: | ---: | ---: | ---: |
| 0,30 | 0,8824 | 0,8571 | 0,8696 | 0,9042 |
| 0,50 | 0,8824 | 0,8571 | 0,8696 | 0,9042 |
| 0,60 | 0,8788 | 0,8286 | 0,8529 | 0,8899 |
| 0,70 | 0,8750 | 0,8000 | 0,8358 | 0,8756 |
| 0,90 | 0,8750 | 0,8000 | 0,8358 | 0,8756 |

0,5 dipilih karena berada di dataran tertinggi dan sama dengan default P0, sehingga tidak perlu mengubah config hanya untuk threshold.

## Ablasi: konteks premise

| Setup | Threshold terpilih | Precision | Recall | F1 | Balanced accuracy |
| --- | ---: | ---: | ---: | ---: | ---: |
| Tanpa konteks (passage text saja) | 0,85 | 0,9000 | 0,2571 | 0,4000 | 0,6225 |
| Dengan konteks (resep + buku + tahun) | **0,50** | **0,8824** | **0,8571** | **0,8696** | **0,9042** |

Tanpa konteks, klaim yang menyebut tahun/resep — mis. “The 1796 cheap seed cake is baked for one and a half hours.” — diberi entailment ±0,00 karena judul resep tidak ada di teks passage. Setelah judul resep dari `doc_id` dan buku/tahun ditambahkan, skor melonjak ke ±0,99. Ini bug desain P0, bukan masalah threshold.

## Cakupan positif per slice (dengan konteks, threshold 0,5)

| Slice | Positif | Mean entailment | Didukung |
| --- | ---: | ---: | ---: |
| easy | 35 | 0,8381 | 30/35 |
| multi-hop | 90 | 0,5473 | 49/90 |
| temporal | 110 | 0,4548 | 50/110 |

Implikasi: NLI per passage hanya layak untuk klaim atomik. Klaim multi-hop/temporal yang menggabungkan dua dokumen tetap sering NEUTRAL meskipun konteks ditambahkan; klaim seperti ini harus didekomposisi planner sebelum diverifikasi, atau diverifikasi per sub-klaim. Jangan memakai verdict NLI atas klaim agregat sebagai ground truth.

## Analisis error (easy, threshold 0,5)

5 positif di bawah threshold:

- `q019` “The cooked apple mixture stands for twelve hours.” (2 passage, 0,005 dan 0,046) — klaim meringkas proses yang tidak dinyatakan eksplisit di passage.
- `q003` “The bottles are kept in slowly boiling water for half an hour.” (0,011) — parafrase jauh dari teks passage.
- `q013` “The bread steeps in hot steam for about three quarters of an hour.” (0,097) — jarak leksikal.
- `q014` “The 1851 boiled Indian pudding is boiled for at least four hours.” (0,163 pada satu passage; 0,531 pada passage lain) — salah satu gold passage tidak memuat durasi.

4 negatif di atas threshold:

- `q090` vs `tripe-and-oysters` (0,994), `q013` vs `neapolitan-pudding` (0,989), `q032` vs `tomato-cream-sauce` (0,969), `q046` vs `tomata-honey-2` (0,939).

Tiga pertama adalah **label noise**: passage dari resep lain memakai bahan/prosedur yang sangat mirip (overlap token q013 = 0,714), sehingga secara semantik memang mendukung klaim. Ini batas konstruksi negatif sintetis, bukan semata kesalahan model. Presisi 0,88 karena itu bersifat konservatif.

## Rekomendasi

1. Aktifkan `verification.premise_context: true` untuk B4 setelah review A. Config contoh: `configs/b4_verify.yaml`.
2. Pertahankan threshold 0,5; jangan menurunkannya untuk mengejar recall — dataran 0,3–0,5 identik.
3. Jangan memakai NLI untuk memutus klaim multi-hop/temporal agregat; dekomposisi dulu (planner), lalu verifikasi per sub-klaim.
4. Ukur false refusal pada no-evidence train (14 query) saat menjalankan B4 di train-65; angka di laporan ini belum mencakup abstain end-to-end.
5. `keep_refuted=false` tetap dipertahankan sampai ada bukti bahwa pembuangan klaim REFUTED tidak menaikkan false refusal.

## Batasan

- Negatif sintetis, bukan label manusia; precision/recall adalah probe, bukan akurasi berlabel.
- Positif easy hanya 35; interval kepercayaan belum dihitung.
- Threshold dipilih pada train-65; angka final tetap dari test-50 setelah config freeze.
- Klaim gold bisa lebih abstrak daripada klaim yang dihasilkan model; kalibrasi ini tidak mengukur distribusi klaim B4 sebenarnya.

## Reproduksi

```powershell
uv run python tools/calibrate_nli.py `
  --queries benchmark/queries_train.jsonl --qrels benchmark/qrels.jsonl `
  --slices easy --premise-context `
  --probe-out benchmark/nli_probe_train.jsonl `
  --out reports/verifier_calibration.json `
  --markdown reports/verifier_calibration_table.md

uv run python tools/calibrate_nli.py `
  --queries benchmark/queries_train.jsonl --qrels benchmark/qrels.jsonl `
  --slices easy `
  --out reports/verifier_calibration_nocontext.json
```
