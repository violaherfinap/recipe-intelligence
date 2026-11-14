from __future__ import annotations

import argparse
import sys
from pathlib import Path

from recipe_qa.benchmark.finalize import merge_qrel_rows, validate_final_qrels
from recipe_qa.benchmark.validate import (
    load_passages,
    load_queries,
    read_jsonl,
    write_jsonl,
)


def _keys(rows: list[dict]) -> set[tuple[str, str]]:
    return {(row["query_id"], row["passage_id"]) for row in rows}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Merge and validate final pass-1 qrels.")
    parser.add_argument(
        "--manual",
        type=Path,
        default=Path("benchmark/qrels_c_pass1_2026-11-14.jsonl"),
    )
    parser.add_argument(
        "--reviewed", type=Path, default=Path("benchmark/qrels_c_reviewed.jsonl")
    )
    parser.add_argument("--draft", type=Path, default=Path("benchmark/qrels_c_draft.jsonl"))
    parser.add_argument("--pool", type=Path, default=Path("benchmark/pool_v1.jsonl"))
    parser.add_argument("--queries", type=Path, default=Path("benchmark/queries.jsonl"))
    parser.add_argument("--passages", type=Path, default=Path("data/processed/passages.jsonl"))
    parser.add_argument("--commit", type=Path, default=Path("data/corpus_commit.txt"))
    parser.add_argument(
        "--backup",
        type=Path,
        default=Path("benchmark/qrels_c_pass1_2026-11-14.jsonl"),
    )
    parser.add_argument("--out", type=Path, default=Path("benchmark/qrels_c.jsonl"))
    parser.add_argument("--annotator", default="C")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    manual_rows = read_jsonl(args.manual)
    reviewed_rows = read_jsonl(args.reviewed)
    draft_rows = read_jsonl(args.draft)
    pool_rows = read_jsonl(args.pool)
    queries = load_queries(args.queries)
    passages = load_passages(args.passages)
    doc_version = args.commit.read_text(encoding="utf-8").strip()

    report = validate_final_qrels(
        manual_rows=manual_rows,
        reviewed_rows=reviewed_rows,
        draft_rows=draft_rows,
        pool_rows=pool_rows,
        queries=queries,
        passages=passages,
        doc_version=doc_version,
        annotator=args.annotator,
    )

    if args.out.exists():
        if not args.backup.exists():
            report.errors.append(f"backup missing before overwrite: {args.backup}")
        else:
            backup_rows = read_jsonl(args.backup)
            print(f"backup: {args.backup} ({len(backup_rows)} rows)")
            if _keys(backup_rows) != _keys(manual_rows):
                report.errors.append("backup keys do not match manual qrels")

    labels = ", ".join(f"{label}={count}" for label, count in report.labels.items())
    print(f"manual: {report.manual}")
    print(f"reviewed: {report.reviewed}")
    print(f"merged: {report.merged}")
    print(f"queries: {report.queries}")
    print(f"labels: {labels}")
    print(f"overrides: {report.overrides}")
    if report.warnings:
        print(f"warnings: {len(report.warnings)}")
        for warning in report.warnings:
            print(f"  WARN {warning}")
    if report.errors:
        print(f"errors: {len(report.errors)}")
        for error in report.errors:
            print(f"  ERROR {error}")
        return 1

    if args.dry_run:
        print("dry-run: no file written")
        return 0

    merged_rows = merge_qrel_rows(manual_rows, reviewed_rows)
    tmp_path = args.out.with_name(f".{args.out.name}.tmp")
    write_jsonl(tmp_path, merged_rows)
    tmp_path.replace(args.out)
    print(f"written: {args.out} ({len(merged_rows)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
