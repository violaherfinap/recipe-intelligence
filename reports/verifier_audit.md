# Audit verifier dan abstain - B4 frozen

- **Tanggal:** 2026-11-28
- **Owner:** B (Anin)
- **Config:** `configs/b4.yaml` pada tag `w3-config-frozen` (`a6b7a26`)
- **Sumber angka test-50:** `artifacts/runs/b4-test50-s1/results.jsonl`
  (`f07b2adb1699da25411b86ff6521c3a4f717242d969028259f747a084d4bf5b6`)
- **Sumber angka train-65:** `artifacts/runs/b4-train65-s1/results.jsonl`
  (`8db0f7dc3132dacceb1ee7dbdaf429e92a06e329617e60024d49cb99d28a299c`)
- **Sifat:** diagnosis. Tidak ada parameter, threshold, atau config yang dipilih
  dari angka di dokumen ini.

## Ringkasan

Empat penyebab, semuanya terlihat dari kode dan dari payload run yang sudah ada:

1. Skor sufficiency punya lantai dari komponen coverage, sehingga query dengan
   `coverage >= 0,425` tidak mungkin abstain lewat tau.
2. Klaim agregat ("both ...") dinyatakan `SUPPORTED` oleh satu passage.
3. Citation gate tidak bisa menyala pada jalur klaim normal.
4. Verifikasi menguji klaim terhadap passage, bukan klaim terhadap pertanyaan.

## T1 - Sufficiency tidak bisa abstain di atas coverage 0,425

`src/recipe_qa/verify/sufficiency.py`:

```text
score = 0.6 * sigmoid(top_score) + 0.4 * coverage
```

Karena `sigmoid(top_score) >= 0`, maka `score >= 0.4 * coverage`. Dengan tau
0,17, query dengan `coverage >= 0,425` sudah pasti lolos, **seburuk apa pun
skor retrieval-nya**. Komponen `sigmoid` hanya bisa menurunkan skor sebesar
0,6, jadi arahnya tidak pernah bisa menahan query yang tokennya banyak cocok.

Jumlah query yang berada di atas batas itu:

| Split | Query | `coverage >= 0,425` | Abstain via sufficiency |
| --- | ---: | ---: | ---: |
| train-65 | 65 | 26 | 22 |
| test-50 | 50 | 16 | 17 |

Contoh `q099` (no-evidence):

| Field | Nilai |
| --- | ---: |
| `top_score` | -9,0096 |
| `coverage` | 0,5000 |
| `score` | 0,2001 |
| tau | 0,1700 |

Skornya praktis seluruhnya dari coverage (`0,4 * 0,5 = 0,20`). Retrieval
bahkan tidak menemukan passage yang relevan, tetapi gate tetap membuka. Ini
menjelaskan kenapa hanya 17 dari 39 abstain test-50 berasal dari tau.

## T2 - Klaim agregat lolos dengan satu passage (`q062`)

Payload `q062`:

| Item | Nilai |
| --- | --- |
| Pertanyaan | "Did the 1851 and 1871 baked apple recipes both instruct the cook to peel the apples?" |
| Klaim | "Yes, both recipes instruct the cook to peel the apples." |
| Verdict | `SUPPORTED` |
| `evidence_for` | hanya `ye-old-american:baked-apples#directions#0` (1851) |
| Passage 1871 | `ye-old-american:baked-apples-3#directions#0` tidak ada di 10 hit |

Passage 1871 berbunyi "wash, but do not pare them". Verifier tidak pernah
melihatnya, dan tetap menyatakan klaim "both" sebagai `SUPPORTED`.

Dua sebab di kode:

- `src/recipe_qa/pipeline/common.py` `_sentence_claims` menempelkan tiga passage
  top yang sama ke **setiap** kalimat jawaban, tanpa memetakan kalimat ke
  passage.
- `src/recipe_qa/verify/claims.py` `verify_claims` mengambil entailment
  maksimum, lalu berhenti di cabang `cited_support >= threshold`. Kontradiksi
  tidak pernah menjadi veto, dan tidak ada pengecekan bahwa cakupan klaim
  ("both", "which", dua tahun) sepadan dengan jumlah dokumen yang disitasi.

## T3 - Citation gate tidak bisa menyala pada jalur klaim normal

`_sentence_claims` menyalin `passage_id` dari `hits`, lalu `check_citations`
memvalidasi id yang sama terhadap `hits` yang sama. Akibatnya
`unknown_passages` selalu kosong. `AbstainPolicy` hanya memakai
`unknown_passages` dan `missing_evidence`; `span_mismatches` dihitung tetapi
tidak pernah dipakai, dan `require_evidence` bernilai false di config beku.

Rekap artefak:

| Split | `unknown_passages` | `span_mismatches` | `missing_evidence` |
| --- | ---: | ---: | ---: |
| train-65 | 0 | 0 | 0 |
| test-50 | 0 | 0 | 0 |

Jadi gate sitasi tidak pernah menolak apa pun di jalur ini.

## T4 - Klaim diuji terhadap passage, bukan terhadap pertanyaan

`q099` menghasilkan 4 klaim, 3 `SUPPORTED`, semuanya tentang cara memanggang
("set the roaster at a tolerable distance ... heat gradually"). Klaimnya benar
terhadap passage, tetapi tidak ada satu pun yang memuat suhu internal. Tidak
ada tahap yang memeriksa apakah klaim menjawab atribut yang ditanyakan.

Konsekuensinya dua arah: verifier bisa terlalu longgar (`q099`) dan terlalu
ketat sekaligus (21 abstain train-65, 20 abstain test-50 dari verifikasi),
karena keputusannya bergantung pada entailment per passage, bukan pada
kecukupan jawaban.

## Dampak ke angka B4

- "20 dari 39 abstain berasal dari verifikasi" bukan bukti verifier terkalibrasi;
  sebagian berasal dari klaim yang dipotong karena tidak didukung satu passage
  mana pun.
- `q099` dan `q062` adalah dua kegagalan berbeda: satu false confident karena
  klaim tidak relevan ke pertanyaan, satu lagi false confident karena cakupan
  klaim melebihi bukti.
- Angka kalibrasi NLI di `reports/verifier_calibration.md` tetap sah untuk
  keputusan klaim-per-passage; yang tidak diuji di sana adalah cakupan klaim
  dan relevansi ke pertanyaan.

## Usulan perbaikan

Belum diterapkan. Semua perubahan perilaku setelah freeze memerlukan ACC A,
tag baru, dan satu kali run ulang test-50.

1. `verify_claims`: verdict per sitasi. Klaim dengan lebih dari satu
   `evidence_for` harus didukung semua sitasi, dan kontradiksi menjadi veto.
   Hapus fallback `top_n` untuk klaim yang sudah punya sitasi.
2. Pengecekan cakupan klaim: klaim yang memuat "both"/"all"/"which" atau
   menyebut lebih dari satu tahun wajib punya sitasi dari minimal dua `doc_id`;
   jika tidak, `NOT_ENOUGH_EVIDENCE`.
3. Sufficiency: pisahkan menjadi dua gate (`coverage >= tau_coverage` dan
   `sigmoid(top_score) >= tau_score`), atau naikkan bobot retrieval, supaya
   coverage saja tidak bisa membuka gate. Ini mengubah arti tau 0,17, jadi
   butuh keputusan A.
4. Citation policy: pakai `span_mismatches` dan `missing_evidence`, bukan hanya
   `unknown_passages`.
5. Pengecekan relevansi klaim ke pertanyaan: token atribut pertanyaan
   ("temperature", "how long") harus muncul di klaim atau di sitasi.

Validasi perbaikan hanya di train-65. Test-50 dijalankan sekali setelah config
baru dibekukan dan diberi tag.

## Reproduksi

```powershell
Get-Content artifacts/runs/b4-test50-s1/SHA256SUMS.txt
Get-FileHash artifacts/runs/b4-test50-s1/results.jsonl -Algorithm SHA256

uv run python -c "import json; rows=[json.loads(l) for l in open('artifacts/runs/b4-test50-s1/results.jsonl',encoding='utf-8')]; print([r for r in rows if r['query_id'] in ('q062','q099')])"
```
