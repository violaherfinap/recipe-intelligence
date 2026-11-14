"""Build a blinded annotation pool for the benchmark."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from recipe_qa.benchmark.pool import build_pool


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queries", type=Path, default=Path("benchmark/queries.jsonl"))
    parser.add_argument(
        "--gold", type=Path, default=Path("benchmark/gold_candidates.jsonl")
    )
    parser.add_argument(
        "--passages", type=Path, default=Path("data/processed/passages.jsonl")
    )
    parser.add_argument("--dense-dir", type=Path, default=Path("indexes"))
    parser.add_argument(
        "--out", type=Path, default=Path("benchmark/pool_v1.jsonl")
    )
    parser.add_argument(
        "--meta", type=Path, default=Path("benchmark/pool_v1_meta.jsonl")
    )
    parser.add_argument("--split", default="test")
    parser.add_argument("--dense-k", type=int, default=10)
    parser.add_argument("--negatives", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--model", default="BAAI/bge-small-en-v1.5"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = build_pool(
        queries_path=args.queries,
        gold_path=args.gold,
        passages_path=args.passages,
        out_path=args.out,
        meta_path=args.meta,
        dense_dir=args.dense_dir,
        model_name=args.model,
        split=args.split,
        dense_k=args.dense_k,
        negatives=args.negatives,
        seed=args.seed,
    )
    print(
        f"queries={result.queries} candidates={result.candidates} "
        f"gold={result.gold} dense={result.dense} negatives={result.negatives}"
    )
    print(f"blinded pool: {args.out}")
    print(f"provenance (do not open while annotating): {args.meta}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
