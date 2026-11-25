from __future__ import annotations

import argparse
import shutil
from collections import Counter, defaultdict
from pathlib import Path

from recipe_qa.benchmark.schema import Qrel
from recipe_qa.benchmark.validate import (
    load_passages_many,
    load_queries,
    read_jsonl,
    write_jsonl,
)


def _key(row: dict) -> tuple[str, str]:
    return row["query_id"], row["passage_id"]


def _duplicates(rows: list[dict]) -> list[tuple[str, str]]:
    counts = Counter(_key(row) for row in rows)
    return sorted(key for key, count in counts.items() if count > 1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Merge and validate Week 2 C qrels v2 pass 1."
    )
    parser.add_argument(
        "--seed",
        type=Path,
        default=Path("benchmark/work/w2-c/qrels_v2_c_seed.jsonl"),
    )
    parser.add_argument(
        "--reviewed",
        type=Path,
        default=Path("benchmark/work/w2-c/qrels_v2_c_reviewed.jsonl"),
    )
    parser.add_argument(
        "--draft",
        type=Path,
        default=Path("benchmark/work/w2-c/qrels_v2_c_ai_draft.jsonl"),
    )
    parser.add_argument("--pool", type=Path, default=Path("benchmark/pool_v2.jsonl"))
    parser.add_argument("--queries", type=Path, default=Path("benchmark/queries.jsonl"))
    parser.add_argument(
        "--passages",
        type=Path,
        nargs="+",
        default=[
            Path("data/processed/passages.jsonl"),
            Path("data/processed/passages_fixed.jsonl"),
        ],
    )
    parser.add_argument("--commit", type=Path, default=Path("data/corpus_commit.txt"))
    parser.add_argument(
        "--reference",
        type=Path,
        default=Path("benchmark/qrels.jsonl"),
        help="frozen qrels v1.1 used to verify the seed",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("benchmark/qrels_v2_c.jsonl"),
    )
    parser.add_argument("--annotator", default="C")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    seed_rows = read_jsonl(args.seed)
    reviewed_rows = read_jsonl(args.reviewed)
    draft_rows = read_jsonl(args.draft)
    pool_rows = read_jsonl(args.pool)
    reference_rows = read_jsonl(args.reference)
    queries = load_queries(args.queries)
    passages = load_passages_many(args.passages)
    doc_version = args.commit.read_text(encoding="utf-8").strip()

    errors: list[str] = []
    warnings: list[str] = []

    seed_sorted = sorted(seed_rows, key=_key)
    reference_sorted = sorted(reference_rows, key=_key)
    if seed_sorted != reference_sorted:
        errors.append("seed does not exactly match frozen benchmark/qrels.jsonl")

    for name, rows in (
        ("seed", seed_rows),
        ("reviewed", reviewed_rows),
        ("draft", draft_rows),
        ("pool", pool_rows),
    ):
        duplicates = _duplicates(rows)
        if duplicates:
            errors.append(f"duplicate {name} keys: {duplicates[:10]}")

    seed_keys = {_key(row) for row in seed_rows}
    reviewed_keys = {_key(row) for row in reviewed_rows}
    draft_keys = {_key(row) for row in draft_rows}
    pool_keys = {_key(row) for row in pool_rows}
    overlap = seed_keys & reviewed_keys
    if overlap:
        errors.append(f"seed/reviewed overlap: {sorted(overlap)[:10]}")
    if draft_keys != reviewed_keys:
        missing = sorted(draft_keys - reviewed_keys)
        extra = sorted(reviewed_keys - draft_keys)
        errors.append(f"draft keys missing from reviewed: {missing[:10]}")
        errors.append(f"reviewed keys outside draft: {extra[:10]}")

    union_keys = seed_keys | reviewed_keys
    missing_pool = sorted(union_keys - pool_keys)
    extra_pool = sorted(pool_keys - union_keys)
    if missing_pool:
        errors.append(f"final keys missing from pool: {missing_pool[:10]}")
    if extra_pool:
        errors.append(f"pool keys missing from final: {extra_pool[:10]}")

    query_ids = {query.query_id for query in queries}
    final_query_ids = {query_id for query_id, _ in union_keys}
    missing_queries = sorted(query_ids - final_query_ids)
    extra_queries = sorted(final_query_ids - query_ids)
    if missing_queries:
        errors.append(f"queries without qrels: {missing_queries}")
    if extra_queries:
        errors.append(f"qrels for unknown queries: {extra_queries}")

    by_query: dict[str, list[dict]] = defaultdict(list)
    for row in [*seed_rows, *reviewed_rows]:
        by_query[row["query_id"]].append(row)
        try:
            qrel = Qrel.model_validate(row)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{_key(row)}: invalid qrel: {exc}")
            continue
        if _key(row) in reviewed_keys and qrel.annotator != args.annotator:
            errors.append(f"{_key(row)}: reviewed annotator must be {args.annotator!r}")
        if qrel.doc_version != doc_version:
            errors.append(f"{_key(row)}: doc_version does not match corpus commit")
        passage = passages.get(qrel.passage_id)
        if passage is None:
            errors.append(f"{_key(row)}: passage not found")
            continue
        if qrel.doc_id != passage.get("doc_id"):
            errors.append(f"{_key(row)}: doc_id does not match passage")
        if passage.get("split") != "test":
            errors.append(f"{_key(row)}: passage is not in test split")

    for query in queries:
        rows = by_query.get(query.query_id, [])
        if not rows:
            errors.append(f"{query.query_id}: no qrels")
            continue
        relevances = [row.get("relevance") for row in rows]
        if query.slice == "no-evidence" and any(relevances):
            errors.append(f"{query.query_id}: no-evidence query has non-zero labels")
        if query.slice != "no-evidence" and 2 not in relevances:
            errors.append(f"{query.query_id}: answerable query has no relevance-2 passage")
        if query.slice == "multi-hop":
            twos = [row for row in rows if row.get("relevance") == 2]
            doc_ids = {row.get("doc_id") for row in twos}
            if len(twos) < 2 or len(doc_ids) < 2:
                warnings.append(
                    f"{query.query_id}: multi-hop has {len(twos)} relevance-2 passages "
                    f"across {len(doc_ids)} documents"
                )

    draft_relevances = {_key(row): row.get("relevance") for row in draft_rows}
    overrides = sum(
        1
        for row in reviewed_rows
        if _key(row) in draft_relevances
        and row.get("relevance") != draft_relevances[_key(row)]
    )
    labels = Counter(row.get("relevance") for row in [*seed_rows, *reviewed_rows])

    print(f"seed: {len(seed_rows)}")
    print(f"reviewed: {len(reviewed_rows)}")
    print(f"merged: {len(union_keys)}")
    print(f"queries: {len(final_query_ids)}")
    print(f"labels: {dict(sorted(labels.items()))}")
    print(f"overrides: {overrides}")
    if warnings:
        print(f"warnings: {len(warnings)}")
        for warning in warnings:
            print(f"  WARN {warning}")
    if errors:
        print(f"errors: {len(errors)}")
        for error in errors:
            print(f"  ERROR {error}")
        return 1

    merged = sorted([*seed_rows, *reviewed_rows], key=_key)
    if args.dry_run:
        print("dry-run: no file written")
        return 0
    if args.out.exists():
        backup = args.out.with_name(f"{args.out.name}.bak")
        shutil.copy2(args.out, backup)
        print(f"backup: {backup}")
    tmp_path = args.out.with_name(f".{args.out.name}.tmp")
    write_jsonl(tmp_path, merged)
    tmp_path.replace(args.out)
    print(f"written: {args.out} ({len(merged)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
