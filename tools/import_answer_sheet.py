from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from recipe_qa.benchmark.annotation import load_pool
from recipe_qa.benchmark.answer_sheet import (
    AnswerSheetReport,
    import_relevance_sheet,
    import_verdict_sheet,
)
from recipe_qa.benchmark.validate import (
    load_passages_many,
    load_queries,
    write_jsonl,
)


def _backup_existing(path: Path) -> None:
    if not path.exists():
        return
    backup = path.with_name(f"{path.name}.bak")
    shutil.copy2(path, backup)
    print(f"backup: {backup}")


def _write_jsonl_atomic(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp")
    write_jsonl(tmp_path, rows)
    tmp_path.replace(path)


def _print_report(report: AnswerSheetReport) -> None:
    print(f"rows: {report.rows}")
    print(f"queries: {report.queries}")
    print(
        "labels: "
        + ", ".join(f"{label}={count}" for label, count in report.labels.items())
    )
    if report.warnings:
        print(f"warnings: {len(report.warnings)}")
        for warning in report.warnings:
            print(f"  WARN {warning}")
    if report.errors:
        print(f"errors: {len(report.errors)}")
        for error in report.errors:
            print(f"  ERROR {error}")


def _prepare_output(path: Path, force: bool) -> bool:
    if not path.exists():
        return True
    if not force:
        print(f"ERROR output exists: {path}; use --force to overwrite")
        return False
    _backup_existing(path)
    return True


def _relevance(args: argparse.Namespace) -> int:
    out = args.out or Path("benchmark/qrels_d.jsonl")
    rows, report = import_relevance_sheet(
        sheet_path=args.input,
        pool=load_pool(args.pool),
        passages=load_passages_many(args.passages),
        doc_version=args.commit.read_text(encoding="utf-8").strip(),
        annotator=args.annotator,
    )
    _print_report(report)
    if not report.ok:
        return 1
    if args.dry_run:
        print("dry-run: no file written")
        return 0
    if not _prepare_output(out, args.force):
        return 1
    _write_jsonl_atomic(out, [row.model_dump() for row in rows])
    print(f"written: {out} ({len(rows)} rows)")
    return 0


def _verdict(args: argparse.Namespace) -> int:
    out = args.out or Path("benchmark/verdict_qrels_d.jsonl")
    rows, report = import_verdict_sheet(
        sheet_path=args.input,
        queries=load_queries(args.queries),
        annotator=args.annotator,
    )
    _print_report(report)
    if not report.ok:
        return 1
    if args.dry_run:
        print("dry-run: no file written")
        return 0
    if not _prepare_output(out, args.force):
        return 1
    _write_jsonl_atomic(out, [row.model_dump() for row in rows])
    print(f"written: {out} ({len(rows)} rows)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import and validate pass-2 answer sheets.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--input", type=Path, required=True)
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
    common.add_argument("--annotator", default="D", choices=["A", "C", "D"])
    common.add_argument("--force", action="store_true", help="backup and overwrite existing output")
    common.add_argument("--dry-run", action="store_true")

    relevance = subparsers.add_parser("relevance", parents=[common])
    relevance.add_argument("--pool", type=Path, default=Path("benchmark/pool_v1.jsonl"))
    relevance.add_argument("--commit", type=Path, default=Path("data/corpus_commit.txt"))
    relevance.set_defaults(func=_relevance)

    verdict = subparsers.add_parser("verdict", parents=[common])
    verdict.set_defaults(func=_verdict)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
