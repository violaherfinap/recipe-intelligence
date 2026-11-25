from __future__ import annotations

import argparse
from pathlib import Path

from recipe_qa.benchmark.annotation import (
    JudgmentKey,
    append_qrel,
    append_verdict,
    evidence_passages,
    load_judged,
    load_pool,
    order_candidates,
    relevance_progress,
    verdict_progress,
)
from recipe_qa.benchmark.schema import Qrel, VerdictQrel
from recipe_qa.benchmark.validate import load_passages_many, load_queries


def _ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print("\nStopped. Progress has been saved.")
        raise SystemExit(130) from None


def _commit_sha(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def _show_passage(passage: dict) -> None:
    header = (
        f"{passage['doc_id']} | {passage.get('source_title', '')} "
        f"({passage.get('source_year', '?')}) | {passage['section']}#{passage['idx']}"
    )
    print(f"\n{header}")
    print("-" * len(header))
    print(passage["text"].strip())


def _relevance(args: argparse.Namespace) -> int:
    queries = load_queries(args.queries)
    if args.query_id:
        queries = [query for query in queries if query.query_id == args.query_id]
    pool = load_pool(args.pool)
    passages = load_passages_many(args.passages)
    judged = load_judged(args.out)
    commit = _commit_sha(args.commit_file)

    for query in queries:
        if query.author == args.annotator:
            print(f"skip {query.query_id}: annotator is the query author")
            continue
        candidates = pool.get(query.query_id, [])
        if not candidates:
            print(f"skip {query.query_id}: no candidates in pool")
            continue
        ordered = order_candidates(candidates, args.annotator)
        todo = [
            candidate
            for candidate in ordered
            if JudgmentKey(query.query_id, candidate.passage_id) not in judged
        ]
        if not todo:
            continue
        if args.limit is not None:
            todo = todo[: args.limit]

        print("\n" + "=" * 78)
        print(f"{query.query_id} | {query.slice} | as_of={query.as_of} | scope={query.scope}")
        print(f"Q: {query.text}")
        print(f"candidates left: {len(todo)}")

        for candidate in todo:
            passage = passages.get(candidate.passage_id)
            if passage is None:
                print(f"missing passage {candidate.passage_id}; skipping")
                continue
            _show_passage(passage)
            pending_note = ""
            while True:
                answer = _ask("relevance [0/1/2], n=note, s=skip, q=quit > ").lower()
                if answer == "q":
                    return 0
                if answer == "s":
                    pending_note = ""
                    break
                if answer == "n":
                    pending_note = _ask("note > ")
                    continue
                if answer in {"0", "1", "2"}:
                    qrel = Qrel(
                        query_id=query.query_id,
                        passage_id=candidate.passage_id,
                        doc_id=candidate.doc_id,
                        doc_version=commit,
                        relevance=int(answer),
                        annotator=args.annotator,
                        notes=pending_note,
                    )
                    append_qrel(args.out, qrel)
                    judged.add(JudgmentKey(query.query_id, candidate.passage_id))
                    break
                print("enter 0, 1, 2, n, s, or q")

    print("\nRelevance annotation finished.")
    print(f"output: {args.out}")
    return 0


def _verdict(args: argparse.Namespace) -> int:
    queries = load_queries(args.queries)
    if args.query_id:
        queries = [query for query in queries if query.query_id == args.query_id]
    passages = load_passages_many(args.passages)
    done: set[tuple[str, str]] = set()
    if args.out.exists():
        from recipe_qa.benchmark.validate import load_verdict_qrels

        for row in load_verdict_qrels(args.out):
            done.add((row.query_id, row.claim_id))

    for query in queries:
        if query.author == args.annotator:
            continue
        claims = list(query.gold_claims)
        if not claims:
            continue
        evidence = evidence_passages(query.query_id, args.qrels)
        print("\n" + "=" * 78)
        print(f"{query.query_id} | {query.slice} | as_of={query.as_of}")
        print(f"Q: {query.text}")
        for index, claim in enumerate(claims, start=1):
            claim_id = f"c{index}"
            if (query.query_id, claim_id) in done:
                continue
            print(f"\nClaim {claim_id}: {claim}")
            if evidence:
                for passage_id in evidence:
                    passage = passages.get(passage_id)
                    if passage is not None:
                        _show_passage(passage)
            else:
                print("(no level-2 evidence in qrels)")
            while True:
                answer = _ask(
                    "verdict [s=SUPPORTED, r=REFUTED, n=NOT_ENOUGH_EVIDENCE, q=quit] > "
                ).lower()
                if answer == "q":
                    return 0
                mapping = {
                    "s": "SUPPORTED",
                    "r": "REFUTED",
                    "n": "NOT_ENOUGH_EVIDENCE",
                }
                if answer in mapping:
                    note = _ask("note (optional) > ")
                    append_verdict(
                        args.out,
                        VerdictQrel(
                            query_id=query.query_id,
                            claim_id=claim_id,
                            verdict=mapping[answer],
                            annotator=args.annotator,
                            notes=note,
                        ),
                    )
                    done.add((query.query_id, claim_id))
                    break
                print("enter s, r, n, or q")

    print("\nVerdict annotation finished.")
    print(f"output: {args.out}")
    return 0


def _status(args: argparse.Namespace) -> int:
    queries = load_queries(args.queries)
    if args.out.name.startswith("verdict"):
        progress = verdict_progress(queries, args.out)
        total_done = sum(done for done, _ in progress.values())
        total = sum(total for _, total in progress.values())
        print(f"claims: {total_done}/{total}")
    else:
        pool = load_pool(args.pool)
        judged = load_judged(args.out)
        progress = relevance_progress(queries, pool, judged)
        total_done = sum(done for done, _ in progress.values())
        total = sum(total for _, total in progress.values())
        print(f"judgments: {total_done}/{total}")
    incomplete = [query_id for query_id, (done, total) in progress.items() if done < total]
    print(f"queries incomplete: {len(incomplete)}")
    if incomplete:
        print(" ".join(incomplete[:20]))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Annotate benchmark relevance and claim verdicts.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--annotator", required=True, choices=["A", "C", "D"])
    common.add_argument("--queries", type=Path, default=Path("benchmark/queries.jsonl"))
    common.add_argument(
        "--passages",
        type=Path,
        nargs="+",
        default=[Path("data/processed/passages.jsonl")],
    )
    common.add_argument("--out", type=Path, required=True)
    common.add_argument("--query-id", default=None)
    common.add_argument("--limit", type=int, default=None)

    relevance = subparsers.add_parser("relevance", parents=[common])
    relevance.add_argument("--pool", type=Path, default=Path("benchmark/pool_v1.jsonl"))
    relevance.add_argument("--commit-file", type=Path, default=Path("data/corpus_commit.txt"))
    relevance.set_defaults(func=_relevance)

    verdict = subparsers.add_parser("verdict", parents=[common])
    verdict.add_argument("--qrels", type=Path, required=True)
    verdict.set_defaults(func=_verdict)

    status = subparsers.add_parser("status", parents=[common])
    status.add_argument("--pool", type=Path, default=Path("benchmark/pool_v1.jsonl"))
    status.set_defaults(func=_status)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
