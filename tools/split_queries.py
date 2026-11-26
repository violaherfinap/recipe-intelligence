from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from recipe_qa.benchmark.query_split import SLICES, split_benchmark


def parse_counts(values: list[str]) -> dict[str, int]:
    parsed: dict[str, int] = {}
    for value in values:
        if "=" not in value:
            raise SystemExit(f"--train-counts expects slice=count, got {value!r}")
        name, count = value.split("=", 1)
        if name not in SLICES:
            raise SystemExit(f"unknown slice {name!r}; choose from {SLICES}")
        parsed[name] = int(count)
    missing = [name for name in SLICES if name not in parsed]
    if missing:
        raise SystemExit(f"--train-counts is missing slices: {missing}")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Split the frozen benchmark queries into stratified train/test sets."
    )
    parser.add_argument("--queries", type=Path, default=Path("benchmark/queries.jsonl"))
    parser.add_argument("--qrels", type=Path, default=Path("benchmark/qrels.jsonl"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train-total", type=int, default=65)
    parser.add_argument(
        "--train-counts",
        nargs="*",
        default=None,
        metavar="SLICE=COUNT",
        help="override per-slice train counts, e.g. easy=20 multi-hop=14 temporal=17 no-evidence=14",
    )
    parser.add_argument("--out", type=Path, default=Path("benchmark/query_split.json"))
    parser.add_argument("--out-dir", type=Path, default=Path("benchmark"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    train_counts = parse_counts(args.train_counts) if args.train_counts else None
    result = split_benchmark(
        queries_path=args.queries,
        qrels_path=args.qrels,
        out_path=args.out,
        out_dir=args.out_dir,
        seed=args.seed,
        train_total=args.train_total,
        train_counts=train_counts,
    )
    summary = {
        "queries": result.queries,
        "train": result.train,
        "test": result.test,
        "train_slices": result.train_slices,
        "test_slices": result.test_slices,
        "components": {
            "total": result.components,
            "train": result.train_components,
            "mixed_slice": result.mixed_slice_components,
        },
        "gold_docs": {
            "train": result.gold_docs_train,
            "test": result.gold_docs_test,
            "overlap": result.gold_doc_overlap,
        },
        "queries_sha256": result.queries_sha256,
        "qrels_sha256": result.qrels_sha256,
        "train_sha256": result.train_sha256,
        "test_sha256": result.test_sha256,
    }
    print(json.dumps(summary, indent=2))
    print(f"written: {args.out}")
    print(f"written: {args.out_dir / 'queries_train.jsonl'}")
    print(f"written: {args.out_dir / 'queries_test.jsonl'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
