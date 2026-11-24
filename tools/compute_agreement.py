from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from recipe_qa.benchmark.validate import load_qrels, load_verdict_qrels, read_jsonl
from recipe_qa.eval.agreement import (
    AgreementReport,
    compare_relevance,
    compare_verdict,
    fleiss_kappa,
)


def _summary(report: AgreementReport) -> str:
    kappa = "undefined" if report.kappa is None else f"{report.kappa:.4f}"
    observed = "n/a" if report.observed is None else f"{report.observed:.4f}"
    return (
        f"{report.kind}: n={report.n} kappa={kappa} observed={observed} "
        f"conflicts={len(report.disagreements)} only_c={len(report.only_c)} "
        f"only_d={len(report.only_d)}"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compute C/D inter-annotator agreement.")
    parser.add_argument("--qrels-c", type=Path, default=Path("benchmark/qrels_c.jsonl"))
    parser.add_argument("--qrels-d", type=Path, default=Path("benchmark/qrels_d.jsonl"))
    parser.add_argument(
        "--qrels-a",
        type=Path,
        default=None,
        help="optional third annotator; enables Fleiss kappa",
    )
    parser.add_argument(
        "--keys",
        type=Path,
        default=None,
        help="optional JSONL keys restricting the agreement population",
    )
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
    parser.add_argument("--out", type=Path, default=Path("benchmark/kappa.json"))
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="write the report even when one annotator has unjudged items",
    )
    return parser


def _filter_qrels(rows, keys: set[tuple[str, str]]):
    return [row for row in rows if (row.query_id, row.passage_id) in keys]


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    keys = None
    if args.keys is not None:
        keys = {
            (row["query_id"], row["passage_id"]) for row in read_jsonl(args.keys)
        }

    rows_c = load_qrels(args.qrels_c)
    rows_d = load_qrels(args.qrels_d)
    if keys is not None:
        rows_c = _filter_qrels(rows_c, keys)
        rows_d = _filter_qrels(rows_d, keys)

    relevance = compare_relevance(rows_c, rows_d)
    verdict = compare_verdict(
        load_verdict_qrels(args.verdict_c),
        load_verdict_qrels(args.verdict_d),
    )

    payload = {
        "relevance": relevance.to_dict(),
        "verdict": verdict.to_dict(),
    }

    fleiss = None
    missing_a: list[tuple[str, str]] = []
    if args.qrels_a is not None:
        rows_a = load_qrels(args.qrels_a)
        if keys is None:
            keys = {(row.query_id, row.passage_id) for row in rows_a}
            rows_c = _filter_qrels(rows_c, keys)
            rows_d = _filter_qrels(rows_d, keys)
            relevance = compare_relevance(rows_c, rows_d)
            payload["relevance"] = relevance.to_dict()
        rows_a = _filter_qrels(rows_a, keys)

        index_a = {(row.query_id, row.passage_id): row for row in rows_a}
        index_c = {(row.query_id, row.passage_id): row for row in rows_c}
        index_d = {(row.query_id, row.passage_id): row for row in rows_d}
        missing_a = sorted(keys - index_a.keys())
        missing_c = sorted(keys - index_c.keys())
        missing_d = sorted(keys - index_d.keys())
        complete = sorted(
            key for key in keys if key in index_a and key in index_c and key in index_d
        )
        fleiss = fleiss_kappa(
            [
                [
                    index_a[key].relevance,
                    index_c[key].relevance,
                    index_d[key].relevance,
                ]
                for key in complete
            ]
        )
        payload["relevance_fleiss"] = {
            "n": fleiss.n,
            "observed": fleiss.observed,
            "expected": fleiss.expected,
            "kappa": fleiss.kappa,
            "labels": fleiss.labels,
            "missing_a": [list(key) for key in missing_a],
            "missing_c": [list(key) for key in missing_c],
            "missing_d": [list(key) for key in missing_d],
        }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = args.out.with_name(f".{args.out.name}.tmp")
    tmp_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")
    tmp_path.replace(args.out)

    print(_summary(relevance))
    if fleiss is not None:
        kappa = "undefined" if fleiss.kappa is None else f"{fleiss.kappa:.4f}"
        observed = "n/a" if fleiss.observed is None else f"{fleiss.observed:.4f}"
        print(
            f"relevance_fleiss: n={fleiss.n} kappa={kappa} observed={observed} "
            f"missing_a={len(missing_a)}"
        )
    print(_summary(verdict))
    print(f"written: {args.out}")

    errors: list[str] = []
    for report in (relevance, verdict):
        if not report.complete:
            errors.append(f"{report.kind}: incomplete overlap")
        if report.kappa is None:
            errors.append(f"{report.kind}: kappa is undefined")
    if fleiss is not None:
        if missing_a:
            errors.append(f"relevance_fleiss: {len(missing_a)} items missing A labels")
        if fleiss.kappa is None:
            errors.append("relevance_fleiss: kappa is undefined")
    if errors and not args.allow_missing:
        for error in errors:
            print(f"ERROR {error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
