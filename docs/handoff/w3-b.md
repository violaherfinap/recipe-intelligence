# Handoff W3-B — split query 65/50 dan rencana verifier

- **Owner:** B (Anin)
- **Branch:** `feat/w3-b-dev`
- **Base:** tag `w3-base-a2` (`ba9574d`)
- **Tanggal:** 2026-11-26
- **Status:** split 65/50 frozen di branch; menunggu review dan tag dari A
- **Menggantikan:** rencana 24 query dev baru di `docs/handoff/w3.md` §5

## 1. Keputusan

Requirement baru: 115 query yang sudah berlabel dibagi menjadi **65 train / 50 test** pada level query. Konsekuensinya:

- Dev set 24 query dari dokumen `split=dev` **dibatalkan**.
- Tidak ada anotasi baru dari C/D; qrels v2 (2.237 baris) sudah mencakup seluruh 115 query.
- Tidak ada pool dev baru.
- 65 train dipakai untuk kalibrasi threshold, τ, dan pemilihan konfigurasi.
- 50 test hanya dipakai untuk angka final setelah config freeze.

## 2. Artefak

| Artefak | Path | SHA-256 |
| --- | --- | --- |
| Peta split + metadata | `benchmark/query_split.json` | — |
| 65 query train | `benchmark/queries_train.jsonl` | `9d000d51...a7b66a` |
| 50 query test | `benchmark/queries_test.jsonl` | `08f4e3fa...b2757c` |
| Tool split | `tools/split_queries.py` | — |
| Logika split | `src/recipe_qa/benchmark/query_split.py` | — |
| Test | `tests/unit/test_query_split.py` | — |

Hash sumber tidak berubah:

- `benchmark/queries.jsonl` = `d5128e48...a27b2ac`
- `benchmark/qrels.jsonl` = `8ed07e8e...38171926`

## 3. Spesifikasi split

| Slice | Total | Train | Test |
| --- | ---: | ---: | ---: |
| `easy` | 35 | 20 | 15 |
| `multi-hop` | 25 | 14 | 11 |
| `temporal` | 30 | 17 | 13 |
| `no-evidence` | 25 | 14 | 11 |
| **Total** | **115** | **65** | **50** |

Metode:

- Query dihubungkan menjadi komponen jika berbagi gold document `relevance=2`.
- 104 gold document, 35 dipakai lebih dari satu query → **88 komponen** (terbesar 5 query).
- Seluruh komponen masuk satu sisi; assignment diselesaikan dengan DP exact-cover dan seed 42.
- Hasil: **54 gold document di train, 50 di test, 0 overlap**. Komponen yang mencakup lebih dari satu slice: 8.
- File query asli tidak diubah; split hanya menambah file turunan.

Reproduksi:

```powershell
uv run python tools/split_queries.py
uv run pytest tests/unit/test_query_split.py -q
```

## 4. Yang harus dilakukan A

1. Review `benchmark/query_split.json` dan method di `src/recipe_qa/benchmark/query_split.py`.
2. Tag split, mis. `w3-query-split`, setelah disetujui.
3. Jalankan ulang baseline B0–B3 pada **50 test**:

   ```powershell
   uv run python tools/eval_retrieval.py --config configs/b3.yaml `
     --queries benchmark/queries_test.jsonl --limit 0 `
     --out artifacts/runs/retrieval_b3_test50.json
   uv run python tools/run_config.py --config configs/b0.yaml `
     --queries benchmark/queries_test.jsonl --limit 0 `
     --out-dir artifacts/runs/b0-test50-s1
   ```

4. Perbarui `reports/b0_b3_test_s1.md` atau tulis laporan test-50 baru. Angka 115 yang lama tetap valid sebagai *development evaluation*, bukan test final.
5. Putuskan apakah hash split masuk `benchmark/manifest.sha256` atau file manifest terpisah.
6. Revisi `docs/handoff/w3.md` §5 (dev 24 → split 65/50) dan tabel branch: C/D tidak lagi membuat `feat/w3-c-dev-label` / `feat/w3-d-dev-label`.

## 5. Yang harus dilakukan C (Dhea)

- Tidak ada branch label dev. Lanjut `feat/w3-c-lora-b5` dari `w3-base-a2`.
- Dataset LoRA tetap hanya dari passage `split=train`. **Jangan** memakai passage gold milik 65 query train sebagai teks training, karena passage itu `split=test` di korpus.
- Evaluasi B5 di train-65 (dev) dan OOD 1824; test-50 hanya setelah `w3-config-frozen`.

## 6. Yang harus dilakukan D (Vio)

- Tidak ada branch label dev. Lanjut `feat/w3-d-prep` dari `w3-base-a2`.
- A3/A6 dijalankan pada train-65 selama fase pengembangan.
- Test B4/B5 pada test-50 hanya setelah `w3-config-frozen`; catat commit config.

## 7. Rencana B selanjutnya (branch verifier)

Branch `feat/w3-b-verifier-dev` dibuat dari `w3-base-a2` setelah `feat/w3-b-dev` di-push.

1. Audit P0: `pipeline/common.py`, `verify/nli.py`, `verify/claims.py`, `verify/sufficiency.py`; jangan duplikasi NLI/repair.
2. Tambah `verify/citations.py`, `verify/temporal.py`, `pipeline/abstain.py`.
3. Kalibrasi NLI/τ di 65 train:
   - positif: gold claim × gold passage;
   - negatif sintetis: klaim yang sama × passage tahun/dokumen lain;
   - sweep threshold, laporkan precision/recall dengan caveat negatif sintetis;
   - probe disimpan di `benchmark/nli_probe_train.jsonl`.
4. Tulis `reports/verifier_calibration.md`.
5. Tulis `reports/b4_dev.md` dari run B4 milik A di train-65; jangan jalankan run duplikat.
6. Semua angka final hanya dari test-50.

## 8. Guardrail

- Jangan mengubah `benchmark/queries.jsonl`, `qrels.jsonl`, `verdict_qrels.jsonl`, atau `manifest.sha256` test.
- Jangan memilih parameter dari test-50.
- Jangan merge branch pribadi ke `dev`/`main`; lewat `feat/w3-integration`.
- Jangan memakai 65 query train sebagai teks training LoRA.
- Jangan memilih split berdasarkan performa model.

## 9. Pertanyaan terbuka

| ID | Isu | Dampak |
| --- | --- | --- |
| Q13 | NLI precision/recall butuh label negatif; `verdict_qrels` hanya punya 1 REFUTED | B memakai probe sintetis dari train-65; opsi label C/D 40–50 pasangan menunggu keputusan A |
| — | Apakah hash split masuk manifest test atau manifest terpisah? | Diputuskan A saat freeze |
