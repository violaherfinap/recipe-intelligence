from __future__ import annotations

import argparse
import json
from pathlib import Path

from recipe_qa.benchmark.validate import (
    load_passages_many,
    load_qrels,
    load_queries,
    write_jsonl,
)
from recipe_qa.eval.nli_calibration import build_probe, calibrate, threshold_grid


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Calibrate the NLI threshold on a labelled query split."
    )
    parser.add_argument("--queries", type=Path, required=True)
    parser.add_argument("--qrels", type=Path, required=True)
    parser.add_argument(
        "--passages",
        type=Path,
        nargs="+",
        default=[
            Path("data/processed/passages.jsonl"),
            Path("data/processed/passages_fixed.jsonl"),
        ],
    )
    parser.add_argument("--model", default="cross-encoder/nli-deberta-v3-base")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--negatives-per-claim", type=int, default=1)
    parser.add_argument("--start", type=float, default=0.30)
    parser.add_argument("--stop", type=float, default=0.90)
    parser.add_argument("--step", type=float, default=0.05)
    parser.add_argument("--probe-out", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--markdown", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def _markdown(report: dict, queries_path: Path) -> str:
    lines = [
        "# NLI verifier calibration",
        "",
        f"- Model: `{report['model']}`",
        f"- Query set: `{queries_path}` ({report['queries']} queries)",
        f"- Pairs: {report['pairs']} ({report['positives']} gold, "
        f"{report['negatives']} synthetic negatives)",
        f"- Selected threshold: **{report['threshold']}**",
        f"- Precision {report['precision']:.4f} · Recall {report['recall']:.4f} · "
        f"F1 {report['f1']:.4f} · Balanced accuracy {report['balanced_accuracy']:.4f}",
        "",
        "| Threshold | Precision | Recall | F1 | Balanced accuracy |",
        "| ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in report["sweep"]:
        lines.append(
            f"| {row['threshold']} | {row['precision']:.4f} | {row['recall']:.4f} | "
            f"{row['f1']:.4f} | {row['balanced_accuracy']:.4f} |"
        )
    lines.extend(
        [
            "",
            f"Caveat: {report['caveat']}.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    queries = load_queries(args.queries)
    qrels = load_qrels(args.qrels)
    passages = load_passages_many(args.passages)
    pairs = build_probe(
        queries,
        qrels,
        passages,
        seed=args.seed,
        negatives_per_claim=args.negatives_per_claim,
    )
    if not pairs:
        raise SystemExit("probe is empty; check the query set has gold passages")
    if args.probe_out:
        write_jsonl(args.probe_out, [pair.to_dict() for pair in pairs])
        print(f"probe: {args.probe_out} ({len(pairs)} pairs)")

    if args.dry_run:
        positives = sum(1 for pair in pairs if pair.label == 1)
        print(
            json.dumps(
                {
                    "queries": len(queries),
                    "pairs": len(pairs),
                    "positives": positives,
                    "negatives": len(pairs) - positives,
                },
                indent=2,
            )
        )
        return 0

    from recipe_qa.verify.nli import NliVerifier

    verifier = NliVerifier(args.model)
    scored = [
        (
            verifier.score(str(passages[pair.passage_id].get("text", "")), pair.claim).entailment,
            pair.label,
        )
        for pair in pairs
    ]
    report = calibrate(scored, threshold_grid(args.start, args.stop, args.step))
    report.update(
        {
            "model": args.model,
            "queries": len(queries),
            "queries_path": str(args.queries).replace("\\", "/"),
            "seed": args.seed,
        }
    )
    text = json.dumps(report, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
        print(f"report: {args.out}")
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(_markdown(report, args.queries), encoding="utf-8")
        print(f"markdown: {args.markdown}")
    print(
        json.dumps(
            {
                "threshold": report["threshold"],
                "precision": report["precision"],
                "recall": report["recall"],
                "f1": report["f1"],
                "balanced_accuracy": report["balanced_accuracy"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
