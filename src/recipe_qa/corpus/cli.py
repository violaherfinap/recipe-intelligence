"""Command line entry point for the corpus build."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from transformers import AutoTokenizer

from .build import build_corpus, build_passages, read_jsonl, write_json, write_jsonl
from .schema import Doc


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

    passages = subparsers.add_parser(
        "passages",
        help="build a passages file for one chunking mode without rebuilding the corpus",
    )
    passages.add_argument("--docs", type=Path, default=Path("data/processed/docs.jsonl"))
    passages.add_argument("--out", type=Path, required=True)
    passages.add_argument(
        "--mode",
        choices=("section", "fixed", "hierarchical"),
        default="section",
    )
    passages.add_argument("--tokenizer", default="BAAI/bge-small-en-v1.5")
    passages.add_argument("--max-tokens", type=int, default=350)
    passages.add_argument("--overlap", type=int, default=40)
    return parser


def _build_passages(args: argparse.Namespace) -> int:
    docs = [Doc.model_validate(row) for row in read_jsonl(args.docs)]
    if not docs:
        raise SystemExit(f"no docs in {args.docs}")

    dedup_path = args.docs.parent / "dedup_log.jsonl"
    removed = (
        {row["doc_id"] for row in read_jsonl(dedup_path)}
        if dedup_path.exists()
        else set()
    )
    docs = [doc for doc in docs if doc.doc_id not in removed]

    token_offsets = _token_offsets_factory(args.tokenizer)
    passages = []
    for doc in docs:
        passages.extend(
            build_passages(
                doc,
                token_offsets,
                max_tokens=args.max_tokens,
                overlap=args.overlap,
                mode=args.mode,
            )
        )

    write_jsonl(args.out, [passage.model_dump() for passage in passages])
    summary = {
        "mode": args.mode,
        "docs": len(docs),
        "duplicates_excluded": len(removed),
        "passages": len(passages),
        "sections": dict(Counter(passage.section for passage in passages)),
        "max_tokens": args.max_tokens,
        "overlap": args.overlap,
        "tokenizer": args.tokenizer,
        "out": str(args.out),
    }
    write_json(args.out.with_suffix(args.out.suffix + ".manifest.json"), summary)
    print(json.dumps(summary, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "passages":
        return _build_passages(args)
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
