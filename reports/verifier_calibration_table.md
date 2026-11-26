# NLI verifier calibration

- Model: `cross-encoder/nli-deberta-v3-base`
- Query set: `benchmark\queries_train.jsonl` (65 queries)
- Slices: `['easy']`
- Premise context: `True`
- Probe pairs: 317 (all train claims)
- Calibration pairs: 117 (35 gold, 82 synthetic negatives)
- Selected threshold: **0.5**
- Precision 0.8824 · Recall 0.8571 · F1 0.8696 · Balanced accuracy 0.9042

| Threshold | Precision | Recall | F1 | Balanced accuracy |
| ---: | ---: | ---: | ---: | ---: |
| 0.3 | 0.8824 | 0.8571 | 0.8696 | 0.9042 |
| 0.35 | 0.8824 | 0.8571 | 0.8696 | 0.9042 |
| 0.4 | 0.8824 | 0.8571 | 0.8696 | 0.9042 |
| 0.45 | 0.8824 | 0.8571 | 0.8696 | 0.9042 |
| 0.5 | 0.8824 | 0.8571 | 0.8696 | 0.9042 |
| 0.55 | 0.8788 | 0.8286 | 0.8529 | 0.8899 |
| 0.6 | 0.8788 | 0.8286 | 0.8529 | 0.8899 |
| 0.65 | 0.8788 | 0.8286 | 0.8529 | 0.8899 |
| 0.7 | 0.8750 | 0.8000 | 0.8358 | 0.8756 |
| 0.75 | 0.8750 | 0.8000 | 0.8358 | 0.8756 |
| 0.8 | 0.8750 | 0.8000 | 0.8358 | 0.8756 |
| 0.85 | 0.8750 | 0.8000 | 0.8358 | 0.8756 |
| 0.9 | 0.8750 | 0.8000 | 0.8358 | 0.8756 |

## Positive coverage per slice

| Slice | Positives | Mean entailment | Supported at threshold |
| --- | ---: | ---: | ---: |
| easy | 35 | 0.8381 | 30/35 |
| multi-hop | 90 | 0.5473 | 49/90 |
| temporal | 110 | 0.4548 | 50/110 |

Caveat: negatives are synthetic; report precision/recall as a probe, not human-annotated accuracy.
