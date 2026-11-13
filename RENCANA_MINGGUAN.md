# RENCANA MINGGUAN — EKSEKUSI SEQUENTIAL 4 ORANG

**Dokumen acuan:** `RENCANA_LENGKAP.md` **Periode:** 16 November – 13 Desember 2026 (4 minggu) **Tim:** Orang A, Orang B, Orang C, Orang D

---

## 0\. Aturan eksekusi

1. **Sequential per blok.** Dalam satu minggu: Orang A menyelesaikan **seluruh** tugasnya lebih dulu, lalu handoff ke B. B menyelesaikan seluruh tugasnya, handoff ke C. C selesai, handoff ke D. D menutup minggu.  
2. **Tidak ada lompat-lompat.** B tidak mulai sebelum A selesai dan handoff diterima. C tidak mulai sebelum B selesai. D tidak mulai sebelum C selesai.  
3. **Satu blok \= satu orang.** Tidak ada dua orang bekerja bersamaan dalam satu minggu.  
4. **Handoff wajib.** Setiap blok menghasilkan artefak di path yang ditentukan \+ catatan 3 baris di `docs/handoff_log.md` (selesai apa, belum apa, langkah berikutnya).  
5. **Definition of Ready.** Sebelum mulai, input dari blok sebelumnya harus ada dan bisa dibuka.  
6. **Definition of Done.** Output ada, test/lint lulus, acceptance criteria terpenuhi.  
7. **Blocker.** Jika tertahan \> 2 jam, pemilik melapor; keputusan dicatat di `docs/open_questions.md`.  
8. **Percepatan.** Kalau satu blok selesai lebih cepat, blok berikutnya boleh mulai lebih awal. Urutan tetap A → B → C → D.

Beban default: A ±2 hari, B ±2 hari, C ±1,5 hari, D ±2 hari (total ±7–8 hari per minggu).

---

## 1\. Minggu 1 — Fondasi data, benchmark, qrels (16–22 Nov)

**Tujuan:** korpus \+ index siap; 115 query; qrels v1 final; alat ukur dasar siap. **Gate 1:** 5.605 dokumen terindeks; 115 query frozen; qrels v1 ≥95% lengkap; κ dilaporkan; hash test frozen.

| Blok | Owner | Jam | Output utama | Handoff ke |
| :---- | :---- | :---- | :---- | :---- |
| 1 | A | 14 | corpus, passages, split, index | B |
| 2 | B | 14 | guideline, tool anotasi, 115 query | C |
| 3 | C | 10 | anotasi pass 1, metrics library | D |
| 4 | D | 12 | anotasi pass 2, κ, qrels v1 final | A (minggu 2\) |

### Blok 1 — Orang A (hari 1–2): fondasi data

| No | Tugas | Jam | Output | Acceptance |
| :---- | :---- | :---- | :---- | :---- |
| 1 | Clone repo, pin commit, inventarisasi 5.605 resep | 1 | `data/raw/`, `data/corpus_commit.txt` | commit SHA tercatat |
| 2 | Tulis ADR-001 (korpus) \+ ADR-002 (pemetaan use case) | 1 | `docs/adr/` | dua ADR lengkap |
| 3 | Parser JSONL → `docs.jsonl` \+ validasi \+ hash | 3 | `data/processed/docs.jsonl` | 5.605 baris; field wajib lengkap |
| 4 | Passage builder \+ `source_register.csv` \+ `manifest.json` | 2 | `passages.jsonl`, `source_register.csv` | 15k–20k passage; ID unik |
| 5 | Dedup dalam buku \+ split 70/15/15 \+ freeze hash | 2 | `split.json`, `manifest.sha256` | tidak ada doc di 2 split; semua tahun ada |
| 6 | Index BM25 \+ smoke retrieval | 2 | `indexes/bm25/` | 10 query mengembalikan hasil |
| 7 | Embedding \+ index dense \+ index manifest | 2 | `indexes/dense.npy` | \~17k vektor; dot product jalan |
| 8 | Handoff \+ catatan | 1 | `docs/handoff_log.md` | 3 baris \+ path artefak |

**Handoff ke B:** corpus \+ index siap dipakai; B membaca `passages.jsonl`, `source_register.csv`, `split.json`.

### Blok 2 — Orang B (hari 3–4): benchmark

| No | Tugas | Jam | Output | Acceptance |
| :---- | :---- | :---- | :---- | :---- |
| 1 | Annotation guideline \+ skema query | 2 | `benchmark/guidelines.md` | aturan 0/1/2, pooling, no-evidence jelas |
| 2 | Tool anotasi \+ blinding \+ larangan menilai query sendiri | 2 | `tools/annotate.py` | anotator tidak melihat label lain |
| 3 | Tulis 35 query easy | 3 | `queries.jsonl` (35) | jawaban tidak ada di teks query |
| 4 | Tulis 25 query multi-hop | 2,5 | `queries.jsonl` (60) | butuh ≥2 passage |
| 5 | Tulis 30 query temporal/conflict | 2,5 | `queries.jsonl` (90) | menyebut tahun/buku; konflik nyata |
| 6 | Tulis 25 query no-evidence \+ verifikasi seluruh korpus | 2 | `queries.jsonl` (115), `no_evidence_check.csv` | 25/25 terbukti tidak ada bukti |

**Catatan:** B adalah satu-satunya penulis query, sehingga C dan D (bukan penulis) bisa menjadi dua anotator blind.

**Handoff ke C:** 115 query frozen; tool siap; B tidak lagi mengubah query.

### Blok 3 — Orang C (hari 5–6): anotasi pass 1 \+ alat ukur

| No | Tugas | Jam | Output | Acceptance |
| :---- | :---- | :---- | :---- | :---- |
| 1 | Anotasi qrels pass 1 (gold \+ dense top-10 pool) | 7 | `qrels_c.jsonl` | semua query answerable punya ≥1 level 2 |
| 2 | Metrics library: retrieval \+ claims | 2 | `src/recipe_qa/eval/metrics/*.py` | unit test lulus |
| 3 | Handoff \+ catatan | 1 | `docs/handoff_log.md` | label C tidak terlihat oleh D |

**Handoff ke D:** label pass 1 tersimpan; tool menyembunyikan label C dari D.

### Blok 4 — Orang D (hari 7): anotasi pass 2, adjudication, freeze

| No | Tugas | Jam | Output | Acceptance |
| :---- | :---- | :---- | :---- | :---- |
| 1 | Anotasi qrels pass 2 (blind) | 7 | `qrels_d.jsonl` | tidak melihat label C |
| 2 | Hitung κ relevance \+ verdict | 1 | `kappa.json` | κ dilaporkan |
| 3 | Adjudication \+ disagreement log | 2 | `annotation_log.csv`, `qrels.jsonl` v1 | semua konflik diputuskan |
| 4 | Freeze qrels v1 \+ test manifest | 1 | `benchmark/manifest.sha256` | hash query \+ qrels \+ doc test |
| 5 | Handoff \+ gate report | 1 | `reports/week1.md` | gate 1 terpenuhi |

**Gate 1:** korpus \+ index \+ 115 query \+ qrels v1 \+ κ \+ hash frozen.

---

## 2\. Minggu 2 — Retrieval, A1, A2 (23–29 Nov)

**Tujuan:** B2/B3 \+ A1/A2 selesai di dev; qrels v2 final; config B0/B1 siap. **Gate 2:** qrels v2 frozen; Recall@10 B3 \> B2 di dev; config equality B0–B3 lulus.

| Blok | Owner | Jam | Output utama | Handoff ke |
| :---- | :---- | :---- | :---- | :---- |
| 1 | A | 14 | B2, B3, A1/A2 varian, config | B |
| 2 | B | 13 | smoke B0/B1, eval B2/B3/A2, pool v2 | C |
| 3 | C | 10 | anotasi pool v2 pass 1, eval A1 | D |
| 4 | D | 13 | anotasi pool v2 pass 2, qrels v2, error taxonomy | A (minggu 3\) |

### Blok 1 — Orang A: implementasi retrieval

| No | Tugas | Jam | Output | Acceptance |
| :---- | :---- | :---- | :---- | :---- |
| 1 | Pipeline B2 (dense \+ fixed chunk \+ top-5) | 3 | `pipeline/b2.py`, `configs/b2.yaml` | end-to-end jalan |
| 2 | B3: BM25 \+ RRF \+ reranker \+ filter | 4 | `retrieval/fusion.py`, `rerank.py`, `pipeline/b3.py` | RRF k=60; 50 → 10 |
| 3 | A1 varian: fixed / section / hierarchical | 3 | `index/build.py` mode chunking | 3 index terbentuk |
| 4 | A2 varian: dense / bm25 / hybrid / hybrid+rerank | 2 | `configs/retrieval_*.yaml` | 4 konfigurasi |
| 5 | Prompt registry B0/B1 \+ config | 1 | `prompts/registry/`, `configs/b0.yaml`, `b1.yaml` | config equality lulus |
| 6 | Handoff | 1 | `docs/handoff_log.md` | artefak siap |

### Blok 2 — Orang B: eksekusi dan pool

| No | Tugas | Jam | Output | Acceptance |
| :---- | :---- | :---- | :---- | :---- |
| 1 | Smoke B0/B1 di dev | 2 | `artifacts/runs/smoke/` | 20 query; schema validity dilaporkan |
| 2 | Jalankan B2/B3 di dev \+ metrik retrieval | 3 | `reports/b2b3_dev.md` | Recall@5/10, nDCG, MRR |
| 3 | A2 eval (4 varian, qrels sama) | 3 | `reports/a2_dev.md` | tabel lengkap |
| 4 | Pool refresh: top-10 B2 \+ top-10 B3 | 3 | `pool_v2.jsonl` | \~20 kandidat unik/query |
| 5 | Config equality test B0–B3 | 2 | `tests/test_config_equality.py` | lulus |

**Handoff ke C:** pool v2 siap dianotasi; B2/B3 dev numbers tercatat.

### Blok 3 — Orang C: anotasi pool \+ A1

| No | Tugas | Jam | Output | Acceptance |
| :---- | :---- | :---- | :---- | :---- |
| 1 | Anotasi kandidat baru pool v2 (pass 1\) | 6 | `qrels_v2_c.jsonl` | semua kandidat dinilai |
| 2 | A1 eval (3 chunking) | 3 | `reports/a1_dev.md` | passage recall, index size, context length |
| 3 | Handoff | 1 | `docs/handoff_log.md` | label C tersembunyi dari D |

### Blok 4 — Orang D: finalisasi qrels v2 \+ error taxonomy

| No | Tugas | Jam | Output | Acceptance |
| :---- | :---- | :---- | :---- | :---- |
| 1 | Anotasi pool v2 (pass 2, blind) | 6 | `qrels_v2_d.jsonl` | tidak melihat label C |
| 2 | κ \+ adjudication \+ freeze qrels v2 | 4 | `qrels.jsonl` v2, `benchmark/manifest.sha256` | konflik diputuskan; hash tercatat |
| 3 | Error taxonomy: kodekan ≥50 kegagalan dev | 3 | `docs/error_taxonomy.md`, `error_analysis.csv` | kode E1–E8 dipakai |

**Gate 2:** qrels v2 frozen; B3 \> B2 di dev; config equality lulus.

---

## 3\. Minggu 3 — B4, B5, verifier (30 Nov–6 Des)

**Tujuan:** B4 dan B5 selesai; A3/A4/A6 selesai; angka test B0–B5 tersedia. **Gate 3:** adapter terlatih; B5 dievaluasi; A3/A4/A6 punya hasil; base model tidak berubah.

| Blok | Owner | Jam | Output utama | Handoff ke |
| :---- | :---- | :---- | :---- | :---- |
| 1 | A | 14 | test B0–B3, planner, sufficiency, retry, B4 | B |
| 2 | B | 13 | verifier, citation/temporal, abstain, kalibrasi | C |
| 3 | C | 13 | dataset LoRA, training, adapter, eval B5 | D |
| 4 | D | 13 | A3/A4/A6, test B4/B5, 3 seed | A (minggu 4\) |

### Blok 1 — Orang A: B4 inti \+ test B0–B3

| No | Tugas | Jam | Output | Acceptance |
| :---- | :---- | :---- | :---- | :---- |
| 1 | Run B0–B3 di test dengan qrels v2 (seed 1\) | 3 | `artifacts/runs/b0..b3-test-s1/` | 115 query/config |
| 2 | Planner: dekomposisi \+ filter | 3 | `pipeline/planner.py` | JSON valid; fallback rule-based |
| 3 | Sufficiency score \+ kalibrasi τ di dev | 3 | `verify/sufficiency.py` | balanced accuracy dilaporkan |
| 4 | Retry terbatas (maks. 2\) | 2 | `pipeline/retry.py` | tidak melebihi budget |
| 5 | Integrasi B4 end-to-end | 2 | `pipeline/b4.py`, `configs/b4.yaml` | 20 query dev jalan |
| 6 | Handoff | 1 | `docs/handoff_log.md` | B4 siap diverifikasi |

### Blok 2 — Orang B: verifier \+ abstain

| No | Tugas | Jam | Output | Acceptance |
| :---- | :---- | :---- | :---- | :---- |
| 1 | NLI verifier | 3 | `verify/nli.py` | mapping label benar (cek config model) |
| 2 | Citation check \+ temporal check | 2 | `verify/citations.py`, `temporal.py` | sitasi/tahun terdeteksi |
| 3 | Policy abstain \+ threshold | 3 | `pipeline/abstain.py` | alasan abstain lengkap |
| 4 | Kalibrasi verifier di dev | 2 | `reports/verifier_calibration.md` | precision/recall NLI |
| 5 | Evaluasi B4 di dev | 3 | `reports/b4_dev.md` | metrik utama dilaporkan |

### Blok 3 — Orang C: LoRA

| No | Tugas | Jam | Output | Acceptance |
| :---- | :---- | :---- | :---- | :---- |
| 1 | Dataset LoRA: 600–800 contoh dari train | 4 | `train/dataset.jsonl` | tidak ada passage test; hash dicatat |
| 2 | Training LoRA CPU (overnight) \+ log | 3 | `train/adapter/`, `train/logs/` | adapter load; loss tercatat |
| 3 | Evaluasi adapter \+ OOD (buku 1824\) | 3 | `reports/b5_dev.md` | B4 vs B5 pada dev \+ OOD |
| 4 | Dokumentasi resource \+ overfit awal | 2 | `reports/b5_dev.md` | jam training, RAM, train-dev gap |
| 5 | Handoff | 1 | `docs/handoff_log.md` | adapter \+ hash |

**Catatan:** training dijalankan malam; jika gagal: turunkan r/step, ulangi sekali, dokumentasikan; jangan ganti base model.

### Blok 4 — Orang D: ablation \+ test B4/B5

| No | Tugas | Jam | Output | Acceptance |
| :---- | :---- | :---- | :---- | :---- |
| 1 | A3: verifier on/off \+ repair | 3 | `reports/a3_dev.md` | unsupported claim \+ false refusal |
| 2 | A4: gain, overfit, resource, OOD | 2 | `reports/a4_dev.md` | train-dev gap dilaporkan |
| 3 | A6: fixed vs adaptive retrieval | 3 | `reports/a6_dev.md` | per slice \+ biaya |
| 4 | Run B4/B5 di test (seed 1\) | 3 | `artifacts/runs/b4,b5-test-s1/` | 115 query/config |
| 5 | 3 seed subset B4/B5 | 2 | `artifacts/runs/*-subset/` | variance |

**Gate 3:** adapter \+ B5 eval \+ A3/A4/A6 \+ test B4/B5.

---

## 4\. Minggu 4 — B6, red-team, serving, laporan (7–13 Des)

**Tujuan:** B6 selesai; 20 red-team punya baseline vs mitigation; API/UI jalan; angka final \+ laporan. **Gate 4:** demo hidup; semua artefak ber-hash; laporan lengkap; setiap anggota bisa menjelaskan bagiannya.

| Blok | Owner | Jam | Output utama | Handoff ke |
| :---- | :---- | :---- | :---- | :---- |
| 1 | A | 13 | B6 tool \+ controller \+ auth \+ A5 | B |
| 2 | B | 12 | 20 red-team \+ A7 \+ fairness | C |
| 3 | C | 12 | API \+ UI \+ fallback \+ final run | D |
| 4 | D | 13 | 3 seed, hallucination audit, laporan, demo | selesai |

### Blok 1 — Orang A: B6

| No | Tugas | Jam | Output | Acceptance |
| :---- | :---- | :---- | :---- | :---- |
| 1 | 4 tool \+ JSON Schema | 4 | `tools/*.py` | argumen tervalidasi |
| 2 | Authorization \+ budget \+ trace | 4 | `pipeline/controller.py` | path terlarang ditolak |
| 3 | Loop agent \+ final verification | 3 | `pipeline/b6.py` | maks. 4 langkah; trace lengkap |
| 4 | A5: tool on/off | 2 | `reports/a5_dev.md` | tool correctness, unsafe call |

### Blok 2 — Orang B: red-team \+ A7 \+ fairness

| No | Tugas | Jam | Output | Acceptance |
| :---- | :---- | :---- | :---- | :---- |
| 1 | 20 fixture (5+5+5+5) \+ index terpisah | 4 | `redteam/fixtures.jsonl`, `redteam/index/` | 20 kasus, tidak masuk korpus utama |
| 2 | Harness red-team off/on | 3 | `redteam/results/` | baseline \+ mitigation |
| 3 | A7: konteks 2k vs 6k | 2 | `reports/a7_dev.md` | kualitas, p95, token |
| 4 | Audit bias/fairness | 3 | `reports/fairness_audit.md` | HHI, JS divergence, paritas |

### Blok 3 — Orang C: serving \+ final run

| No | Tugas | Jam | Output | Acceptance |
| :---- | :---- | :---- | :---- | :---- |
| 1 | API `/ask`, `/health`, `/configs` | 3 | `app/api.py` | 200 \+ schema valid |
| 2 | UI Streamlit \+ screenshot | 3 | `app/ui.py`, `docs/screenshots/` | jawaban \+ bukti \+ trace |
| 3 | Fallback \+ error handling | 2 | `app/fallback.py` | 5 skenario diuji |
| 4 | Final run semua config (seed 1\) | 4 | `artifacts/runs/final/` | 7 config × 115 query |

### Blok 4 — Orang D: reliabilitas \+ audit \+ laporan

| No | Tugas | Jam | Output | Acceptance |
| :---- | :---- | :---- | :---- | :---- |
| 1 | 3 seed subset \+ variance | 3 | `reports/variance_final.md` | mean ± std |
| 2 | Hallucination audit (120 klaim) | 3 | `reports/hallucination_audit.md` | κ \+ hallucination rate |
| 3 | Draft laporan | 4 | `docs/laporan.md` | semua bagian spek tercakup |
| 4 | Demo \+ repro README \+ contribution matrix | 3 | `README.md`, `docs/contribution_matrix.md` | demo jalan; peran tercatat |

**Gate 4:** demo \+ laporan \+ seluruh artefak.

---

## 5\. Rekap beban

| Minggu | A | B | C | D | Total |
| :---- | :---- | :---- | :---- | :---- | :---- |
| 1 | 14 | 14 | 10 | 12 | 50 |
| 2 | 14 | 13 | 10 | 13 | 50 |
| 3 | 14 | 13 | 13 | 13 | 53 |
| 4 | 13 | 12 | 12 | 13 | 50 |
| **Total** | **55** | **52** | **45** | **51** | **203** |

C paling ringan; jika perlu, C mengambil sebagian audit fairness di minggu 4\.

---

## 6\. Jika jadwal molor (urutan potong)

Potong dari bawah, jangan dari minimum spek:

1. A7 (2k vs 6k) → satu level \+ analisis biaya.  
2. A5 → dev saja, tanpa 20 item konfirmasi.  
3. A6 → 2 slice saja (easy vs conflict).  
4. B6 → 2 tool (search \+ get\_recipe), tetap dengan authorization.  
5. Audit fairness → 2 metrik (HHI \+ paritas tahun).  
6. UI → satu halaman sederhana; API tetap lengkap.

**Jangan dipotong:** 300 dokumen (kita 5.605), 100 query (kita 115), qrels answerable \+ no-evidence, 20 red-team, 3 run subset, B0–B6, plain vs LoRA, UI+API.

---

## 7\. Mode paralel (opsional, menyimpang dari permintaan)

Jika tim memutuskan paralel, gunakan lane:

| Lane | Owner | Fokus |
| :---- | :---- | :---- |
| 1 | A | corpus \+ index \+ retrieval |
| 2 | B | benchmark \+ anotasi \+ evaluasi |
| 3 | C | generation \+ verifier \+ LoRA |
| 4 | D | app \+ red-team \+ laporan |

Konsekuensi: lebih cepat, tetapi risiko konflik artefak dan handoff lebih tinggi. Urutan dependensi di tabel mingguan tetap berlaku.

---

## 8\. Checklist handoff (dipakai setiap blok)

- [ ] Artefak ada di path yang ditentukan.  
- [ ] Manifest/hash diperbarui.  
- [ ] Test/lint lulus.  
- [ ] Acceptance criteria terpenuhi.  
- [ ] Catatan 3 baris di `docs/handoff_log.md`.  
- [ ] `docs/contribution_matrix.md` diperbarui (owner \+ jam).  
- [ ] Blok berikutnya tahu input mana yang harus dibaca.