# Handoff W3-C - Status, Blocker, dan Action Request

- **Owner:** C (Dhea)
- **Tanggal:** 2026-11-27
- **Branch kerja:** `feat/w3-c-lora-b5`
- **Base:** `w3-base-a3` (`3af39db`)
- **Branch test-50 (rencana):** `feat/w3-c-b5-test50` dari `w3-config-frozen`
- **Adapter:** `w3-c-adapter/adapter`
- **Adapter SHA-256:** `392fe5f5fd1b9b11676fc06fd5318757edaf887275c0745397660f1bf469b58e`
- **Dataset SHA-256:** `20deed873ddc10a734709590ccdbf3be84b78ff78d6e516c7e11aa143534f827`
- **Drive adapter:** https://drive.google.com/drive/folders/1BT67FGjPQKgVeCwYP-S1JJeWEkBG3917?usp=sharing

## 1. Status

- [x] Dataset v2
- [x] Training adapter v2
- [x] Package adapter v2
- [x] Sanity B5 v2
- [x] B4 control
- [x] Frozen config tag terverifikasi
- [ ] B5 train-65 full
- [ ] B5 OOD 1824 full
- [ ] B5 test-50
- [ ] 3 seed B4/B5
- [ ] Reports merged
- [ ] Gate 3

**Status keseluruhan:** PARTIAL / BLOCKED.

## 2. Ringkasan

Adapter v2 sudah selesai dan dipaketkan. Schema valid 10/10 dan tidak ada
echo ID training. Namun sanity 10 query masih 10/10 abstain.

B4 control tanpa adapter juga abstain 9/10, dan B4 test-50 dari Lois
melaporkan abstain 39/50 (78%). Jadi over-abstain bersifat sistemik:
retrieval + verifier + prompt, bukan hanya LoRA.

## 3. Angka kunci

### 3.1 Training v2

| Item | Nilai |
| --- | ---: |
| Dataset | 700 contoh |
| Train / val | 527 / 173 |
| Steps | 66 |
| Epoch | 1 |
| Wall time | 16.808,42 s |
| Peak RSS | 2.611,6 MB |
| Eval loss | 0.0306 -> 0.0150 -> 0.0121 |
| Adapter SHA-256 | `392fe5f5...` |

### 3.2 B5 v2 sanity vs B4 control

| Metrik | B5 v2 | B4 |
| --- | ---: | ---: |
| n | 10 | 10 |
| schema valid | 10/10 | 8/10 |
| abstain | 10/10 | 9/10 |
| ID echo | 0 | 0 |
| q021 benar | tidak | ya |

### 3.3 B4 test-50 (dari Lois)

Sumber: `reports/b4_test50.md` di branch `origin/feat/w3-a-calibration`.

| Metrik | Nilai |
| --- | ---: |
| Query | 50 |
| Schema valid | 49/50 |
| Abstain | 39/50 (78%) |
| Klaim SUPPORTED | 14 |
| Klaim REFUTED | 9 |
| Klaim dropped | 24 |
| Abstain karena verifikasi | 20 dari 39 |
| Latency p50 | 43.441,1 ms |
| Latency p95 | 82.027,8 ms |

Temuan penting dari A:

- `q099` (no-evidence) menghasilkan 3 klaim SUPPORTED.
- `q062` (temporal 1851 vs 1871) salah menyimpulkan "both peel".
- Sebagian besar abstain bukan dari tau sufficiency, tapi dari verifikasi NLI
  dan pembuangan klaim.

## 4. Bukti per query sanity B5 v2

| Query | Temuan | Penyebab | Owner |
| --- | --- | --- | --- |
| q001 | gold tidak ada di top 10 | retrieval | Vio |
| q005 | gold tidak ada di top 10 | retrieval | Vio |
| q010 | 1824, abstain | OOD/retrieval | Vio/Lois |
| q021 | B4 benar "1 hour" | pipeline bisa | Vio/Anin |
| q040 | 1824, format_error di B4 | OOD/format | Vio/Lois |
| q043 | evidence ada, abstain | verifier/prompt | Anin/Vio |
| q071 | 1824/1871, abstain | OOD/verifier | Anin/Vio |
| q082 | evidence ada, out_of_period | verifier/OOD | Anin/Vio |
| q094 | no-evidence, abstain | benar | - |
| q115 | no-evidence, abstain | benar | - |

## 5. Root cause

1. v1 menghafal karena `target.query_id = example_id`, template seragam,
   dan validasi doc-only.
2. v2 memperbaiki: `query_id="q"`, 4 template, template holdout, abstain 60.
3. v2 tidak echo ID dan eval loss bagus, jadi memorization utama sudah hilang.
4. Masalah tersisa: task mismatch + retrieval + verifier + prompt + 1824 OOD.
5. B4 control dan B4 test-50 membuktikan over-abstain juga terjadi tanpa adapter.

## 6. Frozen config

- Handoff A menyebut freeze di commit `a6b7a26`, tag `w3-config-frozen`.
- Branch `origin/feat/w3-a-calibration` sudah berisi commit tersebut.
- **Tag `w3-config-frozen` sudah di-push dan terverifikasi di remote**
  (2026-11-28). Annotated object `ca35609` -> commit `a6b7a26`.
  `configs/b4.yaml` SHA-256 `57339e7b6b4a9d06630f26d7485d80d7fc2e5469c1fe5ab35831b240029c6a44`.
- `configs/b4.yaml` frozen berisi:
  - `verification.premise_context: true`
  - `nli_threshold: 0.5`
  - `abstain.sufficiency: true`
  - `sufficiency_threshold: 0.17`
  - citation/temporal gate aktif
- `reports/b4_train65.md` belum ada di branch A.
- Jangan memakai `w3-base-a3` sebagai base test-50 karena `configs/b4.yaml`
  sudah berubah.

## 7. Mengapa harus diperbaiki

| Orang | Alasan | Bukti | Dampak jika tidak |
| --- | --- | --- | --- |
| Lois (A) | Tag frozen di-push & terverifikasi (2026-11-28) | remote tag `ca35609` -> `a6b7a26` | selesai |
| Lois (A) | B4 train-65 report belum ada | `reports/b4_train65.md` tidak ditemukan | train-test gap B4 belum bisa dihitung |
| Anin (B) | Verifier terlalu agresif | B4 test-50: 20/39 abstain dari verifikasi; q099 false confident | B5 abstain walau evidence ada |
| Anin (B) | Ada error temporal | q062 salah menyimpulkan "both peel" | temporal slice tidak valid |
| Vio (D) | Retrieval miss | q001/q005 gold tidak ada di top 10 | model tidak punya evidence |
| Vio (D) | A6 + test-50/3-seed ada di scope D | B4 test-50 abstain 78% | test-50 tetap over-abstain |
| Dhea (C) | Dataset belum mewakili tipe pertanyaan benchmark | dataset hanya 5 jenis; benchmark how long/how many/temporal | model default abstain |
| Dhea (C) | B5 train-65/OOD/test-50 belum jalan | sanity gagal | acceptance B5 belum lengkap |

## 8. Branch map

| Orang | Branch | Base | Tugas | Merge/tag |
| --- | --- | --- | --- | --- |
| Lois | `feat/w3-a-calibration` | `w3-base-a3` | tau, B4 test-50, freeze | `feat/w3-integration` + tag `w3-config-frozen` |
| Anin | `feat/w3-b-verifier-w3` (baru) | `w3-base-a3` | audit verifier/abstain, B4 report | integration sebelum freeze |
| Vio prep | `feat/w3-d-prep` | `w3-base-a3` | A3/A6 train-65 | integration sebelum freeze |
| Vio test | `feat/w3-d-ablation-test` | `w3-config-frozen` | A3/A6/B4/B5 test-50, 3 seed | integration setelah test |
| Dhea | `feat/w3-c-lora-b5` | `w3-base-a3` | dataset/training/adapter/B5 | PR ke integration |
| Dhea test | `feat/w3-c-b5-test50` | `w3-config-frozen` | B5 test-50 + report | PR ke integration |

Catatan:

- Jangan lanjut branch arsip Anin (`feat/w3-b-dev`, `feat/w3-b-verifier-dev`).
- Jangan checkout tag tanpa membuat branch.
- Jangan merge langsung ke `dev`/`main`.
- Adapter tidak masuk Git; lewat Drive.
- Jangan memakai branch pribadi orang lain; gunakan tag `w3-config-frozen`.

## 9. Action items

### Lois (A)

1. ~~Push tag `w3-config-frozen` di commit `a6b7a26`~~ (selesai 2026-11-28).
2. ~~Share commit hash + hash `configs/b4.yaml`~~ (selesai 2026-11-28).
3. Share/lengkapi `reports/b4_train65.md`; jangan label `b4_calib` sebagai B4 final.
4. Review config B4/B5 dan pastikan tidak ada tuning di test-50.

### Anin (B)

1. Audit verifier/abstain pada frozen threshold: 20/39 abstain dari verifikasi.
2. Audit `q099` (false confident) dan `q062` (temporal salah).
3. Jangan recalibrate threshold tanpa persetujuan Lois; fokus pada logic
   claim dropping/verification.
4. Lengkapi `reports/b4_train65.md` dari run B4 yang valid.

### Vio (D)

1. Download `w3-c-adapter/`, verifikasi SHA256SUMS.
2. Perbaiki retrieval/A6: q001/q005 gold tidak ada di top 10.
3. A3/A6 train-65 sebelum freeze.
4. Setelah freeze: A3/A6/B4/B5 test-50.
5. 3 seed subset B4/B5.
6. Catat adapter path + hash di `reports/b5_test50.md`.

### Dhea (C)

1. Commit kode/dataset/test, tanpa adapter/logs.
2. Setelah tag frozen ada: buat `feat/w3-c-b5-test50` dari `w3-config-frozen`.
3. Merge/cherry-pick B5 code ke branch test-50.
4. Refresh `configs/b5.yaml` = B4 frozen + adapter.
5. Jalankan test config equality.
6. Full B5 train-65 + OOD setelah pipeline fix.
7. B5 test-50 setelah freeze.
8. Tulis `reports/b5_train65.md` dan `reports/b5_test50.md`.
9. PR ke `feat/w3-integration`.

## 10. Artefak

| Artefak | Path | Status |
| --- | --- | --- |
| Adapter package | `w3-c-adapter/` | Drive: link di atas |
| Adapter hash | `w3-c-adapter/SHA256SUMS.txt` | verified |
| B5 sanity | `artifacts/runs/b5-v2-sanity/` | ada |
| B4 control | `artifacts/runs/b4-sanity/` | ada |
| B4 test-50 (audit) | `artifacts/runs/b4-test50-s1/` | Drive: https://drive.google.com/drive/folders/1ou6L22amy3z605wMoiQkZS_iwwmRfAd0 |
| B5 test-50 | `artifacts/runs/b5-test50-s1/` | pending |
| B5 report | `reports/b5_test50.md` | pending |
| Training log | `train/logs/resource.json` | ada |
| Dataset hash | `train/dataset.sha256` | ada |

## 11. Blockers

1. `reports/b4_train65.md` belum ada (run B4 train-65 sudah selesai; report milik B).
2. B5 train-65 full dan OOD 1824 belum jalan.
3. B5 test-50 belum bisa jalan.
4. Keputusan pipeline-first vs v3 belum diambil.

## 12. Keputusan yang dibutuhkan

1. **Pipeline-first:** perbaiki retrieval/verifier/prompt, lalu ulang B5.
2. **v3 dataset:** hanya jika setelah pipeline fix adapter masih over-abstain.
3. **Negative result:** dokumentasikan v2 + B4 control/B4 test-50 jika waktu
   tidak cukup.

## 13. Urutan merge

1. Anin verifier/abstain audit -> integration.
2. Vio A3/A6 prep -> integration.
3. Lois tau + B4 test-50 -> integration.
4. Lois tag `w3-config-frozen`.
5. Vio branch dari tag; Dhea branch dari tag.
6. Test-50 B4/B5; 3 seed.
7. Lois tag `w3-test-s1`.
8. Gate 3.

## 14. Guardrail

- Jangan tuning di test-50.
- Jangan pakai passage test/1824 untuk training LoRA.
- Jangan commit adapter/logs.
- Jangan merge langsung ke `dev`/`main`.
- Jangan checkout tag tanpa branch.
- Jangan pakai branch pribadi orang lain; pakai `w3-config-frozen`.
- Kalau pipeline fix setelah freeze, freeze harus diulang.
