from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_runs(values: list[str]) -> list[dict]:
    runs = []
    for value in values:
        if "=" not in value:
            raise SystemExit(f"--runs expects name=path, got {value!r}")
        name, path = value.split("=", 1)
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        payload["name"] = name
        runs.append(payload)
    return runs


def overall_table(runs: list[dict]) -> str:
    header = (
        "| Run | n | R@5 | R@10 | nDCG@10 | MRR@10 | Doc recall | Judged | Test split | p50 ms | p95 ms |\n"
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"
    )
    lines = [header]
    for run in runs:
        metrics = run["metrics"]
        latency = run["latency_ms"]
        lines.append(
            "| {name} | {n} | {r5:.4f} | {r10:.4f} | {ndcg:.4f} | {mrr:.4f} | "
            "{doc:.4f} | {judged:.4f} | {test:.4f} | {p50:.1f} | {p95:.1f} |".format(
                name=run["name"],
                n=metrics.get("queries", 0),
                r5=metrics.get("recall@5", 0.0),
                r10=metrics.get("recall@10", 0.0),
                ndcg=metrics.get("ndcg@10", 0.0),
                mrr=metrics.get("mrr@10", 0.0),
                doc=metrics.get("doc_recall", 0.0),
                judged=metrics.get("judged_rate", 0.0),
                test=metrics.get("test_split_rate", 0.0),
                p50=latency.get("p50", 0.0),
                p95=latency.get("p95", 0.0),
            )
        )
    return "\n".join(lines)


def slice_table(run: dict, key: str) -> str:
    header = (
        "| Slice | n | R@5 | R@10 | nDCG@10 | MRR@10 | Doc recall | Test split |\n"
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"
    )
    lines = [header]
    for name, metrics in sorted(run.get("per_slice", {}).items()):
        lines.append(
            "| {name} | {n} | {r5:.4f} | {r10:.4f} | {ndcg:.4f} | {mrr:.4f} | {doc:.4f} | {test:.4f} |".format(
                name=name,
                n=metrics.get("slice_queries", 0),
                r5=metrics.get("recall@5", 0.0),
                r10=metrics.get("recall@10", 0.0),
                ndcg=metrics.get("ndcg@10", 0.0),
                mrr=metrics.get("mrr@10", 0.0),
                doc=metrics.get("doc_recall", 0.0),
                test=metrics.get("test_split_rate", 0.0),
            )
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render Markdown tables from retrieval runs.")
    parser.add_argument("--runs", action="append", required=True, metavar="NAME=PATH")
    parser.add_argument("--slices", action="append", default=[], metavar="NAME")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    runs = load_runs(args.runs)
    sections = ["## Overall", "", overall_table(runs), ""]
    by_name = {run["name"]: run for run in runs}
    for name in args.slices:
        if name not in by_name:
            raise SystemExit(f"unknown slice run {name!r}")
        sections.extend([f"## Per slice — {name}", "", slice_table(by_name[name], name), ""])

    text = "\n".join(sections)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
