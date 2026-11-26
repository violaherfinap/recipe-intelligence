"""Calibrate the sufficiency threshold on a labelled dev run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from recipe_qa.eval.sufficiency_calibration import (
    answerable_labels,
    calibrate,
    extract_scores,
)


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Calibrate sufficiency threshold.")
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--qrels", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--step", type=float, default=0.01)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    results = read_jsonl(args.results)
    qrels = read_jsonl(args.qrels)
    labels = answerable_labels(qrels)
    scored = extract_scores(results)
    report = calibrate(scored, labels, step=args.step)
    text = json.dumps(report, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
