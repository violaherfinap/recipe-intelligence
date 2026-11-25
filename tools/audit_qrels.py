"""Reproduce the v1.1 audit population and compare audit labels with final qrels.

The audit population is every item where at least one of the two annotators gave
a non-zero label: those are the items that move Recall@10. Items both annotators
called 0 are not re-read.

Usage:
    uv run python tools/audit_qrels.py worklist
    uv run python tools/audit_qrels.py compare
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

BENCH = Path("benchmark")


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load_relevance(path: Path) -> dict[tuple[str, str], int]:
    return {(row["query_id"], row["passage_id"]): int(row["relevance"]) for row in read_jsonl(path)}


def population(
    labels_c: dict[tuple[str, str], int],
    labels_d: dict[tuple[str, str], int],
) -> list[tuple[str, str]]:
    """Items where at least one annotator gave >= 1, sorted deterministically."""
    return sorted(
        key
        for key in set(labels_c) | set(labels_d)
        if labels_c.get(key, 0) >= 1 or labels_d.get(key, 0) >= 1
    )


def compare(
    audit_rows: list[dict],
    labels_c: dict[tuple[str, str], int],
    labels_d: dict[tuple[str, str], int],
    final: dict[tuple[str, str], int],
) -> dict:
    """Compare audit labels against the current final qrels."""
    missing = [
        row
        for row in audit_rows
        if (row["query_id"], row["passage_id"]) not in final
    ]
    stale = [
        row
        for row in audit_rows
        if (row["query_id"], row["passage_id"]) in final
        and row["audit_label"] != final[(row["query_id"], row["passage_id"])]
    ]
    applied = [
        row
        for row in audit_rows
        if row["label_v1_0"] != row["audit_label"]
    ]
    return {
        "population_expected": len(population(labels_c, labels_d)),
        "population_audited": len(audit_rows),
        "confirm": sum(1 for row in audit_rows if row["result"] == "confirm"),
        "change": sum(1 for row in audit_rows if row["result"] == "change"),
        "applied_changes": applied,
        "audit_vs_final_mismatch": stale,
        "missing_from_qrels": missing,
    }


def _cmd_compare(args: argparse.Namespace) -> int:
    labels_c = load_relevance(BENCH / "qrels_c.jsonl")
    labels_d = load_relevance(BENCH / "qrels_d.jsonl")
    final = load_relevance(BENCH / "qrels.jsonl")
    audit_rows = read_jsonl(args.audit)
    report = compare(audit_rows, labels_c, labels_d, final)

    print(f"population expected : {report['population_expected']}")
    print(f"population audited  : {report['population_audited']}")
    print(f"confirm             : {report['confirm']}")
    print(f"change              : {report['change']}")
    print("applied changes:")
    for row in report["applied_changes"]:
        print(
            f"  {row['query_id']} {row['passage_id']}: "
            f"{row['label_v1_0']} -> {row['audit_label']}"
        )
    print(f"audit vs final mismatch: {len(report['audit_vs_final_mismatch'])}")
    for row in report["audit_vs_final_mismatch"]:
        print(f"  {row['query_id']} {row['passage_id']}")
    if report["missing_from_qrels"]:
        print(f"missing from qrels: {len(report['missing_from_qrels'])}")
        return 1
    if report["audit_vs_final_mismatch"]:
        return 1
    return 0


def _cmd_worklist(args: argparse.Namespace) -> int:
    queries = {row["query_id"]: row for row in read_jsonl(BENCH / "queries.jsonl")}
    passages = {row["passage_id"]: row for row in read_jsonl(args.passages)}
    labels_c = load_relevance(BENCH / "qrels_c.jsonl")
    labels_d = load_relevance(BENCH / "qrels_d.jsonl")

    current = None
    for query_id, passage_id in population(labels_c, labels_d):
        if query_id != current:
            current = query_id
            query = queries[query_id]
            print(f"\n===== {query_id} [{query['slice']}] {query['text']}")
            for index, claim in enumerate(query["gold_claims"], start=1):
                print(f"  c{index}: {claim}")
        passage = passages[passage_id]
        print(f"-- {passage_id} | {passage.get('source_year')} | {passage['section']}")
        print("   " + passage["text"].strip().replace("\n", " / "))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    worklist = sub.add_parser("worklist", help="print the audit population without labels")
    worklist.add_argument("--passages", type=Path, default=Path("data/processed/passages.jsonl"))
    worklist.set_defaults(func=_cmd_worklist)

    compare_cmd = sub.add_parser("compare", help="compare audit labels with final qrels")
    compare_cmd.add_argument("--audit", type=Path, default=BENCH / "audit_v1_1.jsonl")
    compare_cmd.set_defaults(func=_cmd_compare)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
