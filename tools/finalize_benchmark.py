from __future__ import annotations

import argparse
import sys
from pathlib import Path

from recipe_qa.benchmark.adjudication import (
    build_final_benchmark,
    load_decisions,
    split_doc_ids,
    write_jsonl_atomic,
    write_manifest,
    write_test_docs,
)
from recipe_qa.benchmark.validate import (
    load_passages_many,
    load_qrels,
    load_queries,
    load_verdict_qrels,
    read_jsonl,
)


def _format_kappa(value: float | None) -> str:
    return "undefined" if value is None else f"{value:.4f}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Apply adjudication decisions and freeze the final benchmark."
    )
    parser.add_argument("--qrels-a", type=Path, default=None)
    parser.add_argument("--qrels-c", type=Path, default=Path("benchmark/qrels_c.jsonl"))
    parser.add_argument("--qrels-d", type=Path, default=Path("benchmark/qrels_d.jsonl"))
    parser.add_argument("--a-keys", type=Path, default=None)
    parser.add_argument(
        "--verdict-c",
        type=Path,
        default=Path("benchmark/verdict_qrels_c.jsonl"),
    )
    parser.add_argument(
        "--verdict-d",
        type=Path,
        default=Path("benchmark/verdict_qrels_d.jsonl"),
    )
    parser.add_argument(
        "--decisions",
        type=Path,
        default=Path("benchmark/adjudication.jsonl"),
    )
    parser.add_argument("--queries", type=Path, default=Path("benchmark/queries.jsonl"))
    parser.add_argument(
        "--passages",
        type=Path,
        nargs="+",
        default=[
            Path("data/processed/passages.jsonl"),
            Path("data/processed/passages_fixed.jsonl"),
        ],
    )
    parser.add_argument("--pool", type=Path, default=Path("benchmark/pool_v1.jsonl"))
    parser.add_argument("--commit", type=Path, default=Path("data/corpus_commit.txt"))
    parser.add_argument("--out-qrels", type=Path, default=Path("benchmark/qrels.jsonl"))
    parser.add_argument(
        "--out-verdict",
        type=Path,
        default=Path("benchmark/verdict_qrels.jsonl"),
    )
    parser.add_argument("--test-docs", type=Path, default=Path("benchmark/test_docs.txt"))
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("benchmark/manifest.sha256"),
    )
    parser.add_argument("--annotator", default="D")
    parser.add_argument("--allow-missing", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    passages = load_passages_many(args.passages)
    required_a_keys = None
    if args.a_keys is not None:
        required_a_keys = {
            (row["query_id"], row["passage_id"]) for row in read_jsonl(args.a_keys)
        }
    report = build_final_benchmark(
        rows_qrels_c=load_qrels(args.qrels_c),
        rows_qrels_d=load_qrels(args.qrels_d),
        rows_verdict_c=load_verdict_qrels(args.verdict_c),
        rows_verdict_d=load_verdict_qrels(args.verdict_d),
        pool_rows=read_jsonl(args.pool),
        queries=load_queries(args.queries),
        passages=passages,
        doc_version=args.commit.read_text(encoding="utf-8").strip(),
        decisions=load_decisions(args.decisions),
        annotator=args.annotator,
        allow_missing=args.allow_missing,
        rows_qrels_a=load_qrels(args.qrels_a) if args.qrels_a is not None else None,
        required_a_keys=required_a_keys,
    )

    if report.relevance is not None:
        print(
            f"relevance: n={report.relevance.n} "
            f"kappa={_format_kappa(report.relevance.kappa)} "
            f"conflicts={len(report.relevance.disagreements)} "
            f"only_c={len(report.relevance.only_c)} only_d={len(report.relevance.only_d)}"
        )
    if report.verdict is not None:
        print(
            f"verdict: n={report.verdict.n} "
            f"kappa={_format_kappa(report.verdict.kappa)} "
            f"conflicts={len(report.verdict.disagreements)} "
            f"only_c={len(report.verdict.only_c)} only_d={len(report.verdict.only_d)}"
        )
    print(f"final: qrels={len(report.qrels)} verdicts={len(report.verdicts)}")
    print(
        f"resolved: {report.resolved}/{report.conflicts} "
        f"ties={report.ties} majority={report.majority}"
    )
    print(
        f"missing: A={report.missing_a} C={report.missing_c} D={report.missing_d}"
    )
    print(
        "relevance labels: "
        + ", ".join(f"{label}={count}" for label, count in report.relevance_labels.items())
    )
    print(
        "verdict labels: "
        + ", ".join(f"{label}={count}" for label, count in report.verdict_labels.items())
    )
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

    write_jsonl_atomic(args.out_qrels, [row.model_dump() for row in report.qrels])
    write_jsonl_atomic(args.out_verdict, [row.model_dump() for row in report.verdicts])
    write_test_docs(args.test_docs, split_doc_ids(passages))
    manifest_lines = write_manifest(
        args.manifest,
        [args.queries, args.out_qrels, args.out_verdict, args.test_docs],
        base=Path("."),
    )
    print(f"written: {args.out_qrels} ({len(report.qrels)} rows)")
    print(f"written: {args.out_verdict} ({len(report.verdicts)} rows)")
    print(f"written: {args.test_docs}")
    print(f"written: {args.manifest} ({len(manifest_lines)} entries)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
