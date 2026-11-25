"""Run one retrieval configuration over benchmark queries (A2 smoke/eval helper)."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from ..config import load_retrieval_config
from ..corpus.build import read_jsonl
from ..eval.metrics.retrieval import evaluate_retrieval
from .search import Retriever


def load_qrels(path: Path) -> dict[str, dict[str, int]]:
    qrels: dict[str, dict[str, int]] = defaultdict(dict)
    for row in read_jsonl(path):
        qrels[row["query_id"]][row["passage_id"]] = int(row["relevance"])
    return dict(qrels)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a retrieval config over queries")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--queries", type=Path, default=Path("benchmark/queries.jsonl"))
    parser.add_argument("--qrels", type=Path, default=Path("benchmark/qrels.jsonl"))
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="number of queries to run; 0 means all (default: 20)",
    )
    args = parser.parse_args(argv)

    experiment = load_retrieval_config(args.config)
    queries = list(read_jsonl(args.queries))
    if args.limit:
        queries = queries[: args.limit]

    retriever = Retriever(experiment.retrieval)
    rankings: dict[str, list[str]] = {}
    for query in queries:
        hits = retriever.retrieve(query["text"], filter_spec=query.get("filter"))
        rankings[query["query_id"]] = [hit.passage_id for hit in hits]

    qrels = load_qrels(args.qrels)
    run_ids = set(rankings)
    qrels = {query_id: relevance for query_id, relevance in qrels.items() if query_id in run_ids}
    metrics = evaluate_retrieval(qrels, rankings)
    payload = {
        "id": experiment.id,
        "queries": len(queries),
        "metrics": metrics,
        "rankings": rankings,
    }
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"id": experiment.id, "queries": len(queries), "metrics": metrics}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
