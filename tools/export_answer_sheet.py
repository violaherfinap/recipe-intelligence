from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from recipe_qa.benchmark.annotation import load_pool
from recipe_qa.benchmark.answer_sheet import (
    RELEVANCE_FIELDS,
    VERDICT_FIELDS,
    apply_relevance_labels,
    build_relevance_rows,
    build_verdict_rows,
    write_sheet,
)
from recipe_qa.benchmark.validate import (
    load_passages_many,
    load_qrels,
    load_queries,
)


def _backup_existing(path: Path) -> None:
    if not path.exists():
        return
    backup = path.with_name(f"{path.name}.bak")
    shutil.copy2(path, backup)
    print(f"backup: {backup}")


def _prepare_output(path: Path, force: bool) -> bool:
    if not path.exists():
        return True
    if not force:
        print(f"ERROR output exists: {path}; use --force to overwrite")
        return False
    _backup_existing(path)
    return True


def _relevance(args: argparse.Namespace) -> int:
    out = args.out or Path("benchmark/answer_sheet_d.csv")
    if not _prepare_output(out, args.force):
        return 1
    rows = build_relevance_rows(
        queries=load_queries(args.queries),
        pool=load_pool(args.pool),
        passages=load_passages_many(args.passages),
        annotator=args.annotator,
    )
    if args.prefill is not None:
        if not args.prefill.exists():
            print(f"WARNING prefill not found: {args.prefill}; sheet left blank")
        else:
            applied = apply_relevance_labels(rows, load_qrels(args.prefill))
            print(f"prefilled: {applied} rows from {args.prefill}")
    write_sheet(out, rows, RELEVANCE_FIELDS)
    print(f"relevance rows: {len(rows)}")
    print(f"written: {out}")
    print("isi kolom relevance dengan 0, 1, atau 2; notes opsional")
    return 0


def _verdict(args: argparse.Namespace) -> int:
    out = args.out or Path("benchmark/verdict_answer_sheet_d.csv")
    if not args.qrels.exists():
        print(f"ERROR qrels not found: {args.qrels}")
        print("selesaikan relevance pass 2 dan import qrels_d.jsonl dulu")
        return 1
    if not _prepare_output(out, args.force):
        return 1
    rows = build_verdict_rows(
        queries=load_queries(args.queries),
        qrels=load_qrels(args.qrels),
        passages=load_passages_many(args.passages),
    )
    write_sheet(out, rows, VERDICT_FIELDS)
    print(f"verdict rows: {len(rows)}")
    print(f"written: {out}")
    print("isi kolom verdict dengan SUPPORTED, REFUTED, atau NOT_ENOUGH_EVIDENCE")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export CSV answer sheets for pass 2.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--queries", type=Path, default=Path("benchmark/queries.jsonl"))
    common.add_argument(
        "--passages",
        type=Path,
        nargs="+",
        default=[
            Path("data/processed/passages.jsonl"),
            Path("data/processed/passages_fixed.jsonl"),
        ],
    )
    common.add_argument("--out", type=Path, default=None)
    common.add_argument("--force", action="store_true", help="backup and overwrite an existing sheet")

    relevance = subparsers.add_parser("relevance", parents=[common])
    relevance.add_argument("--pool", type=Path, default=Path("benchmark/pool_v1.jsonl"))
    relevance.add_argument("--annotator", default="D", choices=["A", "C", "D"])
    relevance.add_argument(
        "--prefill",
        type=Path,
        default=None,
        help="copy existing labels into the sheet",
    )
    relevance.set_defaults(func=_relevance)

    verdict = subparsers.add_parser("verdict", parents=[common])
    verdict.add_argument("--qrels", type=Path, default=Path("benchmark/qrels_d.jsonl"))
    verdict.set_defaults(func=_verdict)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
