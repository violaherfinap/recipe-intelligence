from __future__ import annotations

import argparse
import json
from pathlib import Path

from recipe_qa.benchmark.preannotation import parse_answers, validate_answers
from recipe_qa.benchmark.schema import Qrel
from recipe_qa.benchmark.validate import read_jsonl, write_jsonl


def _prepare_output(path: Path, force: bool) -> bool:
    if not path.exists():
        return True
    if not force:
        print(f"ERROR output exists: {path}; use --force to overwrite")
        return False
    backup = path.with_name(f"{path.name}.bak")
    backup.write_bytes(path.read_bytes())
    print(f"backup: {backup}")
    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import LLM preannotation answers.")
    parser.add_argument("--input", type=Path, nargs="+", required=True)
    parser.add_argument(
        "--keys", type=Path, default=Path("benchmark/work/w2-c/keys.jsonl")
    )
    parser.add_argument(
        "--commit", type=Path, default=Path("data/corpus_commit.txt")
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("benchmark/work/w2-c/qrels_v2_c_ai_draft.jsonl"),
    )
    parser.add_argument("--annotator", default="preannotator")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    key_rows = read_jsonl(args.keys)
    expected = {(row["query_id"], row["passage_id"]) for row in key_rows}
    doc_by_key = {
        (row["query_id"], row["passage_id"]): row["doc_id"] for row in key_rows
    }
    doc_version = args.commit.read_text(encoding="utf-8").strip()

    parsed_rows: list[dict] = []
    errors: list[str] = []
    for path in args.input:
        parsed = parse_answers(path.read_text(encoding="utf-8"))
        parsed_rows.extend(parsed.rows)
        errors.extend(f"{path.name}: {error}" for error in parsed.errors)

    errors.extend(validate_answers(parsed_rows, expected))
    if errors:
        print(f"errors: {len(errors)}")
        for error in errors:
            print(f"  ERROR {error}")
        return 1

    qrels = [
        Qrel(
            query_id=row["query_id"],
            passage_id=row["passage_id"],
            doc_id=doc_by_key[(row["query_id"], row["passage_id"])],
            doc_version=doc_version,
            relevance=row["relevance"],
            annotator=args.annotator,
            notes=row["notes"],
        )
        for row in parsed_rows
    ]
    qrels.sort(key=lambda row: (row.query_id, row.passage_id))
    print(json.dumps({"rows": len(qrels), "queries": len({row.query_id for row in qrels})}))
    if args.dry_run:
        print("dry-run: no file written")
        return 0
    if not _prepare_output(args.out, args.force):
        return 1
    write_jsonl(args.out, [row.model_dump() for row in qrels])
    print(f"written: {args.out} ({len(qrels)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
