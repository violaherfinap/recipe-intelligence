from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from recipe_qa.benchmark.adjudication import load_decisions
from recipe_qa.benchmark.validate import load_passages, load_qrels, load_queries, load_verdict_qrels
from recipe_qa.eval.agreement import (
    AgreementReport,
    Disagreement,
    compare_relevance,
    compare_verdict,
)


def _ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print("\nStopped. Decisions have been saved.")
        raise SystemExit(130) from None


def _show_passage(passage: dict) -> None:
    header = (
        f"{passage['doc_id']} | {passage.get('source_title', '')} "
        f"({passage.get('source_year', '?')}) | {passage['section']}#{passage['idx']}"
    )
    print(f"\n{header}")
    print("-" * len(header))
    print(passage["text"].strip())


def _reports(args: argparse.Namespace) -> list[AgreementReport]:
    reports: list[AgreementReport] = []
    if args.kind in {"all", "relevance"}:
        reports.append(
            compare_relevance(load_qrels(args.qrels_c), load_qrels(args.qrels_d))
        )
    if args.kind in {"all", "verdict"}:
        reports.append(
            compare_verdict(
                load_verdict_qrels(args.verdict_c),
                load_verdict_qrels(args.verdict_d),
            )
        )
    return reports


def _conflict_rows(reports: list[AgreementReport]) -> list[dict]:
    rows: list[dict] = []
    for report in reports:
        for conflict in report.disagreements:
            row = {
                "kind": report.kind,
                "query_id": conflict.query_id,
                "item_id": conflict.item_id,
                "label_c": conflict.label_c,
                "label_d": conflict.label_d,
            }
            rows.append(row)
    return rows


def _append_decision(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(row, ensure_ascii=False) + "\n"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line)
        handle.flush()
        os.fsync(handle.fileno())


def _show_relevance(
    conflict: Disagreement,
    queries: dict,
    passages: dict[str, dict],
) -> None:
    query = queries.get(conflict.query_id)
    print("\n" + "=" * 78)
    print(f"RELEVANCE {conflict.query_id} | {conflict.item_id}")
    if query is not None:
        print(f"Q: {query.text}")
    print(f"C={conflict.label_c} D={conflict.label_d}")
    passage = passages.get(conflict.item_id)
    if passage is not None:
        _show_passage(passage)


def _show_verdict(
    conflict: Disagreement,
    queries: dict,
    passages: dict[str, dict],
    qrels_path: Path,
) -> None:
    query = queries.get(conflict.query_id)
    print("\n" + "=" * 78)
    print(f"VERDICT {conflict.query_id}/{conflict.item_id}")
    if query is not None:
        print(f"Q: {query.text}")
        try:
            claim_index = int(conflict.item_id.removeprefix("c")) - 1
            print(f"Claim: {query.gold_claims[claim_index]}")
        except (ValueError, IndexError):
            pass
    print(f"C={conflict.label_c} D={conflict.label_d}")

    if not qrels_path.exists():
        return
    evidence = [row for row in load_qrels(qrels_path) if row.query_id == conflict.query_id]
    for row in sorted(evidence, key=lambda item: (-item.relevance, item.passage_id)):
        if row.relevance < 2:
            continue
        passage = passages.get(row.passage_id)
        if passage is not None:
            _show_passage(passage)


def _review_relevance(
    conflicts: list[Disagreement],
    args: argparse.Namespace,
    queries: dict,
    passages: dict[str, dict],
    decisions: dict,
) -> None:
    for conflict in conflicts:
        key = ("relevance", conflict.query_id, conflict.item_id)
        if key in decisions:
            continue
        _show_relevance(conflict, queries, passages)
        note = ""
        while True:
            answer = _ask("final [0/1/2], c=use C, d=use D, n=note, k=skip, q=quit > ").lower()
            if answer == "q":
                return
            if answer == "k":
                break
            if answer == "n":
                note = _ask("note > ")
                continue
            if answer == "c":
                answer = conflict.label_c
            elif answer == "d":
                answer = conflict.label_d
            if answer in {"0", "1", "2"}:
                _append_decision(
                    args.decisions,
                    {
                        "kind": "relevance",
                        "query_id": conflict.query_id,
                        "item_id": conflict.item_id,
                        "label_c": conflict.label_c,
                        "label_d": conflict.label_d,
                        "final": int(answer),
                        "notes": note,
                    },
                )
                decisions[key] = True
                break
            print("enter 0, 1, 2, c, d, n, k, or q")


def _review_verdict(
    conflicts: list[Disagreement],
    args: argparse.Namespace,
    queries: dict,
    passages: dict[str, dict],
    decisions: dict,
) -> None:
    mapping = {"s": "SUPPORTED", "r": "REFUTED", "e": "NOT_ENOUGH_EVIDENCE"}
    for conflict in conflicts:
        key = ("verdict", conflict.query_id, conflict.item_id)
        if key in decisions:
            continue
        _show_verdict(conflict, queries, passages, args.qrels)
        note = ""
        while True:
            answer = _ask(
                "final [s/r/e], c=use C, d=use D, n=note, k=skip, q=quit > "
            ).lower()
            if answer == "q":
                return
            if answer == "k":
                break
            if answer == "n":
                note = _ask("note > ")
                continue
            if answer == "c":
                answer = conflict.label_c
            elif answer == "d":
                answer = conflict.label_d
            final = mapping.get(answer, answer)
            if final in {"SUPPORTED", "REFUTED", "NOT_ENOUGH_EVIDENCE"}:
                _append_decision(
                    args.decisions,
                    {
                        "kind": "verdict",
                        "query_id": conflict.query_id,
                        "item_id": conflict.item_id,
                        "label_c": conflict.label_c,
                        "label_d": conflict.label_d,
                        "final": final,
                        "notes": note,
                    },
                )
                decisions[key] = True
                break
            print("enter s, r, e, c, d, n, k, or q")


def _conflicts_subcommand(args: argparse.Namespace) -> int:
    reports = _reports(args)
    rows = _conflict_rows(reports)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = args.out.with_name(f".{args.out.name}.tmp")
    with tmp_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    tmp_path.replace(args.out)
    for report in reports:
        print(
            f"{report.kind}: conflicts={len(report.disagreements)} "
            f"only_c={len(report.only_c)} only_d={len(report.only_d)}"
        )
    print(f"written: {args.out} ({len(rows)} conflicts)")
    return 0


def _review_subcommand(args: argparse.Namespace) -> int:
    reports = _reports(args)
    items = [
        (report.kind, conflict)
        for report in reports
        for conflict in report.disagreements
    ]
    if args.query_id:
        items = [item for item in items if item[1].query_id == args.query_id]
    if args.limit is not None:
        items = items[: args.limit]

    queries = {query.query_id: query for query in load_queries(args.queries)}
    passages = load_passages(args.passages)
    decisions = load_decisions(args.decisions)

    for report in reports:
        if report.only_c or report.only_d:
            print(
                f"WARNING {report.kind}: only_c={len(report.only_c)} "
                f"only_d={len(report.only_d)}; run status before finalizing"
            )

    relevance = [conflict for kind, conflict in items if kind == "relevance"]
    verdict = [conflict for kind, conflict in items if kind == "verdict"]
    _review_relevance(relevance, args, queries, passages, decisions)
    _review_verdict(verdict, args, queries, passages, decisions)
    print(f"decisions saved: {args.decisions}")
    return 0


def _status_subcommand(args: argparse.Namespace) -> int:
    reports = _reports(args)
    decisions = load_decisions(args.decisions)
    print(f"decisions: {len(decisions)}")
    for report in reports:
        open_conflicts = [
            conflict
            for conflict in report.disagreements
            if (report.kind, conflict.query_id, conflict.item_id) not in decisions
        ]
        print(
            f"{report.kind}: conflicts={len(report.disagreements)} "
            f"open={len(open_conflicts)} only_c={len(report.only_c)} only_d={len(report.only_d)}"
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="List and resolve C/D annotation conflicts.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--kind", choices=["all", "relevance", "verdict"], default="all")
    common.add_argument("--qrels-c", type=Path, default=Path("benchmark/qrels_c.jsonl"))
    common.add_argument("--qrels-d", type=Path, default=Path("benchmark/qrels_d.jsonl"))
    common.add_argument(
        "--verdict-c",
        type=Path,
        default=Path("benchmark/verdict_qrels_c.jsonl"),
    )
    common.add_argument(
        "--verdict-d",
        type=Path,
        default=Path("benchmark/verdict_qrels_d.jsonl"),
    )
    common.add_argument(
        "--decisions",
        type=Path,
        default=Path("benchmark/adjudication.jsonl"),
    )

    conflicts = subparsers.add_parser("list", parents=[common])
    conflicts.add_argument("--out", type=Path, default=Path("benchmark/conflicts.jsonl"))
    conflicts.set_defaults(func=_conflicts_subcommand)

    review = subparsers.add_parser("review", parents=[common])
    review.add_argument("--queries", type=Path, default=Path("benchmark/queries.jsonl"))
    review.add_argument("--passages", type=Path, default=Path("data/processed/passages.jsonl"))
    review.add_argument("--qrels", type=Path, default=Path("benchmark/qrels_d.jsonl"))
    review.add_argument("--query-id", default=None)
    review.add_argument("--limit", type=int, default=None)
    review.set_defaults(func=_review_subcommand)

    status = subparsers.add_parser("status", parents=[common])
    status.set_defaults(func=_status_subcommand)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
