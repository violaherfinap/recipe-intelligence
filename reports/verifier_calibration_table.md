# NLI verifier calibration

- Model: `cross-encoder/nli-deberta-v3-base`
- Query set: `benchmark\queries_train.jsonl` (65 queries)
- Slices: `['easy']`
- Premise context: `True`
- Probe pairs: 317 (all train claims)
- Calibration pairs: 117 (35 gold, 82 synthetic negatives)
- Selected threshold: **0.5**
- Precision 0.7500 · Recall 0.8571 · F1 0.8000 · Balanced accuracy 0.8676

| Threshold | Precision | Recall | F1 | Balanced accuracy |
| ---: | ---: | ---: | ---: | ---: |
| 0.3 | 0.7500 | 0.8571 | 0.8000 | 0.8676 |
| 0.35 | 0.7500 | 0.8571 | 0.8000 | 0.8676 |
| 0.4 | 0.7500 | 0.8571 | 0.8000 | 0.8676 |
| 0.45 | 0.7500 | 0.8571 | 0.8000 | 0.8676 |
| 0.5 | 0.7500 | 0.8571 | 0.8000 | 0.8676 |
| 0.55 | 0.7436 | 0.8286 | 0.7838 | 0.8533 |
| 0.6 | 0.7436 | 0.8286 | 0.7838 | 0.8533 |
| 0.65 | 0.7436 | 0.8286 | 0.7838 | 0.8533 |
| 0.7 | 0.7368 | 0.8000 | 0.7671 | 0.8390 |
| 0.75 | 0.7778 | 0.8000 | 0.7887 | 0.8512 |
| 0.8 | 0.8000 | 0.8000 | 0.8000 | 0.8573 |
| 0.85 | 0.8000 | 0.8000 | 0.8000 | 0.8573 |
| 0.9 | 0.8000 | 0.8000 | 0.8000 | 0.8573 |

## Positive coverage per slice

| Slice | Positives | Mean entailment | Supported at threshold |
| --- | ---: | ---: | ---: |
| easy | 35 | 0.8381 | 30/35 |
| multi-hop | 90 | 0.5473 | 49/90 |
| temporal | 110 | 0.4548 | 50/110 |

Caveat: negatives are synthetic; report precision/recall as a probe, not human-annotated accuracy.
