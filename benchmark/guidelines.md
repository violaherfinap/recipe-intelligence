# Benchmark & Annotation Guidelines — v1

**Proyek:** Historical Recipe Evidence QA
**Use case:** C (temporal fact-checking) pada korpus `ye-old-american`
**Versi:** 1.0 — 2026-11-14
**Pemilik:** B (penulis query)
**Anotator:** C (pass 1) dan D (pass 2)
**Corpus commit:** `ae3bd2c009a8899dfe63b9166fa98ae3fa8041a8`

Dokumen ini adalah aturan resmi untuk:

1. menulis dan membekukan 115 query benchmark;
2. membangun pool kandidat passage;
3. menilai relevansi passage (0/1/2);
4. memberi verdict klaim (SUPPORTED/REFUTED/NOT_ENOUGH_EVIDENCE);
5. mencatat konflik dan adjudikasi.

Semua angka dan label harus bisa dilacak ke file di `benchmark/`.

---

## 1. Peran dan batas

| Peran | Boleh | Tidak boleh |
| --- | --- | --- |
| B | Menulis query, gold claim, gold candidate; membangun tool; memverifikasi no-evidence | Menilai qrels, mengubah query setelah freeze |
| C | Anotasi relevance pass 1; verdict pass 1; metrik | Melihat label D; menilai query miliknya sendiri |
| D | Anotasi relevance pass 2; verdict pass 2; κ; adjudikasi; freeze | Melihat label C sebelum pass 2 selesai |
| A | Menyediakan korpus/index; audit teknis | Menulis query/qrels |

B adalah satu-satunya penulis query, sehingga C dan D dapat menjadi dua anotator blind.

---

## 2. Artefak benchmark

| File | Isi | Pemilik |
| --- | --- | --- |
| `benchmark/queries.jsonl` | 115 query + gold claim | B (frozen) |
| `benchmark/gold_candidates.jsonl` | Passage gold dari penulis query | B |
| `benchmark/pool_v1.jsonl` | Kandidat blinded untuk anotasi | C (dibangun dengan tool) |
| `benchmark/pool_v1_meta.jsonl` | Provenance kandidat; **jangan dibuka anotator** | B/C (audit) |
| `benchmark/qrels_c.jsonl` | Relevance pass 1 | C |
| `benchmark/qrels_d.jsonl` | Relevance pass 2 | D |
| `benchmark/verdict_qrels_c.jsonl` | Verdict pass 1 | C |
| `benchmark/verdict_qrels_d.jsonl` | Verdict pass 2 | D |
| `benchmark/no_evidence_check.csv` | Bukti negatif 25 query | B |
| `benchmark/queries.sha256` | Hash query beku | B |
| `benchmark/manifest.sha256` | Hash query + qrels + daftar doc test | D |

**Aturan keras:** `benchmark/` tidak boleh diakses oleh pipeline agent/training. Jangan menyalin passage test ke `prompts/` atau dataset LoRA.

---

## 3. Komposisi benchmark

| Slice | Jumlah | ID | Ciri |
| --- | ---: | --- | --- |
| `easy` | 35 | q001–q035 | Jawaban ada di satu passage; satu klaim atomik |
| `multi-hop` | 25 | q036–q060 | Butuh ≥2 passage dan ≥2 dokumen; biasanya "which two" |
| `temporal` | 30 | q061–q090 | Membandingkan ≥2 buku/tahun; `as_of` wajib |
| `no-evidence` | 25 | q091–q115 | Jawaban tidak ada di seluruh korpus |

Setiap query answerable (90 query) punya minimal satu gold passage. Semua gold passage harus `split=test`.

---

## 4. Skema query

```json
{
  "query_id": "q001",
  "text": "How long is the 1796 cheap seed cake baked?",
  "slice": "easy",
  "scope": "year:1796",
  "as_of": 1796,
  "filter": {
    "year_min": 1796,
    "year_max": 1796,
    "book": "American Cookery",
    "section": null
  },
  "gold_claims": [
    "The 1796 cheap seed cake is baked for one and a half hours."
  ],
  "notes": "American Cookery 1796",
  "author": "B"
}
```

Aturan field:

- `query_id`: `qNNN`, unik, berurutan q001–q115.
- `slice`: salah satu dari empat nilai di atas.
- `scope`: untuk manusia, mis. `year:1896`, `years:1851,1896`.
- `as_of`: tahun batas bukti; wajib untuk `temporal`; `null` jika tidak relevan.
- `filter`: untuk mesin; `year_min`/`year_max`/`book`/`section`. Harus konsisten dengan `scope`.
- `gold_claims`: klaim atomik; bukan paragraf. Query `no-evidence` wajib `[]`.
- `notes`: catatan untuk evaluator; **tidak boleh** dipakai sebagai konteks model.
- `author`: `"B"`.

**Gold candidates** disimpan terpisah:

```json
{
  "query_id": "q001",
  "passage_ids": ["ye-old-american:a-cheap-seed-cake#directions#0"],
  "doc_ids": ["ye-old-american:a-cheap-seed-cake"],
  "source": "author"
}
```

File ini hanya untuk pooling dan validasi. Jangan membukanya saat menilai.

---

## 5. Aturan penulisan query (untuk B)

1. Bahasa Inggris.
2. Jawaban tidak boleh muncul di teks query.
   - Konstrain boleh muncul: tahun, buku, nama bahan, nama masakan.
   - Nilai jawaban tidak boleh muncul: waktu, kuantitas, nama resep yang ditanyakan.
3. Jangan menyalin lebih dari 8 kata berurutan dari passage.
4. Jangan menyebut `passage_id`, `doc_id`, `split`, atau istilah sistem.
5. Satu query harus punya jawaban yang determinate dalam scope-nya.
6. Untuk `easy` dan `multi-hop`, sebut tahun atau buku kecuali jawaban sudah diverifikasi unik di seluruh korpus.
7. Jangan bertanya tentang author/source_url/tahun sebagai fakta; itu metadata, bukan isi passage.
8. `multi-hop` wajib punya ≥2 `doc_id` berbeda dan ≥2 klaim.
9. `temporal` wajib menyebut tahun/buku dan punya ≥2 buku berbeda.
10. `no-evidence` wajib diverifikasi ke seluruh 5.605 dokumen dan punya baris di `no_evidence_check.csv`.

Contoh bentuk yang benar:

```text
How long is the 1796 cheap seed cake baked?
Which two 1896 recipes use both butter and mace?
Did the 1851 and 1871 baked apple recipes both instruct the cook to peel the apples?
What internal temperature does the 1896 book require for roast chicken?
```

Contoh yang salah:

```text
Is the 1796 cheap seed cake baked for one and a half hours?   # jawaban ada di query
Which recipe is ye-old-american:a-cheap-seed-cake?            # memakai doc_id
How long is tomato soup cooked?                               # scope tidak determinate
```

---

## 6. Skala relevance 0/1/2

Nilailah **passage**, bukan dokumen, terhadap **query**.

| Label | Arti | Contoh |
| ---: | --- | --- |
| `2` | Passage langsung menjawab atau menyelesaikan klaim query | Query menanyakan lama memanggang; passage menyebut "bake forty to forty-five minutes" |
| `1` | Relevan parsial: memberi konteks, bahan terkait, atau satu bagian jawaban | Passage hanya menyebut bahan tanpa waktu |
| `0` | Tidak relevan, atau hanya berbagi kata umum | Query tentang seed cake; passage tentang roast beef |

Aturan tambahan:

- Bukti yang **bertentangan** tetap bisa `2` jika query meminta perbandingan/verifikasi.
- Jika passage hanya mengulang query tanpa menjawab, beri `1`, bukan `2`.
- Jika ragu antara `0` dan `1`, pilih `0`; jika ragu antara `1` dan `2`, pilih `1`.
- Jangan memberi `2` hanya karena tahun/buku cocok.
- Jangan memakai pengetahuan luar korpus.

Contoh (ilustratif, bukan passage test):

```text
Query: How long is the bread baked?
Passage: "Bake in a moderate oven forty minutes."        -> 2
Passage: "Mix flour, milk, and salt into a dough."       -> 1
Passage: "Roast the beef for an hour."                   -> 0
```

---

## 7. Pooling

Pool v1 dibangun oleh C dengan:

```powershell
uv run python tools/build_pool.py `
  --queries benchmark/queries.jsonl `
  --gold benchmark/gold_candidates.jsonl `
  --passages data/processed/passages.jsonl `
  --dense-dir indexes `
  --out benchmark/pool_v1.jsonl `
  --meta benchmark/pool_v1_meta.jsonl `
  --split test --dense-k 10 --negatives 5 --seed 42
```

Isi pool per query:

- semua gold passage (dari penulis query),
- dense top-10 (BGE, hanya `split=test`),
- 5 negatif acak dari passage test.

Aturan:

- Kandidat di-dedup per query.
- `pool_v1.jsonl` hanya berisi `query_id`, `passage_id`, `doc_id`; tidak ada skor/sumber.
- `pool_v1_meta.jsonl` menyimpan `source`/`rank`/`score`; **jangan dibuka saat anotasi**.
- Unjudged = non-relevan (0). Semua kandidat pool harus dinilai.
- Jangan menambah kandidat dari luar pool saat anotasi; jika menemukan passage relevan yang tidak ada di pool, catat di `notes` dan laporkan ke D.

---

## 8. Blinding

- C tidak boleh melihat `qrels_d.jsonl`, `verdict_qrels_d.jsonl`, atau `pool_v1_meta.jsonl`.
- D tidak boleh melihat `qrels_c.jsonl`, `verdict_qrels_c.jsonl`, atau catatan C sampai pass 2 selesai.
- Tool tidak menampilkan `source`, `rank`, `score`, gold claim, atau label anotator lain.
- Urutan kandidat diacak deterministik per `(query_id, annotator)`.
- Jangan berdiskusi tentang label sebelum adjudikasi.
- Anotator tidak boleh menilai query yang ia tulis sendiri; tool menolak berdasarkan `author`.

---

## 9. Prosedur anotasi relevance

C (pass 1):

```powershell
uv run python tools/annotate.py relevance `
  --annotator C `
  --queries benchmark/queries.jsonl `
  --pool benchmark/pool_v1.jsonl `
  --passages data/processed/passages.jsonl `
  --out benchmark/qrels_c.jsonl
```

D (pass 2, blind):

```powershell
uv run python tools/annotate.py relevance `
  --annotator D `
  --queries benchmark/queries.jsonl `
  --pool benchmark/pool_v1.jsonl `
  --passages data/processed/passages.jsonl `
  --out benchmark/qrels_d.jsonl
```

Kontrol:

- `0/1/2` = nilai relevance.
- `n` = tambah catatan untuk kandidat berikutnya.
- `s` = lewati kandidat (bisa kembali lain waktu).
- `q` = keluar; progres tersimpan.
- Setiap penilaian langsung ditulis append-only; aman jika crash.

Cek progres:

```powershell
uv run python tools/annotate.py status --annotator C --out benchmark/qrels_c.jsonl
```

Target: semua kandidat di pool dinilai. C/D tidak boleh mengubah `queries.jsonl`.

---

## 10. Verdict klaim

Setelah relevance selesai, C dan D menilai klaim gold:

```powershell
uv run python tools/annotate.py verdict `
  --annotator C `
  --queries benchmark/queries.jsonl `
  --qrels benchmark/qrels_c.jsonl `
  --passages data/processed/passages.jsonl `
  --out benchmark/verdict_qrels_c.jsonl
```

Skala:

| Verdict | Arti | Syarat |
| --- | --- | --- |
| `SUPPORTED` | Passage mendukung klaim | Ada minimal satu passage relevansi 2 yang mengimplikasikan klaim |
| `REFUTED` | Passage menolak klaim | Ada bukti yang secara eksplisit bertentangan |
| `NOT_ENOUGH_EVIDENCE` | Bukti tidak cukup | Tidak ada passage yang mendukung atau menolak |

Aturan:

- Jangan memakai label qrels relevance sebagai verdict otomatis; baca passage.
- Satu klaim = satu verdict.
- Jika klaim punya dua bagian, nilai bagian yang paling material; catat di `notes`.
- Untuk klaim komparatif ("both use mace"), nilai klaim sebagai satu proposisi; jika salah satu sisi tidak memakai mace, verdict `REFUTED`.

---

## 11. No-evidence

Query `no-evidence` tidak punya gold claim dan tidak punya gold passage. Verifikasi B:

1. Pecah query menjadi key terms + sinonim/ejaan lama.
2. Cari di `docs.jsonl` (5.605 dokumen, termasuk 5 dokumen yang tidak diindeks) dengan regex.
3. Cari di `passages.jsonl` untuk konteks.
4. Jalankan BM25 top-20; baca hit yang berpotensi menjawab.
5. Catat di `benchmark/no_evidence_check.csv`:
   `query_id, text, key_terms, book_scope, bm25_top20, terms_searched, docs_reviewed, evidence_found, decision, rationale, verified_by, verified_at`.
6. Jika ada satu bukti yang menjawab: ganti query (ID tetap), ulangi verifikasi, catat `decision=replace`.

Kriteria final:

- 25/25 baris `decision=absent`.
- `evidence_found=no`.
- Setiap baris punya minimal 2 istilah pencarian dan alasan.
- Spot-check 5 query oleh C/D setelah handoff.

Contoh aman: pertanyaan tentang kalori, vitamin, sodium, gram, thermometer daging, microwave, blender, food processor, gas oven, aluminium foil, plastic wrap, slow cooker, gluten, pasteurized, USDA/FDA, danger zone, smoke point, sous vide, air fryer, dehydrator, salmonella.

Jangan memakai pertanyaan yang jawabannya bisa diinferensikan dari instruksi resep atau dari buku lain dalam korpus.

---

## 12. Temporal/conflict

- `as_of` = tahun terbaru yang dibandingkan.
- Filter `year_min`/`year_max` mencakup kedua buku.
- Minimal 2 passage dari 2 buku berbeda.
- `notes` menyebut atribut yang dibandingkan; bukan jawaban.
- Konflik harus nyata: baca kedua passage. Jika hanya beda istilah kecil, ubah menjadi `change` atau ganti topik.
- Jangan mengarang konflik. Jika kedua buku setuju, query tetap valid sebagai `agreement`, tetapi jangan menulis "berbeda" jika tidak.

---

## 13. Adjudikasi

D menghitung:

- Cohen's κ untuk relevance (C vs D).
- Cohen's κ untuk verdict (C vs D).
- Disagreement log: query, passage/claim, label C, label D, alasan, keputusan.
- Adjudikasi oleh D (atau A jika D terlibat konflik):
  - pilih label yang didukung passage;
  - catat alasan;
  - tulis qrels final `benchmark/qrels.jsonl`.

Aturan adjudikasi:

- Jangan memilih "tengah" hanya untuk mencapai agreement.
- Jika passage ambigu, pilih label yang lebih konservatif (0/1, atau NEI).
- Semua konflik harus punya catatan.

---

## 14. Freeze

B membuat:

```powershell
$h = (Get-FileHash benchmark/queries.jsonl -Algorithm SHA256).Hash.ToLower()
"$h  queries.jsonl" | Set-Content benchmark/queries.sha256
```

Setelah freeze:

- Jangan mengubah `queries.jsonl`.
- Jika ada perbaikan darurat, catat di `docs/open_questions.md`, buat hash baru, dan beri tahu C/D.
- D membuat `benchmark/manifest.sha256` yang memuat hash query, qrels final, dan daftar `doc_id` test.

---

## 15. Perintah ringkas

```powershell
# validasi benchmark
uv run python tools/validate_benchmark.py --strict

# bangun pool (C)
uv run python tools/build_pool.py

# anotasi relevance (C/D)
uv run python tools/annotate.py relevance --annotator C --out benchmark/qrels_c.jsonl

# anotasi verdict (C/D)
uv run python tools/annotate.py verdict --annotator C `
  --qrels benchmark/qrels_c.jsonl --out benchmark/verdict_qrels_c.jsonl

# progres
uv run python tools/annotate.py status --annotator C --out benchmark/qrels_c.jsonl

# test
uv run pytest -q
uv run ruff check src tests tools
```

---

## 16. Versi dan perubahan

| Versi | Tanggal | Perubahan |
| --- | --- | --- |
| 1.0 | 2026-11-14 | Versi awal: 115 query, aturan 0/1/2, pooling, verdict, no-evidence, adjudikasi |

Perubahan aturan harus disetujui B + C + D dan dicatat di tabel ini.
