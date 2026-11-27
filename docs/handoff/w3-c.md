# Handoff W3-C - LoRA dataset, adapter, dan B5 (progress)

> **Status terbaru dan action request:** lihat `docs/handoff/w3-c-status.md`.

- **Owner:** C (Dhea)
- **Branch:** `feat/w3-c-lora-b5`
- **Base:** `w3-base-a3` (`3af39db`)
- **Tanggal:** 2026-11-27
- **Status:** adapter v2 selesai, package candidate siap; sanity B5 v2 gagal karena over-abstain, B4 control menunjukkan masalah sistemik; full eval/test-50 ditahan
- **Handoff ke:** D (Vio) sebagai candidate; test-50 menunggu `w3-config-frozen`

## Ringkasan

Pipeline LoRA dibangun dari nol karena `train/` sebelumnya kosong. Dataset v1
700 contoh dibuat hanya dari passage `split=train` dan **bukan** tahun 1824.
Training v1 selesai 1 epoch dan B5 train-65 v1 sudah dievaluasi, tetapi model
overfit: 60/65 query abstain dan raw output memantulkan `example_id` training.
Dataset v2 sudah diregenerate dengan `query_id` konstan, 4 variasi template,
dan abstain dikurangi dari 100 ke 60. Split validasi memakai strict template
holdout: 527 contoh train, 173 contoh val, dan 1 template per jenis tidak
pernah masuk training. Training v2 selesai 66 step dengan eval loss
`0.0306 -> 0.0150 -> 0.0121`. Sanity 10 query v2 gagal karena **10/10 abstain**
(tidak echo ID training, schema valid 10/10). B4 control pada query yang sama
juga abstain 9/10, jadi over-abstain bersifat sistemik (retrieval/verifier/
prompt), bukan hanya adapter. Adapter v2 sudah dipaketkan sebagai candidate.

## Angka kunci

| Item | Nilai |
| --- | ---: |
| Dataset v2 | 700 contoh |
| Komposisi v2 | 270 ingredients, 270 directions, 100 metadata, 30 no_recipe, 30 out_of_period |
| Template v2 | 4 variasi per jenis, `template_id` per contoh |
| Dokumen sumber unik | 700 |
| Passage test di dataset | 0 |
| Passage 1824 di dataset | 0 |
| Target schema invalid | 0 |
| SHA-256 dataset v2 | `20deed873ddc10a734709590ccdbf3be84b78ff78d6e516c7e11aa143534f827` |
| SHA-256 dataset v1 | `7b76145dce1d3f0a8e14cfec6eea09788287d9b5e533301b0d944494f0f3b575` (arsip) |
| Training v1 | 700 contoh, 1 epoch, 84 step, 19.016 detik, peak RSS 2.634,8 MB |
| Adapter v1 | 35.237.104 byte, SHA-256 `77bf805d9e1eb0f9589bb38e3074fe577878dcc25a1604477374c6049cca12b1` |
| B5 train-65 v1 | 65/65 schema valid, 60/65 abstain (92,3%), hanya 5 menjawab |
| OOD 1824 v1 | 10/10 abstain |
| Split v2 | 527 train / 173 val; template holdout per jenis |
| Val templates v2 | `directions_cook`, `ingredients_goes_into`, `metadata_when_book`, `no_recipe_list`, `out_of_period_method` |
| Training v2 | 66 step, 16.808,42 detik, peak RSS 2.611,6 MB |
| Eval loss v2 | 0.0306 (20) -> 0.0150 (40) -> 0.0121 (60) |
| Adapter v2 | 35.237.104 byte, SHA-256 `392fe5f5fd1b9b11676fc06fd5318757edaf887275c0745397660f1bf469b58e` |
| Sanity v2 | 10/10 schema valid, 10/10 abstain (9 no_recipe, 1 out_of_period) |
| B4 control | 8/10 schema valid, 9/10 abstain; `q021` benar |
| Package adapter | `w3-c-adapter/`, total 48.213.967 byte |
| Test | 236 lulus |
| Ruff | bersih |

## Artefak

| Artefak | Path | Status |
| --- | --- | --- |
| Builder dataset | `train/build_dataset.py` | commit |
| Logika dataset | `src/recipe_qa/training/dataset.py` | commit |
| Dataset v2 | `train/dataset.jsonl` | commit |
| Hash dataset v2 | `train/dataset.sha256` | commit |
| Audit dataset v2 | `train/dataset_audit.json` | commit |
| Arsip dataset v1 | `train/archive/v1/` | lokal, gitignored |
| Arsip adapter v1 | `train/archive/v1/adapter/` | lokal, gitignored |
| Arsip log v1 | `train/archive/v1/logs/` | lokal, gitignored |
| Config training | `train/lora_config.yaml` | commit |
| Script training | `train/train_lora.py` | commit |
| Config B5 | `configs/b5.yaml` | commit; refresh setelah freeze |
| Dukungan adapter | `src/recipe_qa/config.py`, `src/recipe_qa/generation/generate.py` | commit |
| Test dataset | `tests/unit/test_lora_dataset.py` | commit |
| Test config B4/B5 | `tests/unit/test_config_equality.py` | commit |
| Adapter v2 | `train/adapter/` | lokal, gitignored |
| Log v2 | `train/logs/` | lokal, gitignored |
| Package adapter v2 | `w3-c-adapter/` | lokal, gitignored; candidate untuk Vio |
| Hasil B5 train-65 v1 | `artifacts/runs/b5-train65-s1/` | lokal, gitignored |
| Sanity B5 v2 | `artifacts/runs/b5-v2-sanity/` | lokal, gitignored |
| B4 control | `artifacts/runs/b4-sanity/` | lokal, gitignored |
| Adapter smoke | `train/smoke_adapter/` | lokal, gitignored |
| Log smoke | `train/smoke_logs/` | lokal, gitignored |

## Keputusan dan catatan

- Dataset **tidak** memakai query/qrels benchmark. Semua contoh dibangun dari
  `data/processed/docs.jsonl` dan `passages.jsonl`.
- Tahun **1824 dikeluarkan** dari dataset karena dipakai sebagai OOD, walaupun
  sebagian dokumen 1824 berstatus `split=train`.
- Prompt training memakai registry `structured_v1` yang sama dengan inference.
- Target JSON mengikuti `AnswerPayload`: `query_id`, `answer`, `abstain`,
  `abstain_reason`, `confidence`, `schema_valid`.
- **Akar masalah v1:** `target.query_id` diisi `example_id` training sehingga
  model menghafal ID (`out_of_period_0030`, `metadata_0037`) dan abstain
  berlebihan. Dataset v2 memakai `query_id` konstan `"q"`.
- Dataset v2 menambah `template_id` dan 4 variasi template per jenis; abstain
  diturunkan ke 60 contoh (30 `no_recipe`, 30 `out_of_period`).
- Hyperparameter LoRA v2 **tidak diubah** (`r=16`, `alpha=32`, `dropout=0.05`,
  1 epoch) agar perbaikan dataset terisolasi.
- Validasi v2 memakai **strict template holdout** (`val_mode: template_holdout`):
  satu template per jenis dipilih deterministik dan tidak masuk training.
  Tujuannya mengukur generalisasi ke gaya pertanyaan baru, bukan menghafal
  template. Dokumen train/val otomatis disjoint karena 1 dokumen = 1 contoh.
- **Sanity v2 gagal:** 10/10 abstain. Tidak ada echo ID training dan schema
  valid 10/10, tetapi `q001`, `q005`, `q010`, `q021`, `q040`, `q043`, `q071`
  salah abstain; `q082` `out_of_period`; hanya `q094`/`q115` (no-evidence)
  yang benar abstain.
- **B4 control:** 8/10 schema valid, 9/10 abstain; `q021` dijawab benar
  ("one hour"), `q040`/`q094` `format_error`. Karena B4 juga over-abstain,
  masalah utama bukan hanya adapter: retrieval/verifier/prompt ikut bermain.
  Adapter v2 tetap dikirim sebagai **candidate**, bukan final.
- `configs/b5.yaml` saat ini disalin dari `configs/b4.yaml` + adapter. Setelah
  `w3-config-frozen`, config B5 **wajib** di-refresh dari B4 frozen.
- Adapter tidak masuk Git; dataset dan hash masuk Git.

## Perintah

Build ulang dataset:

```powershell
uv run python train/build_dataset.py
```

Smoke training:

```powershell
uv run python train/train_lora.py --smoke
```

Training penuh:

```powershell
uv run python train/train_lora.py --config train/lora_config.yaml
```

Cek adapter bisa di-load:

```powershell
uv run python -c "from recipe_qa.config import ModelConfig; from recipe_qa.generation.generate import AnswerGenerator; g=AnswerGenerator(ModelConfig(adapter='train/adapter', max_new_tokens=8)); print(g.generate('Say OK'))"
```

## Blocker

1. `w3-config-frozen` belum ada; B5 test-50 belum boleh dijalankan.
2. `reports/b4_train65.md` belum ada; pembanding B4 train-65 menunggu Lois/Anin.
3. Hasil B4 test-50 belum ada; pembanding final menunggu Lois/Vio.
4. Sanity v2 gagal (10/10 abstain); full eval B5 v2 belum dijalankan.
5. Over-abstain juga terjadi di B4; perlu keputusan tim soal retrieval/verifier/
   prompt sebelum retrain v3.

## Langkah berikutnya

1. Kirim `w3-c-adapter/` ke Vio sebagai **candidate** + SHA-256; jangan klaim
   final test-50.
2. Minta `w3-config-frozen`, config B4 frozen, dan `reports/b4_train65.md`
   dari Lois.
3. Tunjukkan hasil B4 control vs B5 v2 ke tim: over-abstain sistemik.
4. Putuskan perbaikan pipeline (retrieval/verifier/prompt) atau retrain v3
   dengan tipe pertanyaan benchmark; jangan retrain sebelum keputusan.
5. Setelah `w3-config-frozen`: refresh `configs/b5.yaml`, jalankan B5 test-50
   dengan adapter final, tulis `reports/b5_test50.md`.
6. Update `docs/handoff_log.md`, `docs/contribution_matrix.md`, lalu PR ke
   `feat/w3-integration`.
