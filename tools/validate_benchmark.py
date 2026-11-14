"""Validate benchmark queries, gold candidates, and no-evidence checks."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from recipe_qa.benchmark.validate import validate_benchmark


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queries", type=Path, default=Path("benchmark/queries.jsonl"))
    parser.add_argument(
        "--gold", type=Path, default=Path("benchmark/gold_candidates.jsonl")
    )
    parser.add_argument(
        "--passages", type=Path, default=Path("data/processed/passages.jsonl")
    )
    parser.add_argument("--split", type=Path, default=Path("data/processed/split.json"))
    parser.add_argument(
        "--no-evidence", type=Path, default=Path("benchmark/no_evidence_check.csv")
    )
    parser.add_argument(
        "--docs", type=Path, default=Path("data/processed/docs.jsonl")
    )
    parser.add_argument(
        "--strict", action="store_true", help="treat warnings as errors"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = validate_benchmark(
        queries_path=args.queries,
        gold_path=args.gold,
        passages_path=args.passages,
        split_path=args.split,
        no_evidence_path=args.no_evidence,
        docs_path=args.docs,
    )
    print(f"queries: {sum(report.counts.values())} {report.counts}")
    if report.warnings:
        print(f"warnings: {len(report.warnings)}")
        for warning in report.warnings:
            print(f"  WARN {warning}")
    if report.errors:
        print(f"errors: {len(report.errors)}")
        for error in report.errors:
            print(f"  ERROR {error}")
        return 1
    if args.strict and report.warnings:
        return 1
    print("benchmark valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
