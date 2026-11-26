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
    parser.add_argument(
        "--slices",
        nargs="*",
        default=None,
        help="restrict calibration to slices, e.g. easy; default uses every query",
    )
    parser.add_argument(
        "--premise-context",
        action="store_true",
        help="prepend recipe title, book, and year to the passage premise",
    )
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
        f"- Slices: `{report['slices']}`",
        f"- Premise context: `{report['premise_context']}`",
        f"- Probe pairs: {report['probe_pairs']} (all train claims)",
        f"- Calibration pairs: {report['pairs']} ({report['positives']} gold, "
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
    if report.get("per_slice"):
        lines.extend(
            [
                "",
                "## Positive coverage per slice",
                "",
                "| Slice | Positives | Mean entailment | Supported at threshold |",
                "| --- | ---: | ---: | ---: |",
            ]
        )
        for name, row in report["per_slice"].items():
            lines.append(
                f"| {name} | {row['positives']} | {row['mean_entailment']:.4f} | "
                f"{row['supported_at_threshold']}/{row['positives']} |"
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
    from recipe_qa.verify.premise import premise_text

    verifier = NliVerifier(args.model)

    def premise(passage: dict) -> str:
        return premise_text(passage) if args.premise_context else str(passage.get("text", ""))

    scored = [
        (
            verifier.score(premise(passages[pair.passage_id]), pair.claim).entailment,
            pair,
        )
        for pair in pairs
    ]
    selected = [
        (score, pair.label)
        for score, pair in scored
        if pair.label == 0 or args.slices is None or pair.slice in set(args.slices)
    ]
    report = calibrate(selected, threshold_grid(args.start, args.stop, args.step))
    per_slice = {}
    for slice_name in sorted({pair.slice for _, pair in scored}):
        positives = [score for score, pair in scored if pair.label == 1 and pair.slice == slice_name]
        if not positives:
            continue
        per_slice[slice_name] = {
            "positives": len(positives),
            "mean_entailment": sum(positives) / len(positives),
            "supported_at_threshold": sum(
                1 for score in positives if score >= report["threshold"]
            ),
        }
    report.update(
        {
            "model": args.model,
            "queries": len(queries),
            "queries_path": str(args.queries).replace("\\", "/"),
            "seed": args.seed,
            "slices": sorted(args.slices) if args.slices else "all",
            "premise_context": args.premise_context,
            "probe_pairs": len(pairs),
            "per_slice": per_slice,
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
