# Week 3 - P0 grounding gate (verifier + abstain + repair)

- **Owner:** D (early Week 3)
- **Tanggal:** 2026-11-25
- **Status:** implementasi selesai; bukti sample sudah ada; kalibrasi train-65
- **Handoff ke:** A/B untuk kalibrasi train-65 dan B4

## Ringkasan

P0 error taxonomy dikerjakan lebih dulu: **E5 overclaim, E7 format error, dan
E8 abstain** (lihat `docs/error_taxonomy.md`). Yang dibangun:

- Verifier NLI per klaim (`cross-encoder/nli-deberta-v3-base`, threshold 0.5).
- Pemecahan jawaban menjadi klaim per kalimat; fragmen trivial dibuang.
- Grounding policy: klaim tanpa dukungan dihapus; jika tidak ada klaim
  terdukung, sistem abstain; jawaban parsial ditulis ulang dari klaim terdukung.
- Repair prompt untuk output JSON invalid (maks. `max_repair_rounds`).
- Sufficiency gate `S = 0.6*sigmoid(rerank_top1) + 0.4*coverage` sudah
  diimplementasikan, tetapi **sengaja dimatikan** karena belum terkalibrasi.

## Perubahan kode

| Artefak | Isi |
| --- | --- |
| `src/recipe_qa/verify/nli.py` | NLI scorer, label mapping dari `id2label` |
| `src/recipe_qa/verify/claims.py` | Verifikasi klaim, prioritas bukti tersitasi, policy drop/abstain |
| `src/recipe_qa/verify/sufficiency.py` | Coverage, sigmoid, skor sufficiency |
| `src/recipe_qa/generation/generate.py` | `build_repair_prompt`, `generate_with_repair` |
| `src/recipe_qa/pipeline/common.py` | Integrasi repair, sufficiency, verifier, metadata hasil |
| `tools/run_config.py` | Load verifier sekali per run; ringkasan verification |
| `configs/a3_verify.yaml` | B3 + verifier + repair, sufficiency **off** |
| `configs/a3_verify_suff.yaml` | Sama, tetapi sufficiency **on** (eksperimen, jangan dipakai untuk klaim) |
| `tests/unit/test_verify_*.py`, `test_generation_repair.py`, `test_pipeline_verify.py` | 22 test baru |

## Hasil sample

### 0. Retrieval taxonomy dihitung ulang

`tools/analyze_retrieval_errors.py` mereproduksi 140 baris identik
(E1=134, E2=6, E4=0). Rincian chunking-aware ada di
`docs/error_taxonomy.md` bagian "Re-check post-P0"; 50 E1 adalah gold
`#fixed#` yang struktural untuk B3 section, sehingga target riil adalah 84 E1.

### 1. No-evidence (6 query audit)

Baseline B3: **0/6 abstain**, semuanya berhalusinasi (`q091`, `q096`, `q101`,
`q106`, `q111`, `q115`). Setelah verifier: **6/6 abstain**.

### 2. Generation audit 24 query

Baseline: 22 error (E3/E5), 1 benar (`q021`), 1 NE (`q060`).

| Hasil setelah verifier | Jumlah |
| --- | ---: |
| Error diblokir (abstain) | **21 / 22** |
| Error residual (tetap dijawab) | 1, yaitu `q071` |
| Jawaban benar dipertahankan | 1, yaitu `q021` |
| NE `q060` (format error) | abstain `format_error` setelah 2 repair |
| No-evidence abstain | 6 / 6 |

`q071` residual adalah entity swap yang tidak bisa dideteksi NLI:
jawaban "Yes, both recipes contain brandy." menggunakan bukti custard sauce,
bukan bread pudding yang diminta. Ini butuh planner/retrieval, bukan verifier.

### 3. Sufficiency gate (proxy 115 query, tanpa generation)

`S < 0.35` abstain pada:

| Slice | Abstain |
| --- | ---: |
| easy | 17 / 35 |
| multi-hop | 23 / 25 |
| temporal | 27 / 30 |
| no-evidence | 25 / 25 |

Gate ini menangkap no-evidence, tetapi **terlalu agresif pada query
answerable**. Skor reranker top-1 sering negatif sehingga `sigmoid` mendekati
0 dan coverage tidak cukup menyelamatkan. **Jangan aktifkan sampai threshold
dikalibrasi di train-65.**

## Latency

24 query audit: p50 **29,2 s**, p95 **55,2 s**, mean 31,7 s (retrieval +
generation + NLI + repair). Tail terpanjang dari query yang gagal repair
(`q060` ±92 s). NLI bukan bottleneck utama; generation dan repair yang mahal.

## Reproduksi

```powershell
uv run python tools/run_config.py --config configs/a3_verify.yaml `
  --query-ids q091 q096 q101 q106 q111 q115 `
  --out-dir artifacts/runs/a3_verify_noevidence

uv run python tools/run_config.py --config configs/a3_verify.yaml `
  --query-ids q001 q006 q011 q016 q021 q026 q036 q040 q045 q050 q055 q060 `
    q061 q066 q071 q076 q081 q086 q091 q096 q101 q106 q111 q115 `
  --out-dir artifacts/runs/a3_verify_generation24

uv run python tools/run_config.py --config configs/a3_verify_suff.yaml `
  --limit 0 --no-generate --out-dir artifacts/runs/a3_sufficiency_all
```

Model NLI diunduh otomatis pada pemakaian pertama
(`cross-encoder/nli-deberta-v3-base`). Hasil di laporan ini dirakit dari tiga
run terpisah (lihat Artefak); perintah kedua menjalankan ulang 24 query dalam
satu direktori.

## Batasan

- Kalibrasi memakai train-65 (`benchmark/queries_train.jsonl`); test final
  memakai `benchmark/queries_test.jsonl` (50). Angka di atas adalah sample,
  bukan test final.
- Sample generation hanya 24 query; jangan klaim cakupan 115 query.
- Jawaban yang diverifikasi berasal dari B3 (tanpa planner). E1/E3 masih
  menyebabkan false refusal; `q071` membuktikan verifier tidak bisa
  memperbaiki kesalahan entitas.
- `keep_refuted=false`: klaim REFUTED dibuang. Untuk use case fact-checking,
  ini bisa menjadi false refusal; perlu keputusan desain di B4.
- Repair JSON tidak selalu berhasil (`q037`, `q060`); hasilnya abstain
  `format_error`, bukan jawaban salah.

## Artefak

- `artifacts/runs/a3_verify_sample14_v2/` - 13 query audit + `q037`.
- `artifacts/runs/a3_verify_generation_rest/` - 9 query audit sisanya.
- `artifacts/runs/a3_verify_check2/` - hasil final `q006` dan `q071`.
- `artifacts/runs/a3_sufficiency_all/` - proxy sufficiency 115 query.
- `artifacts/runs/a3_verify_noevidence/` - 6 no-evidence dengan sufficiency on.
- `artifacts/runs/a3_verify_suff_check/` - `q021` + `q091` dengan sufficiency on.
- `artifacts/runs/error_taxonomy_recheck.csv` - 140 baris retrieval, identik.
- `artifacts/runs/error_taxonomy_recheck_summary.json` - ringkasan gabungan.

## Verifikasi

```powershell
uv run pytest -q
uv run ruff check src tests tools
uv run python tools/validate_benchmark.py --strict
```

- `pytest`: **161 test lulus**.
- `ruff`: bersih.
- `validate_benchmark.py --strict`: benchmark v2 valid.

## Langkah berikutnya (Week 3)

1. Kalibrasi threshold NLI dan τ di train-65 (`benchmark/queries_train.jsonl`).
2. Jalankan A3 verifier on/off di train-65 (pengembangan) dan test-50 setelah
   config freeze dengan `eval` yang sama; laporkan unsupported claim rate,
   abstain recall, false refusal.
3. Jangan aktifkan sufficiency sebelum false refusal terukur di train-65.
4. Planner/retrieval untuk E1 dan entity swap (`q071`).
5. Perluas audit generation dan rerun error taxonomy setelah B4.
