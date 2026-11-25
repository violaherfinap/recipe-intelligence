from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from recipe_qa.benchmark.annotation import JudgmentKey, append_qrel
from recipe_qa.benchmark.review import (
    DECISION_ACCEPT,
    DECISION_SKIP,
    combine_review_notes,
    parse_decisions,
    reviewed_progress,
)
from recipe_qa.benchmark.schema import Qrel
from recipe_qa.benchmark.validate import load_passages_many, load_qrels, load_queries

HELP_TEXT = """\
a / accept   setujui label draft
0 / 1 / 2    override label
s / skip     lewati kandidat ini
all          accept semua kandidat (dengan konfirmasi)
r            tampilkan ulang tabel review
p            tampilkan ulang semua kandidat
?            bantuan
q            keluar; query ini belum disimpan
"""


def _ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print("\nStopped. Progress has been saved.")
        raise SystemExit(130) from None


def _show_passage(passage: dict) -> None:
    header = (
        f"{passage['doc_id']} | {passage.get('source_title', '')} "
        f"({passage.get('source_year', '?')}) | {passage['section']}#{passage['idx']}"
    )
    print(f"\n{header}")
    print("-" * len(header))
    print(passage["text"].strip())


def _load_draft(path: Path, query_id: str | None) -> list[Qrel]:
    rows = load_qrels(path)
    if query_id is not None:
        rows = [row for row in rows if row.query_id == query_id]
    return rows


def _group_by_query(rows: list[Qrel]) -> dict[str, list[Qrel]]:
    grouped: dict[str, list[Qrel]] = {}
    for row in rows:
        grouped.setdefault(row.query_id, []).append(row)
    return grouped


def _query_header(
    query_id: str,
    query,
    progress: dict[str, tuple[int, int]],
) -> None:
    done, total = progress[query_id]
    print("\n" + "=" * 78)
    if query is not None:
        print(f"{query.query_id} | {query.slice} | as_of={query.as_of} | scope={query.scope}")
        print(f"Q: {query.text}")
    else:
        print(f"{query_id} | (query metadata not found)")
    print(f"reviewed: {done}/{total}")


def _show_candidates(
    query_id: str,
    query,
    query_rows: list[Qrel],
    display_rows: list[Qrel],
    passages: dict,
    progress: dict[str, tuple[int, int]],
) -> None:
    _query_header(query_id, query, progress)
    print("\n===== COPY CANDIDATES =====")
    ordinals = {JudgmentKey(row.query_id, row.passage_id): index for index, row in enumerate(query_rows, 1)}
    total = len(query_rows)
    for row in display_rows:
        ordinal = ordinals[JudgmentKey(row.query_id, row.passage_id)]
        passage = passages[row.passage_id]
        print(f"\n[{ordinal}/{total}] {row.passage_id}")
        _show_passage(passage)
        print(f"draft: {row.relevance} | note: {row.notes or '-'}")
    print("\n===== END COPY =====")


def _show_review_table(
    query_id: str,
    query_rows: list[Qrel],
    display_rows: list[Qrel],
) -> dict[JudgmentKey, int]:
    ordinals = {JudgmentKey(row.query_id, row.passage_id): index for index, row in enumerate(query_rows, 1)}
    print(f"\nREVIEW {query_id} — {len(display_rows)} kandidat")
    print(" #   draft  passage")
    for row in display_rows:
        ordinal = ordinals[JudgmentKey(row.query_id, row.passage_id)]
        print(f"{ordinal:>2}   {row.relevance}      {row.passage_id}")
    return ordinals


def _ask_decisions(count: int) -> list[str] | None:
    while True:
        answer = _ask(
            "Keputusan [a=accept, 0/1/2=override, s=skip, all=accept semua, "
            "r=tabel, p=kandidat, ?=bantuan, q=quit] > "
        )
        command = answer.lower()
        if command == "q":
            return None
        if command == "?":
            print(HELP_TEXT)
            continue
        if command == "r":
            return ["__reprint_table__"]
        if command == "p":
            return ["__reprint_candidates__"]
        if command == "all":
            confirm = _ask(f"Accept semua {count} kandidat? [y/N] > ").lower()
            if confirm in {"y", "yes"}:
                return [DECISION_ACCEPT] * count
            continue
        try:
            return parse_decisions(answer, count)
        except ValueError as exc:
            print(f"invalid: {exc}")


def _review_query(args: argparse.Namespace) -> int:
    queries = {query.query_id: query for query in load_queries(args.queries)}
    passages = load_passages_many(args.passages)
    draft = _load_draft(args.draft, args.query_id)
    if args.limit is not None:
        draft = draft[: args.limit]
    reviewed = load_qrels(args.out) if args.out.exists() else []
    reviewed_keys = {JudgmentKey(row.query_id, row.passage_id) for row in reviewed}
    grouped = _group_by_query(draft)
    progress = reviewed_progress(draft, reviewed)

    has_todo = any(
        JudgmentKey(row.query_id, row.passage_id) not in reviewed_keys
        for row in draft
    )
    if not has_todo:
        print("No unreviewed draft rows.")
        return 0

    for query_id, query_rows in grouped.items():
        todo_rows = [
            row
            for row in query_rows
            if JudgmentKey(row.query_id, row.passage_id) not in reviewed_keys
        ]
        if not todo_rows:
            continue
        display_rows = [row for row in todo_rows if row.passage_id in passages]
        for row in todo_rows:
            if row.passage_id not in passages:
                print(f"missing passage {row.passage_id}; skipping")
        if not display_rows:
            continue

        query = queries.get(query_id)
        _show_candidates(query_id, query, query_rows, display_rows, passages, progress)
        ordinals = _show_review_table(query_id, query_rows, display_rows)
        while True:
            decisions = _ask_decisions(len(display_rows))
            if decisions is None:
                return 0
            if decisions == ["__reprint_table__"]:
                ordinals = _show_review_table(query_id, query_rows, display_rows)
                continue
            if decisions == ["__reprint_candidates__"]:
                _show_candidates(query_id, query, query_rows, display_rows, passages, progress)
                ordinals = _show_review_table(query_id, query_rows, display_rows)
                continue
            break

        pending: list[Qrel] = []
        skipped = 0
        for row, decision in zip(display_rows, decisions, strict=True):
            if decision == DECISION_SKIP:
                skipped += 1
                continue
            relevance = row.relevance if decision == DECISION_ACCEPT else int(decision)
            review_note = ""
            if relevance != row.relevance:
                ordinal = ordinals[JudgmentKey(row.query_id, row.passage_id)]
                review_note = _ask(
                    f"[{ordinal}] override {row.relevance}->{relevance}. "
                    "Catatan (Enter=skip) > "
                )
            pending.append(
                Qrel(
                    query_id=row.query_id,
                    passage_id=row.passage_id,
                    doc_id=row.doc_id,
                    doc_version=row.doc_version,
                    relevance=relevance,
                    annotator=args.annotator,
                    notes=combine_review_notes(
                        row.notes,
                        review_note,
                        row.relevance,
                        relevance,
                    ),
                )
            )

        for qrel in pending:
            append_qrel(args.out, qrel)
            reviewed_keys.add(JudgmentKey(qrel.query_id, qrel.passage_id))
        done, total = progress[query_id]
        progress[query_id] = (done + len(pending), total)
        print(f"\nsaved: {len(pending)} | skipped: {skipped}")

    print("\nReview finished.")
    print(f"output: {args.out}")
    return 0


def _review_one_by_one(args: argparse.Namespace) -> int:
    queries = {query.query_id: query for query in load_queries(args.queries)}
    passages = load_passages_many(args.passages)
    draft = _load_draft(args.draft, args.query_id)
    if args.limit is not None:
        draft = draft[: args.limit]
    reviewed = load_qrels(args.out) if args.out.exists() else []
    reviewed_keys = {JudgmentKey(row.query_id, row.passage_id) for row in reviewed}
    todo = [
        row for row in draft if JudgmentKey(row.query_id, row.passage_id) not in reviewed_keys
    ]
    if not todo:
        print("No unreviewed draft rows.")
        return 0

    progress = reviewed_progress(draft, reviewed)
    current_query = ""
    for draft_row in todo:
        if draft_row.query_id != current_query:
            current_query = draft_row.query_id
            query = queries.get(current_query)
            done, total = progress[current_query]
            print("\n" + "=" * 78)
            if query is not None:
                print(
                    f"{query.query_id} | {query.slice} | as_of={query.as_of} | scope={query.scope}"
                )
                print(f"Q: {query.text}")
            else:
                print(f"{current_query} | (query metadata not found)")
            print(f"reviewed: {done}/{total}")

        passage = passages.get(draft_row.passage_id)
        if passage is None:
            print(f"missing passage {draft_row.passage_id}; skipping")
            continue
        done, total = progress[current_query]
        print(f"\n[{done + 1}/{total}] {draft_row.passage_id}")
        _show_passage(passage)
        print(f"draft: {draft_row.relevance} | note: {draft_row.notes or '-'}")

        review_note = ""
        while True:
            answer = _ask(
                "review [Enter=accept, 0/1/2=override, n=note, s=skip, q=quit] > "
            ).lower()
            if answer == "q":
                return 0
            if answer == "s":
                review_note = ""
                break
            if answer == "n":
                review_note = _ask("review note > ")
                print(f"note set: {review_note or '-'}")
                continue
            if answer == "":
                relevance = draft_row.relevance
            elif answer in {"0", "1", "2"}:
                relevance = int(answer)
            else:
                print("enter=accept, 0, 1, 2, n, s, or q")
                continue

            qrel = Qrel(
                query_id=draft_row.query_id,
                passage_id=draft_row.passage_id,
                doc_id=draft_row.doc_id,
                doc_version=draft_row.doc_version,
                relevance=relevance,
                annotator=args.annotator,
                notes=combine_review_notes(
                    draft_row.notes,
                    review_note,
                    draft_row.relevance,
                    relevance,
                ),
            )
            append_qrel(args.out, qrel)
            reviewed_keys.add(JudgmentKey(draft_row.query_id, draft_row.passage_id))
            old_done, total = progress[current_query]
            progress[current_query] = (old_done + 1, total)
            break

    print("\nReview finished.")
    print(f"output: {args.out}")
    return 0


def _review(args: argparse.Namespace) -> int:
    if args.one_by_one:
        return _review_one_by_one(args)
    return _review_query(args)


def _status(args: argparse.Namespace) -> int:
    draft = _load_draft(args.draft, args.query_id)
    if args.limit is not None:
        draft = draft[: args.limit]
    reviewed = load_qrels(args.out) if args.out.exists() else []
    progress = reviewed_progress(draft, reviewed)
    total_done = sum(done for done, _ in progress.values())
    total = sum(total for _, total in progress.values())
    print(f"reviewed: {total_done}/{total}")
    print(f"remaining: {total - total_done}")

    draft_labels = {(row.query_id, row.passage_id): row.relevance for row in draft}
    reviewed_labels = {(row.query_id, row.passage_id): row.relevance for row in reviewed}
    overrides = [
        (key, draft_labels[key], reviewed_labels[key])
        for key in draft_labels
        if key in reviewed_labels and reviewed_labels[key] != draft_labels[key]
    ]
    print(f"overrides: {len(overrides)}")
    for (query_id, passage_id), old, new in sorted(overrides)[:10]:
        print(f"  {query_id} {passage_id}: {old}->{new}")

    incomplete = [query_id for query_id, (done, total) in progress.items() if done < total]
    print(f"queries incomplete: {len(incomplete)}")
    if incomplete:
        print(" ".join(incomplete[:20]))

    by_query = Counter(query_id for query_id, _ in draft_labels)
    print(f"queries in draft: {len(by_query)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Review LLM draft relevance labels.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--draft", type=Path, default=Path("benchmark/qrels_c_draft.jsonl"))
    common.add_argument("--out", type=Path, default=Path("benchmark/qrels_c_reviewed.jsonl"))
    common.add_argument("--queries", type=Path, default=Path("benchmark/queries.jsonl"))
    common.add_argument(
        "--passages",
        type=Path,
        nargs="+",
        default=[Path("data/processed/passages.jsonl")],
    )
    common.add_argument("--annotator", default="C")
    common.add_argument("--query-id", default=None)
    common.add_argument("--limit", type=int, default=None)

    review = subparsers.add_parser("review", parents=[common])
    review.add_argument("--one-by-one", action="store_true")
    review.set_defaults(func=_review)

    status = subparsers.add_parser("status", parents=[common])
    status.set_defaults(func=_status)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
