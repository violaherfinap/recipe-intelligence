from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from .schema import GoldCandidate, PoolCandidate, PoolMeta
from .validate import load_passages_many, load_queries, read_jsonl, write_jsonl


@dataclass
class PoolBuildResult:
    queries: int
    candidates: int
    new_candidates: int
    sources: dict[str, int] = field(default_factory=dict)
    per_query: dict[str, int] = field(default_factory=dict)
    skipped: dict[str, int] = field(default_factory=dict)

    @property
    def queries_without_candidates(self) -> list[str]:
        return sorted(query_id for query_id, count in self.per_query.items() if count == 0)


def _load_rankings(path: Path) -> tuple[str | None, dict[str, list]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if "rankings" not in payload:
        raise ValueError(f"{path} has no rankings block")
    return payload.get("chunking"), payload["rankings"]


def build_pool_v2(
    queries_path: Path,
    pool_path: Path,
    meta_path: Path,
    rankings: dict[str, Path],
    passages_paths: list[Path],
    test_docs_path: Path,
    gold_path: Path,
    out_path: Path,
    meta_out_path: Path,
    split: str = "test",
    top_k: int = 10,
) -> PoolBuildResult:
    queries = load_queries(queries_path)
    passages = load_passages_many(passages_paths)
    test_docs = {
        line.strip()
        for line in test_docs_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    gold = [GoldCandidate.model_validate(row) for row in read_jsonl(gold_path)]

    pool_rows = read_jsonl(pool_path)
    meta_rows = [PoolMeta.model_validate(row).model_dump() for row in read_jsonl(meta_path)]
    existing = {(row["query_id"], row["passage_id"]) for row in pool_rows}
    meta_by_key = {(row["query_id"], row["passage_id"]): row for row in meta_rows}
    missing_meta = existing - set(meta_by_key)
    if missing_meta:
        raise ValueError(f"pool v1 rows without provenance meta: {sorted(missing_meta)[:5]}")

    skipped: Counter[str] = Counter()
    per_query: dict[str, set[str]] = defaultdict(set)

    for row in pool_rows:
        key = (row["query_id"], row["passage_id"])
        passage = passages.get(row["passage_id"])
        if passage is None:
            raise ValueError(f"{key}: passage not found in passage files")
        if passage.get("split") != split:
            raise ValueError(f"{key}: pool v1 passage is not in split={split}")
        if passage["doc_id"] != row["doc_id"]:
            raise ValueError(f"{key}: doc_id mismatch between pool and passages")
        per_query[row["query_id"]].add(row["passage_id"])

    sources: Counter[str] = Counter(row["source"] for row in meta_rows)

    for run_id, path in rankings.items():
        chunking, run_rankings = _load_rankings(path)
        for query in queries:
            hits = run_rankings.get(query.query_id, [])[:top_k]
            for rank, hit in enumerate(hits, start=1):
                passage_id = hit if isinstance(hit, str) else hit.get("passage_id")
                if not passage_id:
                    skipped["missing_passage_id"] += 1
                    continue
                passage = passages.get(passage_id)
                if passage is None:
                    skipped["unknown_passage"] += 1
                    continue
                if passage.get("split") != split:
                    skipped["wrong_split"] += 1
                    continue
                if passage["doc_id"] not in test_docs:
                    skipped["not_test_doc"] += 1
                    continue
                key = (query.query_id, passage_id)
                per_query[query.query_id].add(passage_id)
                if key in meta_by_key:
                    continue
                score = hit.get("score") if isinstance(hit, dict) else None
                meta_by_key[key] = PoolMeta(
                    query_id=query.query_id,
                    passage_id=passage_id,
                    source="retrieval",
                    run_id=run_id,
                    chunking=chunking,
                    rank=rank,
                    score=float(score) if score is not None else None,
                ).model_dump()
                sources["retrieval"] += 1

    for candidate in gold:
        for passage_id in candidate.passage_ids:
            if (candidate.query_id, passage_id) not in meta_by_key:
                raise ValueError(
                    f"gold passage missing from pool: {candidate.query_id} {passage_id}"
                )
            per_query[candidate.query_id].add(passage_id)

    for query in queries:
        per_query.setdefault(query.query_id, set())

    ordered_keys = sorted(meta_by_key)
    output_rows = [
        PoolCandidate(
            query_id=query_id,
            passage_id=passage_id,
            doc_id=passages[passage_id]["doc_id"],
        ).model_dump()
        for query_id, passage_id in ordered_keys
    ]
    output_meta = [meta_by_key[key] for key in ordered_keys]

    write_jsonl(out_path, output_rows)
    write_jsonl(meta_out_path, output_meta)

    counts = {query.query_id: len(per_query[query.query_id]) for query in queries}
    return PoolBuildResult(
        queries=len(queries),
        candidates=len(output_rows),
        new_candidates=len(set(ordered_keys) - existing),
        sources=dict(sorted(sources.items())),
        per_query=counts,
        skipped=dict(sorted(skipped.items())),
    )


def distribution(per_query: dict[str, int]) -> dict[str, float]:
    values = list(per_query.values())
    if not values:
        return {"min": 0, "median": 0.0, "max": 0}
    return {
        "min": min(values),
        "median": float(statistics.median(values)),
        "max": max(values),
    }
