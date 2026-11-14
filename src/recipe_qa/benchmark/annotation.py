"""Blind annotation helpers shared by the CLI and tests."""

from __future__ import annotations

import json
import os
import random
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from .schema import PoolCandidate, Qrel, Query, VerdictQrel
from .validate import load_qrels, load_queries, read_jsonl


@dataclass(frozen=True)
class JudgmentKey:
    query_id: str
    passage_id: str


def load_pool(path: Path) -> dict[str, list[PoolCandidate]]:
    """Group the blinded pool by query while preserving the file order."""
    grouped: dict[str, list[PoolCandidate]] = {}
    for row in read_jsonl(path):
        candidate = PoolCandidate.model_validate(row)
        grouped.setdefault(candidate.query_id, []).append(candidate)
    return grouped


def order_candidates(
    candidates: Iterable[PoolCandidate], annotator: str
) -> list[PoolCandidate]:
    """Return a deterministic shuffle so annotators do not see pool provenance."""
    ordered = list(candidates)
    query_id = ordered[0].query_id if ordered else ""
    random.Random(f"{annotator}:{query_id}").shuffle(ordered)
    return ordered


def load_judged(path: Path) -> set[JudgmentKey]:
    """Return the keys already written to an annotator output file."""
    if not path.exists():
        return set()
    return {
        JudgmentKey(row.query_id, row.passage_id)
        for row in load_qrels(path)
    }


def append_qrel(path: Path, qrel: Qrel) -> None:
    """Append one judgment immediately so a crash does not lose work."""
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(qrel.model_dump(), ensure_ascii=False) + "\n"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line)
        handle.flush()
        os.fsync(handle.fileno())


def append_verdict(path: Path, verdict: VerdictQrel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(verdict.model_dump(), ensure_ascii=False) + "\n"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line)
        handle.flush()
        os.fsync(handle.fileno())


def relevance_progress(
    queries: list[Query],
    pool: dict[str, list[PoolCandidate]],
    judged: set[JudgmentKey],
) -> dict[str, tuple[int, int]]:
    """Return judged/total candidate counts per query."""
    progress: dict[str, tuple[int, int]] = {}
    for query in queries:
        candidates = pool.get(query.query_id, [])
        done = sum(
            1
            for candidate in candidates
            if JudgmentKey(query.query_id, candidate.passage_id) in judged
        )
        progress[query.query_id] = (done, len(candidates))
    return progress


def verdict_progress(
    queries: list[Query], judged_path: Path
) -> dict[str, tuple[int, int]]:
    """Return judged/total claim counts per query."""
    done: dict[str, set[str]] = {}
    if judged_path.exists():
        with judged_path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                done.setdefault(row["query_id"], set()).add(row["claim_id"])
    progress: dict[str, tuple[int, int]] = {}
    for query in queries:
        total = len(query.gold_claims)
        progress[query.query_id] = (len(done.get(query.query_id, set())), total)
    return progress


def evidence_passages(query_id: str, qrels_path: Path, min_relevance: int = 2) -> list[str]:
    """Return passage IDs judged relevant enough for claim verification."""
    if not qrels_path.exists():
        return []
    return [
        qrel.passage_id
        for qrel in load_qrels(qrels_path)
        if qrel.query_id == query_id and qrel.relevance >= min_relevance
    ]


def load_claim_queries(path: Path) -> dict[str, list[str]]:
    return {query.query_id: list(query.gold_claims) for query in load_queries(path)}
