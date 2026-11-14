from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from recipe_qa.benchmark.annotation import (
    append_verdict,
    evidence_passages,
    verdict_progress,
)
from recipe_qa.benchmark.schema import Query, VerdictQrel
from recipe_qa.benchmark.validate import (
    load_passages,
    load_queries,
    load_verdict_qrels,
)
from recipe_qa.benchmark.verdict_review import (
    parse_answer_sheet,
    parse_verdict_decisions,
)

HELP_TEXT = """\
c1=s c2=n   verdict per klaim (s=SUPPORTED, r=REFUTED, n=NOT_ENOUGH_EVIDENCE)
all=s       isi semua klaim query ini dengan verdict yang sama
r           tampilkan ulang blok klaim + evidence
?           bantuan
q           keluar; query ini belum disimpan
"""


def _ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print("\nStopped. Progress has been saved.")
        raise SystemExit(130) from None


def _passage_block(passage_id: str, passage: dict) -> str:
    header = (
        f"{passage_id} | {passage['doc_id']} | {passage.get('source_title', '')} "
        f"({passage.get('source_year', '?')}) | {passage['section']}#{passage['idx']}"
    )
    return f"\n{header}\n{'-' * len(header)}\n{passage['text'].strip()}"


def _pending_claims(query: Query, done: set[tuple[str, str]]) -> list[tuple[str, str]]:
    claims = [
        (f"c{index}", claim) for index, claim in enumerate(query.gold_claims, start=1)
    ]
    return [
        (claim_id, claim)
        for claim_id, claim in claims
        if (query.query_id, claim_id) not in done
    ]


def _query_block(
    query: Query,
    pending: list[tuple[str, str]],
    evidence: list[str],
    passages: dict[str, dict],
) -> str:
    lines = [
        "=" * 78,
        f"{query.query_id} | {query.slice} | as_of={query.as_of} | scope={query.scope}",
        f"Q: {query.text}",
        "",
        "===== COPY CLAIMS =====",
    ]
    for claim_id, claim in pending:
        lines.extend(["", f"Claim {claim_id}: {claim}"])
    if evidence:
        lines.extend(["", "Evidence (relevance 2):"])
        for passage_id in evidence:
            passage = passages.get(passage_id)
            if passage is None:
                lines.extend(["", f"{passage_id}: MISSING PASSAGE"])
                continue
            lines.append(_passage_block(passage_id, passage))
    else:
        lines.extend(["", "Evidence: (none)"])
    lines.extend(["", "===== END COPY ====="])
    return "\n".join(lines)


def _show_block(
    query: Query,
    pending: list[tuple[str, str]],
    evidence: list[str],
    passages: dict[str, dict],
) -> None:
    print("\n" + _query_block(query, pending, evidence, passages))


def _ask_decisions(pending: list[tuple[str, str]]) -> dict[str, str] | str | None:
    claim_ids = [claim_id for claim_id, _ in pending]
    while True:
        answer = _ask(
            "Verdict [c1=s c2=n, all=s, r=reprint, ?=help, q=quit] > "
        )
        command = answer.lower()
        if command == "q":
            return None
        if command == "?":
            print(HELP_TEXT)
            continue
        if command in {"r", "p"}:
            return "__reprint__"
        try:
            return parse_verdict_decisions(answer, claim_ids)
        except ValueError as exc:
            print(f"invalid: {exc}")


def _load_done(path: Path) -> set[tuple[str, str]]:
    if not path.exists():
        return set()
    return {(row.query_id, row.claim_id) for row in load_verdict_qrels(path)}


def _filter_queries(args: argparse.Namespace) -> list[Query]:
    queries = load_queries(args.queries)
    if args.query_id:
        queries = [query for query in queries if query.query_id == args.query_id]
    return queries


def _pending_query_rows(
    queries: list[Query],
    done: set[tuple[str, str]],
    annotator: str,
    limit: int | None = None,
) -> list[tuple[Query, list[tuple[str, str]]]]:
    rows: list[tuple[Query, list[tuple[str, str]]]] = []
    for query in queries:
        if query.author == annotator:
            continue
        pending = _pending_claims(query, done)
        if not pending:
            continue
        if limit is not None and len(rows) >= limit:
            break
        rows.append((query, pending))
    return rows


def _review(args: argparse.Namespace) -> int:
    if not args.qrels.exists():
        print(f"qrels not found: {args.qrels}")
        return 1
    queries = _filter_queries(args)
    passages = load_passages(args.passages)
    done = _load_done(args.out)
    rows = _pending_query_rows(queries, done, args.annotator, args.limit)
    if not rows:
        print("No pending claims.")
        print(f"output: {args.out}")
        return 0

    for query, pending in rows:
        evidence = evidence_passages(query.query_id, args.qrels)
        missing = [passage_id for passage_id in evidence if passage_id not in passages]
        if missing:
            print(f"{query.query_id}: missing evidence passages: {missing}")

        while True:
            _show_block(query, pending, evidence, passages)
            decisions = _ask_decisions(pending)
            if decisions is None:
                return 0
            if decisions == "__reprint__":
                continue
            break

        note = ""
        if args.notes:
            note = _ask("Catatan untuk klaim query ini (Enter=skip) > ")

        for claim_id, _ in pending:
            append_verdict(
                args.out,
                VerdictQrel(
                    query_id=query.query_id,
                    claim_id=claim_id,
                    verdict=decisions[claim_id],
                    annotator=args.annotator,
                    notes=note,
                ),
            )
            done.add((query.query_id, claim_id))
        print(f"\nsaved: {len(pending)}")

    print(f"\nVerdict annotation finished. Queries processed: {len(rows)}")
    print(f"output: {args.out}")
    return 0


def _dump(args: argparse.Namespace) -> int:
    if not args.qrels.exists():
        print(f"qrels not found: {args.qrels}")
        return 1
    queries = _filter_queries(args)
    passages = load_passages(args.passages)
    done = _load_done(args.out)
    rows = _pending_query_rows(queries, done, args.annotator, args.limit)
    if not rows:
        print("No pending claims.")
        return 0

    total_claims = sum(len(pending) for _, pending in rows)
    header = [
        f"# Verdict {args.annotator}: {total_claims} pending claims across {len(rows)} queries",
        f"# qrels: {args.qrels}",
        f"# answer file: {args.answers}",
        "# format: q001 c1=s  |  q002 c1=s c2=n  |  q001 all=s",
        "# s=SUPPORTED, r=REFUTED, n=NOT_ENOUGH_EVIDENCE",
    ]
    blocks = [
        _query_block(query, pending, evidence_passages(query.query_id, args.qrels), passages)
        for query, pending in rows
    ]
    text = "\n\n".join(["\n".join(header), *blocks]) + "\n"
    args.dump_out.parent.mkdir(parents=True, exist_ok=True)
    args.dump_out.write_text(text, encoding="utf-8")
    print(f"written: {args.dump_out} ({total_claims} claims, {len(rows)} queries)")
    return 0


def _fill(args: argparse.Namespace) -> int:
    if not args.answers.exists():
        print(f"answers not found: {args.answers}")
        return 1
    queries = _filter_queries(args)
    done = _load_done(args.out)
    pending_rows = _pending_query_rows(queries, done, args.annotator, args.limit)
    if not pending_rows:
        print("No pending claims.")
        return 0

    claim_ids_by_query = {
        query.query_id: [claim_id for claim_id, _ in pending]
        for query, pending in pending_rows
    }
    try:
        answers = parse_answer_sheet(
            args.answers.read_text(encoding="utf-8"),
            claim_ids_by_query,
        )
    except ValueError as exc:
        print(f"invalid answer sheet: {exc}")
        return 1

    missing = [
        query.query_id for query, _ in pending_rows if query.query_id not in answers
    ]
    if missing:
        print(f"missing answers: {len(missing)} queries")
        print(" ".join(missing[:20]))
        return 1

    rows: list[VerdictQrel] = []
    for query, pending in pending_rows:
        for claim_id, _ in pending:
            rows.append(
                VerdictQrel(
                    query_id=query.query_id,
                    claim_id=claim_id,
                    verdict=answers[query.query_id][claim_id],
                    annotator=args.annotator,
                )
            )

    labels = Counter(row.verdict for row in rows)
    rendered = ", ".join(
        f"{label}={labels.get(label, 0)}"
        for label in ("SUPPORTED", "REFUTED", "NOT_ENOUGH_EVIDENCE")
    )
    if args.dry_run:
        print(f"would write: {len(rows)} claims across {len(pending_rows)} queries")
        print(f"labels: {rendered}")
        return 0

    for row in rows:
        append_verdict(args.out, row)
    print(f"written: {len(rows)} claims across {len(pending_rows)} queries")
    print(f"labels: {rendered}")
    print(f"output: {args.out}")
    return 0


def _status(args: argparse.Namespace) -> int:
    queries = _filter_queries(args)
    if args.limit is not None:
        queries = queries[: args.limit]
    progress = verdict_progress(queries, args.out)
    total_done = sum(done for done, _ in progress.values())
    total = sum(total for _, total in progress.values())
    print(f"claims: {total_done}/{total}")
    print(f"remaining: {total - total_done}")

    incomplete = [query_id for query_id, (done, total) in progress.items() if done < total]
    print(f"queries incomplete: {len(incomplete)}")
    if incomplete:
        print(" ".join(incomplete[:20]))

    if args.out.exists():
        labels = Counter(row.verdict for row in load_verdict_qrels(args.out))
        rendered = ", ".join(f"{label}={labels.get(label, 0)}" for label in (
            "SUPPORTED",
            "REFUTED",
            "NOT_ENOUGH_EVIDENCE",
        ))
        print(f"labels: {rendered}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Batch-review claim verdicts.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--annotator", required=True, choices=["C", "D"])
    common.add_argument("--queries", type=Path, default=Path("benchmark/queries.jsonl"))
    common.add_argument("--passages", type=Path, default=Path("data/processed/passages.jsonl"))
    common.add_argument("--qrels", type=Path, default=None)
    common.add_argument("--out", type=Path, default=None)
    common.add_argument("--query-id", default=None)
    common.add_argument("--limit", type=int, default=None)

    review = subparsers.add_parser("review", parents=[common])
    review.add_argument("--notes", action="store_true")
    review.set_defaults(func=_review)

    dump = subparsers.add_parser("dump", parents=[common])
    dump.add_argument("--dump-out", type=Path, default=None)
    dump.add_argument("--answers", type=Path, default=None)
    dump.set_defaults(func=_dump)

    fill = subparsers.add_parser("fill", parents=[common])
    fill.add_argument("--answers", type=Path, default=None)
    fill.add_argument("--dry-run", action="store_true")
    fill.set_defaults(func=_fill)

    status = subparsers.add_parser("status", parents=[common])
    status.set_defaults(func=_status)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    annotator = args.annotator.lower()
    if args.out is None:
        args.out = Path(f"benchmark/verdict_qrels_{annotator}.jsonl")
    if args.qrels is None:
        args.qrels = Path(f"benchmark/qrels_{annotator}.jsonl")
    if hasattr(args, "answers") and args.answers is None:
        args.answers = Path(f"benchmark/verdict_{annotator}_answers.txt")
    if hasattr(args, "dump_out") and args.dump_out is None:
        args.dump_out = Path(f"benchmark/verdict_{annotator}_prompt.txt")
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
