from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from recipe_qa.benchmark.validate import load_qrels, load_verdict_qrels
from recipe_qa.eval.agreement import AgreementReport, compare_relevance, compare_verdict


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


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    relevance = compare_relevance(load_qrels(args.qrels_c), load_qrels(args.qrels_d))
    verdict = compare_verdict(
        load_verdict_qrels(args.verdict_c),
        load_verdict_qrels(args.verdict_d),
    )

    payload = {
        "relevance": relevance.to_dict(),
        "verdict": verdict.to_dict(),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = args.out.with_name(f".{args.out.name}.tmp")
    tmp_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")
    tmp_path.replace(args.out)

    print(_summary(relevance))
    print(_summary(verdict))
    print(f"written: {args.out}")

    errors: list[str] = []
    for report in (relevance, verdict):
        if not report.complete:
            errors.append(f"{report.kind}: incomplete overlap between C and D")
        if report.kappa is None:
            errors.append(f"{report.kind}: kappa is undefined")
    if errors and not args.allow_missing:
        for error in errors:
            print(f"ERROR {error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
