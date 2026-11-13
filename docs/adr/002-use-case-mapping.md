# ADR-002 — Mapping the project to Use Case C

- **Status:** proposed — **pending lecturer confirmation**
- **Date:** 2026-11-14
- **Owner:** Orang A (Vio)
- **Related:** `spek.md` §2, `RENCANA_LENGKAP.md` §4

## Context

The specification allows three use cases. The group chose the historical recipe
domain. The project needs one explicit mapping so that the output contract,
metrics, and benchmark slices are coherent.

## Decision (proposed)

Map the project to **Use Case C — Temporal Fact-Checking**:

> Given a question (optionally with an `as_of` year), return a short answer,
> decompose it into atomic claims, and give each claim a verdict
> `SUPPORTED`, `REFUTED`, or `NOT_ENOUGH_EVIDENCE`, with evidence for/against
> and a citation. Abstain when the corpus does not support an answer.

## Mapping to the specification

| Spec element (Use Case C) | Implementation |
| --- | --- |
| `SUPPORTED` / `REFUTED` / `NOT_ENOUGH_EVIDENCE` | `claims[].verdict` |
| evidence for/against | `claims[].evidence_for`, `claims[].evidence_against` |
| `as_of` | `claims[].as_of` + temporal metadata filter |
| citation | `passage_id` + span |
| claim decomposition | `claims[]` |
| Macro-F1 | three-class verdict macro-F1 |
| evidence recall | Recall@k against qrels |
| temporal accuracy | all cited passages have `source_year <= as_of` |
| rationale support | citation precision + NLI verifier |
| false confident verdict | non-NEI verdict without supporting evidence |

## Open question

The specification says the use-case mapping must be confirmed by the lecturer.
Until then:

- Corpus and index work can proceed; they are independent of the final mapping.
- Benchmark writing (Week 1, block B) and qrels annotation (C/D) should not be
  frozen until the mapping is confirmed.
- If the lecturer rejects Use Case C, the fallback is to map to Use Case A
  (Academic Policy Intelligence) with a different corpus; that would invalidate
  the recipe benchmark and require a new ADR.

## Out of scope unless separately approved

`Note 1` describes a broader recipe assistant (search by available ingredients,
nutrition estimation). Those features require data that is not in the recipe
corpus and would add new metrics. They are **not** part of this ADR or the
B0–B6 comparison.

## Verification

- `docs/open_questions.md` records the pending confirmation.
- Once confirmed, change the status to `accepted` and add the confirmation date.
