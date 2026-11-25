"""Sufficiency threshold calibration helpers."""

from __future__ import annotations


def answerable_labels(qrels: list[dict]) -> dict[str, bool]:
    labels: dict[str, bool] = {}
    for row in qrels:
        query_id = str(row["query_id"])
        relevance = int(row.get("relevance") or 0)
        labels[query_id] = labels.get(query_id, False) or relevance >= 1
    return labels


def extract_scores(results: list[dict]) -> list[tuple[str, float]]:
    scores = []
    for row in results:
        sufficiency = row.get("sufficiency") or {}
        score = sufficiency.get("score")
        if score is None:
            continue
        scores.append((str(row["query_id"]), float(score)))
    return scores


def balanced_accuracy(
    scored: list[tuple[str, float]],
    labels: dict[str, bool],
    threshold: float,
) -> float:
    positives = [score for query_id, score in scored if labels.get(query_id, False)]
    negatives = [score for query_id, score in scored if not labels.get(query_id, False)]
    if not positives or not negatives:
        return 0.0
    true_positive = sum(1 for score in positives if score >= threshold)
    true_negative = sum(1 for score in negatives if score < threshold)
    return 0.5 * (true_positive / len(positives) + true_negative / len(negatives))


def calibrate(
    scored: list[tuple[str, float]],
    labels: dict[str, bool],
    step: float = 0.01,
) -> dict:
    best_threshold = 0.0
    best_score = -1.0
    sweep = []
    steps = int(round(1.0 / step))
    for index in range(steps + 1):
        threshold = round(index * step, 4)
        score = balanced_accuracy(scored, labels, threshold)
        sweep.append({"threshold": threshold, "balanced_accuracy": score})
        if score > best_score:
            best_score = score
            best_threshold = threshold
    positives = sum(1 for query_id, _ in scored if labels.get(query_id, False))
    return {
        "threshold": best_threshold,
        "balanced_accuracy": best_score,
        "n": len(scored),
        "answerable": positives,
        "no_evidence": len(scored) - positives,
        "sweep": sweep,
    }
