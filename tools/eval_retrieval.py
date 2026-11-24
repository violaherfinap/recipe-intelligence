from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from collections import defaultdict
from pathlib import Path

from recipe_qa.config import load_retrieval_config, load_system_config, load_yaml
from recipe_qa.corpus.build import read_jsonl
from recipe_qa.eval.metrics.coverage import (
    doc_recall_at_k,
    judged_rate_at_k,
    split_coverage_at_k,
    unjudged_test_rate_at_k,
)
from recipe_qa.eval.metrics.retrieval import evaluate_retrieval
from recipe_qa.retrieval.search import Retriever


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "unknown"


def load_config(path: Path):
    payload = load_yaml(path)
    if isinstance(payload, dict) and "model" in payload:
        config = load_system_config(path)
        return config.id, config.retrieval
    config = load_retrieval_config(path)
    return config.id, config.retrieval


def load_qrels(path: Path) -> tuple[dict[str, dict[str, int]], dict[str, str]]:
    qrels: dict[str, dict[str, int]] = defaultdict(dict)
    doc_by_passage: dict[str, str] = {}
    for row in read_jsonl(path):
        qrels[row["query_id"]][row["passage_id"]] = int(row["relevance"])
        doc_by_passage[row["passage_id"]] = row["doc_id"]
    return dict(qrels), doc_by_passage


def load_test_docs(path: Path) -> set[str]:
    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = int(round(fraction * (len(ordered) - 1)))
    return ordered[position]


def query_metrics(
    query_id: str,
    relevance: dict[str, int],
    gold_docs: set[str],
    hits: list[dict],
    final_k: int,
    test_docs: set[str],
) -> dict:
    ranked_pids = [hit["passage_id"] for hit in hits]
    ranked_docs = [hit["doc_id"] for hit in hits]
    judged = set(relevance)
    return {
        "query_id": query_id,
        "retrieved": len(ranked_pids),
        "doc_recall": doc_recall_at_k(ranked_docs, gold_docs, final_k),
        "judged_rate": judged_rate_at_k(ranked_pids, judged, final_k),
        "test_split_rate": split_coverage_at_k(ranked_docs, test_docs, final_k),
        "unjudged_test_rate": unjudged_test_rate_at_k(
            ranked_pids, ranked_docs, judged, test_docs, final_k
        ),
    }


def evaluate_slice(
    query_ids: set[str],
    qrels: dict[str, dict[str, int]],
    doc_by_passage: dict[str, str],
    rankings: dict[str, list[str]],
    hits_by_query: dict[str, list[dict]],
    final_k: int,
    test_docs: set[str],
) -> dict:
    slice_qrels = {query_id: qrels[query_id] for query_id in query_ids if query_id in qrels}
    slice_rankings = {query_id: rankings.get(query_id, [])[:final_k] for query_id in query_ids}
    metrics = evaluate_retrieval(slice_qrels, slice_rankings)

    doc_scores: list[float] = []
    judged_scores: list[float] = []
    test_scores: list[float] = []
    unjudged_scores: list[float] = []
    for query_id in sorted(query_ids):
        relevance = qrels.get(query_id, {})
        gold_docs = {
            doc_by_passage[passage_id]
            for passage_id, grade in relevance.items()
            if grade >= 1 and passage_id in doc_by_passage
        }
        row = query_metrics(
            query_id,
            relevance,
            gold_docs,
            hits_by_query.get(query_id, []),
            final_k,
            test_docs,
        )
        if gold_docs:
            doc_scores.append(row["doc_recall"])
        judged_scores.append(row["judged_rate"])
        test_scores.append(row["test_split_rate"])
        unjudged_scores.append(row["unjudged_test_rate"])

    def mean(values: list[float]) -> float:
        return sum(values) / len(values) if values else 0.0

    metrics["doc_recall"] = mean(doc_scores)
    metrics["judged_rate"] = mean(judged_scores)
    metrics["test_split_rate"] = mean(test_scores)
    metrics["unjudged_test_rate"] = mean(unjudged_scores)
    metrics["slice_queries"] = len(query_ids)
    return metrics


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate one retrieval config.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--queries", type=Path, default=Path("benchmark/queries.jsonl"))
    parser.add_argument("--qrels", type=Path, default=Path("benchmark/qrels.jsonl"))
    parser.add_argument("--test-docs", type=Path, default=Path("benchmark/test_docs.txt"))
    parser.add_argument("--limit", type=int, default=0, help="0 means all queries")
    parser.add_argument(
        "--retain-k",
        type=int,
        default=10,
        help="store at least this many hits per query for pooling",
    )
    parser.add_argument(
        "--eval-k",
        type=int,
        default=0,
        help="evaluation cutoff; 0 uses the config final_k",
    )
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    config_id, retrieval = load_config(args.config)
    final_k = retrieval.final_k
    eval_k = args.eval_k or final_k
    retain_k = max(final_k, eval_k, args.retain_k)
    retrieval = retrieval.model_copy(update={"final_k": retain_k})

    queries = list(read_jsonl(args.queries))
    if args.limit:
        queries = queries[: args.limit]
    query_ids = {row["query_id"] for row in queries}

    retriever = Retriever(retrieval)
    rankings: dict[str, list[str]] = {}
    hits_by_query: dict[str, list[dict]] = {}
    latencies: list[float] = []
    for row in queries:
        started = time.perf_counter()
        hits = retriever.retrieve(row["text"], filter_spec=row.get("filter"))
        latencies.append((time.perf_counter() - started) * 1000.0)
        hit_rows = [hit.to_dict() for hit in hits]
        rankings[row["query_id"]] = [hit["passage_id"] for hit in hit_rows]
        hits_by_query[row["query_id"]] = hit_rows

    qrels, doc_by_passage = load_qrels(args.qrels)
    qrels = {query_id: relevance for query_id, relevance in qrels.items() if query_id in query_ids}
    test_docs = load_test_docs(args.test_docs)

    overall = evaluate_slice(
        query_ids, qrels, doc_by_passage, rankings, hits_by_query, eval_k, test_docs
    )
    slices: dict[str, dict] = {}
    by_slice: dict[str, set[str]] = defaultdict(set)
    for row in queries:
        by_slice[row.get("slice", "unknown")].add(row["query_id"])
    for slice_name, ids in sorted(by_slice.items()):
        slices[slice_name] = evaluate_slice(
            ids, qrels, doc_by_passage, rankings, hits_by_query, eval_k, test_docs
        )

    payload = {
        "config": config_id,
        "config_path": str(args.config),
        "mode": retrieval.mode,
        "chunking": retrieval.chunking,
        "final_k": final_k,
        "eval_k": eval_k,
        "retain_k": retain_k,
        "queries": len(queries),
        "qrels": str(args.qrels),
        "qrels_sha256": sha256_file(args.qrels),
        "queries_sha256": sha256_file(args.queries),
        "git_commit": git_commit(),
        "metrics": overall,
        "per_slice": slices,
        "latency_ms": {
            "p50": percentile(latencies, 0.50),
            "p95": percentile(latencies, 0.95),
            "mean": sum(latencies) / len(latencies) if latencies else 0.0,
        },
        "rankings": {query_id: hits_by_query[query_id][:retain_k] for query_id in rankings},
    }

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    summary = {
        "config": config_id,
        "queries": len(queries),
        "final_k": final_k,
        "eval_k": eval_k,
        "metrics": overall,
        "latency_ms": payload["latency_ms"],
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
