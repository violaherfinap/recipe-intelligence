"""Command line entry point for index building and smoke retrieval."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .build import build_all_indexes, build_bm25, build_dense, smoke


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build and query retrieval indexes")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name, help_text in (
        ("bm25", "build the BM25 index"),
        ("dense", "build the dense embedding index"),
        ("all", "build both indexes"),
    ):
        command = subparsers.add_parser(name, help=help_text)
        command.add_argument("--passages", type=Path, default=Path("data/processed/passages.jsonl"))
        command.add_argument("--out", type=Path, default=Path("indexes"))
        command.add_argument("--model", default="BAAI/bge-small-en-v1.5")
        command.add_argument("--batch-size", type=int, default=32)

    smoke_parser = subparsers.add_parser("smoke", help="run a BM25 and dense smoke query")
    smoke_parser.add_argument("--passages", type=Path, default=Path("data/processed/passages.jsonl"))
    smoke_parser.add_argument("--out", type=Path, default=Path("indexes"))
    smoke_parser.add_argument("--model", default="BAAI/bge-small-en-v1.5")
    smoke_parser.add_argument("--query", default="tomato soup")
    smoke_parser.add_argument("--k", type=int, default=5)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "bm25":
        payload = build_bm25(args.passages, args.out)
    elif args.command == "dense":
        payload = build_dense(
            args.passages,
            args.out,
            model_name=args.model,
            batch_size=args.batch_size,
        )
    elif args.command == "all":
        payload = build_all_indexes(
            args.passages,
            args.out,
            model_name=args.model,
            batch_size=args.batch_size,
        )
    elif args.command == "smoke":
        payload = smoke(
            args.out,
            args.passages,
            args.query,
            model_name=args.model,
            k=args.k,
        )
    else:
        raise SystemExit(f"unknown command: {args.command}")

    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
