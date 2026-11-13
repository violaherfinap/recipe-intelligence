"""Command line entry point for the corpus build."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from transformers import AutoTokenizer

from .build import build_corpus


def _token_offsets_factory(model_name: str):
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    # We only need offsets; do not let the tokenizer warn about >512-token
    # sections. No truncation is performed.
    tokenizer.model_max_length = 1_000_000

    def token_offsets(text: str) -> list[tuple[int, int]]:
        encoded = tokenizer(
            text,
            add_special_tokens=False,
            return_offsets_mapping=True,
            truncation=False,
        )
        return [tuple(pair) for pair in encoded["offset_mapping"]]

    return token_offsets


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the recipe corpus artefacts")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build", help="parse recipes, build passages, split, manifests")
    build.add_argument(
        "--raw",
        type=Path,
        default=Path("data/raw/open-recipe-archive/collections/ye-old-american/recipes.jsonl"),
    )
    build.add_argument("--commit-file", type=Path, default=Path("data/corpus_commit.txt"))
    build.add_argument("--out", type=Path, default=Path("data/processed"))
    build.add_argument("--tokenizer", default="BAAI/bge-small-en-v1.5")
    build.add_argument("--max-tokens", type=int, default=350)
    build.add_argument("--overlap", type=int, default=40)
    build.add_argument("--seed", type=int, default=42)
    build.add_argument(
        "--no-dedup",
        action="store_true",
        help="keep near-duplicate recipes (exact duplicates are still removed)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command != "build":
        raise SystemExit(f"unknown command: {args.command}")

    token_offsets = _token_offsets_factory(args.tokenizer)
    result = build_corpus(
        raw_path=args.raw,
        commit_file=args.commit_file,
        out_dir=args.out,
        token_offsets=token_offsets,
        tokenizer_name=args.tokenizer,
        max_tokens=args.max_tokens,
        overlap=args.overlap,
        seed=args.seed,
        dedup=not args.no_dedup,
    )

    summary = {
        "docs": result["manifest"]["counts"]["docs"],
        "docs_indexed": result["manifest"]["counts"]["docs_indexed"],
        "passages": result["manifest"]["counts"]["passages"],
        "duplicates_removed": result["manifest"]["counts"]["duplicates_removed"],
        "errors": result["manifest"]["counts"]["errors"],
        "split": result["manifest"]["split"]["counts"],
        "files": result["manifest"]["files"],
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
