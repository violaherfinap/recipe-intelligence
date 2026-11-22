# Handoff W2-C - qrels v2 pass 1 dan A1

- **Owner:** C
- **Branch:** `feat/w2-c-qrels-v2-a1`
- **Base:** `ee8f270` (`feat/w2-b-eval-pool`)
- **Tanggal:** 2026-11-22
- **Status:** qrels v2 pass 1 selesai; A1 selesai untuk qrels v1.1; audit verdict C pending
- **Handoff ke:** D

## Ringkasan

C menyelesaikan anotasi 448 kandidat baru pool v2 dengan alur
**LLM preannotation + review manusia 100%**, membentuk `qrels_v2_c.jsonl`
2.237 baris, lalu menjalankan A1 pada tiga index. Tidak ada label C yang boleh
dibuka D sebelum pass 2 selesai.

## Angka kunci

| Item | Nilai |
| --- | ---: |
| Seed qrels v1.1 | 1.789 baris |
| Kandidat baru pool v2 | 448 baris / 113 query |
| Hasil review C | 448/448 |
| Override saat review | 5 |
| `qrels_v2_c.jsonl` | 2.237 baris / 115 query |
| Query tanpa kandidat baru | 2 |
| SHA-256 `qrels_v2_c.jsonl` | `6523382a21df5b2bed9cdea7d7c7bcd6c169d2102461af7d876e759e08700f3e` |
| A1 fixed doc recall@10 | 0,3889 |
| A1 section doc recall@10 | 0,3500 |
| A1 hierarchical doc recall@10 | 0,5778 |
| A1 section passage R@10 | 0,3019 |
| Unit test | 130 lulus |
| Ruff | bersih |

## Artefak

| Artefak | Path | Status |
| --- | --- | --- |
| Qrels v2 C final | `benchmark/qrels_v2_c.jsonl` | commit; jangan dibuka D sebelum pass 2 |
| Qrels v2 C hash | `benchmark/qrels_v2_c.sha256` | commit |
| Qrels v2 C reviewed | `benchmark/work/w2-c/qrels_v2_c_reviewed.jsonl` | lokal, gitignored |
| Qrels v2 C draft | `benchmark/work/w2-c/qrels_v2_c_ai_draft.jsonl` | lokal, gitignored |
| Jawaban LLM | `benchmark/work/w2-c/answers_001.txt`-`answers_012.txt` | lokal, gitignored |
| Seed snapshot | `benchmark/work/w2-c/qrels_v2_c_seed.jsonl` | lokal, gitignored |
| Laporan A1 | `reports/a1_dev.md` | commit |
| Config A1 | `configs/a1_fixed.yaml`, `a1_section.yaml`, `a1_hierarchical.yaml` | commit |
| Tool context A1 | `tools/a1_context_stats.py` | commit |
| Run A1 | `artifacts/runs/a1_*_full.json` | lokal, gitignored |
| Pool v2 | `benchmark/pool_v2.jsonl` + `pool_v2.sha256` | commit |
| Provenance pool | `benchmark/pool_v2_meta.jsonl` | jangan dibuka anotator |

## Diskusi dan keputusan

- **AI-assisted, bukan manual.** 448 label disusun LLM sebagai preannotation,
  lalu direview manusia 100%; 5 label di-override. Tulis sebagai
  **AI-assisted draft + 100% human review**.
- **q048 warning diterima sebagai known limitation.** Pool v2 hanya punya satu
  dokumen gold untuk q048, sehingga tiga passage relevance-2 berasal dari
  dokumen yang sama. Ini gap pool lama, bukan konflik label baru. Jangan
  backfill tanpa persetujuan B/C.
- **A1 memakai qrels v1.1.** Passage recall fixed/hierarchical tidak valid
  karena qrels hanya punya passage ID section; hasil passage fixed/hierarchical
  yang 0 bersifat struktural. Doc recall adalah metrik utama.
- **A1 memakai dense-only.** BM25, reranker, dan filter dimatikan agar efek
  chunking terisolasi. Section A1 mereproduksi dense A2 (passage R@10 0,3019;
  doc recall 0,3500).
- **Q12 belum diputuskan.** Default sementara 2 anotator (C+D), tetapi catatan
  v1.1 menyarankan 3 (A+C+D). Putuskan sebelum D memulai pass 2.

## Instruksi untuk D

### Sebelum mulai

1. Putuskan Q12: 2 anotator (C+D) atau 3 anotator (A+C+D).
2. Jangan membuka `qrels_v2_c.jsonl`, `qrels_v2_c_reviewed.jsonl`,
   `qrels_v2_c_ai_draft.jsonl`, `answers_*.txt`, atau
   `benchmark/work/w2-c/` sampai pass 2 selesai.
3. Gunakan seed `benchmark/qrels.jsonl` v1.1, bukan qrels C.

### Pass 2

```powershell
Copy-Item benchmark/qrels.jsonl benchmark/qrels_v2_d.jsonl

uv run python tools/annotate.py relevance --annotator D `
  --queries benchmark/queries.jsonl `
  --pool benchmark/pool_v2.jsonl `
  --passages data/processed/passages.jsonl data/processed/passages_fixed.jsonl `
  --out benchmark/qrels_v2_d.jsonl
```

- Nilai hanya 448 kandidat baru; seed v1.1 dilewati.
- Jangan membuka `benchmark/pool_v2_meta.jsonl`.
- Setelah pass 2, bandingkan C vs D pada 448 key, hitung agreement, adjudikasi
  konflik, lalu tulis qrels v2 final ke `benchmark/qrels.jsonl` (backup v1.1
  dulu).
- Regenerate `benchmark/manifest.sha256`.

### Setelah qrels v2 freeze

1. Jalankan ulang A1 dengan qrels v2:

```powershell
uv run python tools/eval_retrieval.py --config configs/a1_fixed.yaml --limit 0 --out artifacts/runs/a1_fixed_v2.json
uv run python tools/eval_retrieval.py --config configs/a1_section.yaml --limit 0 --out artifacts/runs/a1_section_v2.json
uv run python tools/eval_retrieval.py --config configs/a1_hierarchical.yaml --limit 0 --out artifacts/runs/a1_hierarchical_v2.json
uv run python tools/a1_context_stats.py --runs artifacts/runs --out artifacts/runs/a1_context_stats_v2.json
```

2. Jalankan ulang B2/B3 dan tutup Gate 2:

```powershell
uv run python tools/eval_retrieval.py --config configs/b2.yaml --limit 0 --retain-k 10 --out artifacts/runs/retrieval_b2_v2.json
uv run python tools/eval_retrieval.py --config configs/b3.yaml --limit 0 --out artifacts/runs/retrieval_b3_v2.json
```

3. Update `reports/a1_dev.md`, `reports/b2b3_dev.md`, dan verdict Gate 2.
4. Audit verdict C (145 klaim) masih pending; lihat `docs/handoff/w1-c.md`.

## A1 - hasil singkat

| Mode | Passage | Dense `index` | Doc R@10 | Context mean | >2.000 token |
| --- | ---: | ---: | ---: | ---: | ---: |
| fixed | 5.738 | 8,81 MB | 0,3889 | 1.822 | 38/115 |
| section | 11.266 | 17,30 MB | 0,3500 | 722 | 4/115 |
| hierarchical | 37.754 | 57,99 MB | **0,5778** | **278** | 0/115 |

Detail, per-slice, dan batasan ada di `reports/a1_dev.md`.

## Verifikasi

```powershell
uv run pytest -q
uv run ruff check src tests tools
uv run python tools/validate_benchmark.py --strict
uv run python tools/audit_qrels.py compare
```

- `pytest`: **130 test lulus**.
- `ruff`: bersih.
- `validate_benchmark.py --strict`: benchmark v1.1 valid.
- `audit_qrels.py compare`: 181 confirm, 2 change, 0 mismatch.
- `qrels_v2_c.jsonl`: 2.237 baris, 115 query, 448 `annotator: C`, 1.789
  `annotator: D`, tanpa duplikat key.

## Catatan terbuka

| ID | Isu | Dampak |
| --- | --- | --- |
| Q10 | Tidak ada dev query set terpisah | A1/A2 memakai 115 query test sebagai evaluation; bukan tuning |
| Q11 | Passage fixed belum lengkap di qrels v1.1 | A1 fixed/hier passage recall belum valid; tunggu qrels v2 |
| Q12 | 2 atau 3 anotator untuk qrels v2? | Putuskan sebelum D pass 2 |
| q048 | Multi-hop hanya punya satu dokumen gold | Warning finalize diterima; backfill butuh persetujuan B/C |
| Audit | Verdict C 145 klaim berasal dari batch AI | Provenance harus ditulis jujur; audit pending |
