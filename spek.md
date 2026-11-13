## TBP: FRONTIER LLM RESEARCH & ENGINEERING

## 1\. Prinsip

Tugas ini sengaja dibuat lebih kompleks daripada proyek “membuat chatbot” dengan LLM (atau RAG). Mahasiswa harus menunjukkan kemampuan merancang eksperimen ilmiah, membedakan penyebab error (retrieval, reasoning, tool, source, prompt, dan adaptation), serta membuktikan keputusan desain. Kinerja harus terukur secara komprehensif dengan berbagai metrics agar coverage menyeluruh dari berbagai aspek.

| Pokok Topic | Implementasi |
| :---- | :---- |
| LLM, prompt engineering, fine-tuning terbatas dan RAG | Perbandingan B0-B6, prompt registry, hybrid RAG, agentic tool use, LoRA/QLoRA. |
| Evaluasi kuantitatif/kualitatif, etika, bias, keamanan | Benchmark locked test, human adjudication, hallucination audit, privasi dan fairness. |
| Proyek NLP/LLM kasus nyata | Sistem end-to-end, versioning, observability, evaluation harness, laporan, demonstrasi teknis dan pertanggungjawaban individu. |

## 1.1. Konvensi

| Status | Arti | Implikasi |
| :---- | :---- | :---- |
| WAJIB | Harus di implement dan diuji serta reproducible | Pokok penilaian. |
| SETARA | Substitusi tools boleh bila metode/kemampuan dan tingkat kesulitan sama. | Memerlukan ADR dan alasan pemilihan tools |

## 1.2. Etika

- Hanya memakai teks/dokumen legal dan berizin; wajib mempertahankan sumber, versi, hak penggunaan. Tidak mengirim PII atau dokumen rahasia ke penyedia model eksternal tanpa concern yang dibenarkan.

- Dilarang mengoptimalkan sistem menggunakan test yang hanya optimal di case tertentu, memasukkan jawaban (ground truth) ke instruksi model, atau memilih hasil terbaik tanpa experiment yang komprehensif. Corpus yang secara alami mengandung bagian informasi jawaban tetap boleh dipakai, tetapi answer key / label dari evaluasi tidak boleh bocor.

- Semua klaim “lebih baik”, “aman”, “reliable”, “agentic”, “fine-tuned”, “real-time”, dan “grounded” harus punya definisi yang jelas tanpa klaim berlebih

- Tahapan training tidak mewajibkan model besar. Gunakan compact open-weight base model (contoh kelas 0.5B-3B) dan LoRA/QLoRA yang realistis, laptop GPU, kaggle, google colab, atau resource komputasi yang diizinkan boleh dipakai dengan bukti konfigurasi.

## 2\. Contoh use case

Setiap kelompok memilih SATU use case. Semua use case wajib menjadikan retrieval relevan terhadap answer.

| Use case | Masalah yang wajib diselesaikan | Output minimum | Contoh metrik |
| :---- | :---- | :---- | :---- |
| A. Academic Policy Intelligence | Pertanyaan multi-hop tentang aturan/layanan akademik, versi kebijakan bertentangan, tanggal efektif, dan permintaan di luar cakupan. | Jawaban, klaim atomik, sitasi passage, valid\_time, verdict supported/unknown, alasan abstain. | Qrels dokumen/passage; correctness, evidence recall, citation precision. |
| B. Evidence-Aware Sentiment & Emotion | Sentimen dan emosi teks Indonesia informal/campur bahasa; ambiguous/multi-label; domain drift; gunakan retrieval label policy dan contoh berizin dari train split. | Label set, skor/ketidakpastian terkalibrasi bila tersedia, rationale berbukti span teks, guideline version, abstain. | Macro-F1, per-class/multilabel F1,, evidence support. |
| C. Temporal Fact-Checking | Informasi publik yang berubah sesuai waktu, cross referensi, dua sumber yang bertentangan, dan kemungkinan NOT ENOUGH EVIDENCE. Misalnya undang undang | SUPPORTED/REFUTED/NOT\_E NOUGH\_EVIDENCE, evidence for/against, as\_of, citation, claim decomposition. | Macro-F1, evidence recall, temporal accuracy, rationale support, false confident verdict. |

## 3\. Target minimum dan evaluasi research-grade

| Elemen | Standar wajib minimum | Cara verifikasi |
| :---- | :---- | :---- |
| Corpus utama | Sumber nyata public atau private dengan izin, minimal 300 dokumen. | Source register, hash, index documents |
| Benchmark utama | Minimal 100 instance query. | Manifest split dan SHA-256; dedup/near-dup checks. |
| Evidence/qrels | Qrels untuk seluruh query berlabel answerable yang bergantung pada retrieval dalam test, dan label unanswerable untuk query tanpa evidence. | Qrels id, relevance level, document/passage version, annotation rule. |
| Human review | Instance dianotasi blindly oleh minimal dua annotator; jika ada label berbeda maka lakukan adjudication. | Agreement, disagreement log, konflik dan resolution notes. |
| Red-team suite | Minimal 20 kasus terpisah: 5 prompt/document injection, 5 policy/PII leakage, 5 tool misuse, 5 safety/robustness. | Fixture ID, goal, attack surface, baseline outcome, mitigation outcome. |
| LLM comparison | Menggunakan model LLM plain dari sumber langsung dibandingkan dengan LLM yang telah di tuning dengan LoRA/QLoRA. | Raw output per item, prompt/model/index versions, per-run token/latency. |
| Repeatability | Minimal 3 run independent pada subset test untuk setiap konfigurasi | Run manifests, seed/sampling; variance. |
| Serving | Sistem UI dan API yang bisa diuji, implementasikan fallback jika perlu. catat logs. | UI, API, screenshot, log, trace dan live demo. |

## 4\. Tujuh konfigurasi pembanding B0-B6

| ID | Konfigurasi | Fitur pembeda | Eksperimen |
| :---- | :---- | :---- | :---- |
| B0 | Direct LLM baseline | Zero-shot tanpa retrieval, tanpa tool dan tanpa evidence verification. | Model dasar, sampling dan output contract tetap. |
| B1 | Structured Prompted LLM | Few-shot (hanya train/dev), constraint, schema dan policy abstain. | Ukur efek prompt terhadap B0. |
| B2 | Naive RAG | Dense retrieval \+ fixed chunk \+ top-k context \+ answer. | Ukur efek retrieval dibanding B1. |
| B3 | Hybrid RAG | BM25 \+ dense \+ fusion \+ reranker \+ metadata filter. Ukur retrieval effectiveness dan tambahan | latensi. |
| B4 | Self-corrective/Adaptive RAG | Query planner, evidence sufficiency score, retrieval retry bounded, claim verifier, abstain. | Ukur retry benefit, failure dan biaya. |
| B5 |  | B4 \+ Parameter-Efficient Fine-Tuning Base generator yang sama dipasangi LoRA/QLoRA untuk task domain; dataset train berizin. | Same retrieval/index/prompt budgets; simpan adapter dan training logs. |
| B6 | Guarded Agentic LLM | B5 atau B4 yang paling kuat (dipilih di dev), structured tool args, authorization, temporal checking, verified final answer. | Catat model asal; evaluasi delta agentic terhadap parent yang identik. |

Kewajiban: gunakan base generator yang sama pada B0-B5; jangan mengganti model besar pada kandidat lalu bilang ada peningkatan ke RAG. B6 wajib dibandingkan dengan parent B4 atau B5 yang sama, bukan hanya dibanding B0.

## 4.1. Ablation dan hipotesis

- A1: fixed vs heading-aware vs hierarchical chunking; log passage recall, index size, context length dan groundedness.

- A2: dense vs BM25 vs hybrid vs hybrid+reranking pada qrels identik; laporkan Recall@5/10, nDCG@10, MRR@10.

- A3: no-verifier vs independent verifier \+ bounded repair; ukur unsupported claims dan false-refusal.

- A4: no-adapter vs LoRA/QLoRA pada parent B4; ukur gain, overfit, resource, dan performa OOD.

- A5: B6 without vs with tool calling; ukur tool correctness, unsafe call rate, budget overrun dan end-task outcome.

- A6: fixed vs adaptive retrieval policy; ukur kualitas pada easy/multi-hop/conflict/no-evidence slice dan biaya per kualitas.

- A7: 2 level token/context budgets (misal 2k vs 6k token atau proporsi sesuai model); ukur Pareto quality, p95 dan biaya.

Untuk semua ablation: satu variabel utama diubah per percobaan; dev dipakai memilih konfigurasi.