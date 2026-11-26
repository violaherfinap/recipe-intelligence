from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from ..benchmark.schema import Qrel, Query


@dataclass(frozen=True)
class ProbePair:
    query_id: str
    slice: str
    claim_id: str
    claim: str
    passage_id: str
    label: int
    kind: str

    def to_dict(self) -> dict:
        return {
            "query_id": self.query_id,
            "slice": self.slice,
            "claim_id": self.claim_id,
            "claim": self.claim,
            "passage_id": self.passage_id,
            "label": self.label,
            "kind": self.kind,
        }


_WORD_RE = re.compile(r"[a-z]{4,}")


def _tokens(text: str) -> set[str]:
    return set(_WORD_RE.findall(text.lower()))


def _rank_key(seed: int, query_id: str, claim_id: str, passage_id: str) -> str:
    return hashlib.sha256(f"{seed}:{query_id}:{claim_id}:{passage_id}".encode()).hexdigest()


def build_probe(
    queries: list[Query],
    qrels: list[Qrel],
    passages: dict[str, dict],
    seed: int = 42,
    negatives_per_claim: int = 1,
    candidate_split: str | None = "train",
) -> list[ProbePair]:
    gold_by_query: dict[str, list[str]] = {}
    gold_docs: dict[str, set[str]] = {}
    gold_passage_ids: set[str] = set()
    for row in qrels:
        if row.relevance != 2:
            continue
        gold_by_query.setdefault(row.query_id, []).append(row.passage_id)
        gold_docs.setdefault(row.query_id, set()).add(row.doc_id)
        gold_passage_ids.add(row.passage_id)
    forbidden_docs = set().union(*gold_docs.values()) if gold_docs else set()

    candidate_ids = [
        passage_id
        for passage_id, passage in passages.items()
        if str(passage.get("text", "")).strip()
        and (candidate_split is None or passage.get("split") == candidate_split)
        and passage_id not in gold_passage_ids
        and passage.get("doc_id") not in forbidden_docs
    ]
    tokens_by_passage = {
        passage_id: _tokens(str(passages[passage_id].get("text", "")))
        for passage_id in candidate_ids
    }

    pairs: list[ProbePair] = []
    for query in queries:
        gold_passages = sorted(gold_by_query.get(query.query_id, []))
        if not gold_passages:
            continue
        for index, claim in enumerate(query.gold_claims, start=1):
            claim_id = f"c{index}"
            for passage_id in gold_passages:
                if passage_id not in passages:
                    continue
                pairs.append(
                    ProbePair(
                        query_id=query.query_id,
                        slice=query.slice,
                        claim_id=claim_id,
                        claim=claim,
                        passage_id=passage_id,
                        label=1,
                        kind="gold",
                    )
                )
            if negatives_per_claim <= 0:
                continue
            claim_tokens = _tokens(claim)
            candidates = list(candidate_ids)
            candidates.sort(
                key=lambda passage_id: (
                    -len(claim_tokens & tokens_by_passage[passage_id]),
                    _rank_key(seed, query.query_id, claim_id, passage_id),
                )
            )
            for passage_id in candidates[:negatives_per_claim]:
                pairs.append(
                    ProbePair(
                        query_id=query.query_id,
                        slice=query.slice,
                        claim_id=claim_id,
                        claim=claim,
                        passage_id=passage_id,
                        label=0,
                        kind="synthetic_negative",
                    )
                )
    return pairs


def sweep_thresholds(scored: list[tuple[float, int]], thresholds: list[float]) -> list[dict]:
    positives = sum(1 for _, label in scored if label == 1)
    negatives = len(scored) - positives
    rows = []
    for threshold in thresholds:
        tp = sum(1 for score, label in scored if label == 1 and score >= threshold)
        fn = positives - tp
        fp = sum(1 for score, label in scored if label == 0 and score >= threshold)
        tn = negatives - fp
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / positives if positives else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        balanced = 0.5 * (
            (tp / positives if positives else 0.0) + (tn / negatives if negatives else 0.0)
        )
        rows.append(
            {
                "threshold": threshold,
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "tn": tn,
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "balanced_accuracy": balanced,
            }
        )
    return rows


def select_threshold(sweep: list[dict]) -> dict:
    if not sweep:
        raise ValueError("empty sweep")
    return max(
        sweep,
        key=lambda row: (
            row["balanced_accuracy"],
            row["f1"],
            row["threshold"],
        ),
    )


def threshold_grid(start: float = 0.30, stop: float = 0.90, step: float = 0.05) -> list[float]:
    count = int(round((stop - start) / step)) + 1
    return [round(start + index * step, 4) for index in range(count)]


def calibrate(
    scored: list[tuple[float, int]],
    thresholds: list[float],
) -> dict:
    sweep = sweep_thresholds(scored, thresholds)
    best = select_threshold(sweep)
    positives = sum(1 for _, label in scored if label == 1)
    return {
        "pairs": len(scored),
        "positives": positives,
        "negatives": len(scored) - positives,
        "threshold": best["threshold"],
        "precision": best["precision"],
        "recall": best["recall"],
        "f1": best["f1"],
        "balanced_accuracy": best["balanced_accuracy"],
        "sweep": sweep,
        "caveat": "negatives are synthetic; report precision/recall as a probe, not human-annotated accuracy",
    }
