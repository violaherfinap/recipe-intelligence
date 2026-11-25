"""Claim-level metrics for verdicts, citations, and evidence support."""

from __future__ import annotations

from collections.abc import Sequence

VERDICT_LABELS = ("SUPPORTED", "REFUTED", "NOT_ENOUGH_EVIDENCE")


def _f1(true_positives: int, false_positives: int, false_negatives: int) -> float:
    if true_positives == 0:
        return 0.0
    precision = true_positives / (true_positives + false_positives)
    recall = true_positives / (true_positives + false_negatives)
    return 2 * precision * recall / (precision + recall)


def macro_f1(
    gold: Sequence[str],
    predicted: Sequence[str],
    labels: Sequence[str] = VERDICT_LABELS,
) -> float:
    if len(gold) != len(predicted):
        raise ValueError("gold and predicted must have the same length")
    scores: list[float] = []
    for label in labels:
        pairs = zip(gold, predicted, strict=True)
        true_positives = sum(1 for actual, guess in pairs if actual == label and guess == label)
        pairs = zip(gold, predicted, strict=True)
        false_positives = sum(1 for actual, guess in pairs if actual != label and guess == label)
        pairs = zip(gold, predicted, strict=True)
        false_negatives = sum(1 for actual, guess in pairs if actual == label and guess != label)
        scores.append(_f1(true_positives, false_positives, false_negatives))
    return sum(scores) / len(scores) if scores else 0.0


def citation_precision(valid_citations: int, total_citations: int) -> float:
    if total_citations <= 0:
        return 0.0
    return valid_citations / total_citations


def citation_recall(supported_with_citation: int, supported_claims: int) -> float:
    if supported_claims <= 0:
        return 0.0
    return supported_with_citation / supported_claims


def unsupported_claim_rate(claims_without_evidence: int, total_claims: int) -> float:
    if total_claims <= 0:
        return 0.0
    return claims_without_evidence / total_claims
