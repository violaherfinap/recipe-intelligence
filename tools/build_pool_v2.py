from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from recipe_qa.benchmark.pool_v2 import build_pool_v2, distribution


def parse_rankings(values: list[str]) -> dict[str, Path]:
    parsed: dict[str, Path] = {}
    for value in values:
        if "=" not in value:
            raise SystemExit(f"--rankings expects name=path, got {value!r}")
        name, path = value.split("=", 1)
        parsed[name] = Path(path)
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build pool v2 from pool v1 and retrieval runs.")
    parser.add_argument("--queries", type=Path, default=Path("benchmark/queries.jsonl"))
    parser.add_argument("--pool", type=Path, default=Path("benchmark/pool_v1.jsonl"))
    parser.add_argument("--meta", type=Path, default=Path("benchmark/pool_v1_meta.jsonl"))
    parser.add_argument(
        "--rankings",
        action="append",
        default=[],
        metavar="NAME=PATH",
        help="retrieval artifact to pool, e.g. b2=artifacts/runs/retrieval_b2_full.json",
    )
    parser.add_argument(
        "--passages",
        type=Path,
        nargs="+",
        default=[Path("data/processed/passages.jsonl")],
    )
    parser.add_argument("--test-docs", type=Path, default=Path("benchmark/test_docs.txt"))
    parser.add_argument("--gold", type=Path, default=Path("benchmark/gold_candidates.jsonl"))
    parser.add_argument("--out", type=Path, default=Path("benchmark/pool_v2.jsonl"))
    parser.add_argument("--meta-out", type=Path, default=Path("benchmark/pool_v2_meta.jsonl"))
    parser.add_argument("--split", default="test")
    parser.add_argument("--top-k", type=int, default=10)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = build_pool_v2(
        queries_path=args.queries,
        pool_path=args.pool,
        meta_path=args.meta,
        rankings=parse_rankings(args.rankings),
        passages_paths=args.passages,
        test_docs_path=args.test_docs,
        gold_path=args.gold,
        out_path=args.out,
        meta_out_path=args.meta_out,
        split=args.split,
        top_k=args.top_k,
    )
    summary = {
        "queries": result.queries,
        "candidates": result.candidates,
        "new_candidates": result.new_candidates,
        "sources": result.sources,
        "per_query": distribution(result.per_query),
        "queries_without_candidates": result.queries_without_candidates,
        "skipped": result.skipped,
    }
    print(json.dumps(summary, indent=2))
    print(f"blinded pool: {args.out}")
    print(f"provenance (do not open while annotating): {args.meta_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
