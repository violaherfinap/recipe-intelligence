from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from recipe_qa.benchmark.validate import load_passages_many, read_jsonl

FIELDS = [
    "error_id",
    "source",
    "query_id",
    "slice",
    "query",
    "as_of",
    "code",
    "evidence_passage_id",
    "evidence_doc_id",
    "evidence_text",
    "retrieved_rank",
    "retrieved_passage_id",
    "retrieved_doc_id",
    "retrieved_year",
    "retrieved_text",
    "relevance_label",
    "justification",
    "notes",
]


def _qrels_index(path: Path) -> tuple[dict[str, dict[str, int]], dict[str, str]]:
    grades: dict[str, dict[str, int]] = {}
    docs: dict[str, str] = {}
    for row in read_jsonl(path):
        query_id = row["query_id"]
        passage_id = row["passage_id"]
        grades.setdefault(query_id, {})[passage_id] = int(row["relevance"])
        docs[passage_id] = row["doc_id"]
    return grades, docs


def _passage_text(passages: dict[str, dict], passage_id: str) -> str:
    passage = passages.get(passage_id)
    return "" if passage is None else str(passage.get("text", "")).strip()


def _hit_year(hit: dict, passages: dict[str, dict]) -> str:
    year = hit.get("source_year")
    if year is None:
        passage = passages.get(hit["passage_id"], {})
        year = passage.get("source_year")
    return "" if year is None else str(year)


def _row(
    source: str,
    query: dict,
    code: str,
    justification: str,
    *,
    evidence_passage_id: str = "",
    evidence_doc_id: str = "",
    evidence_text: str = "",
    retrieved_rank: str = "",
    retrieved_passage_id: str = "",
    retrieved_doc_id: str = "",
    retrieved_year: str = "",
    retrieved_text: str = "",
    relevance_label: str = "",
    notes: str = "",
) -> dict:
    return {
        "source": source,
        "query_id": query["query_id"],
        "slice": query.get("slice", ""),
        "query": query.get("text", ""),
        "as_of": "" if query.get("as_of") is None else query["as_of"],
        "code": code,
        "evidence_passage_id": evidence_passage_id,
        "evidence_doc_id": evidence_doc_id,
        "evidence_text": evidence_text,
        "retrieved_rank": retrieved_rank,
        "retrieved_passage_id": retrieved_passage_id,
        "retrieved_doc_id": retrieved_doc_id,
        "retrieved_year": retrieved_year,
        "retrieved_text": retrieved_text,
        "relevance_label": relevance_label,
        "justification": justification,
        "notes": notes,
    }


def build_rows(
    run_path: Path,
    qrels_path: Path,
    queries_path: Path,
    passages: dict[str, dict],
    top_k: int,
) -> list[dict]:
    run = json.loads(run_path.read_text(encoding="utf-8"))
    rankings = run.get("rankings", {})
    grades_by_query, doc_by_passage = _qrels_index(qrels_path)
    queries = {row["query_id"]: row for row in read_jsonl(queries_path)}

    rows: list[dict] = []
    for query_id in sorted(rankings):
        query = queries.get(query_id)
        if query is None:
            continue
        if query.get("slice") == "no-evidence":
            continue
        grades = grades_by_query.get(query_id, {})
        relevant = {
            passage_id: grade for passage_id, grade in grades.items() if grade >= 1
        }
        if not relevant:
            continue
        relevant_docs = {
            doc_by_passage.get(passage_id, "") for passage_id in relevant
        }
        hits = rankings[query_id][:top_k]
        retrieved_ids = {hit["passage_id"] for hit in hits}
        top_hit = hits[0] if hits else None
        top_text = _passage_text(passages, top_hit["passage_id"]) if top_hit else ""
        top_label = "" if top_hit is None else str(grades.get(top_hit["passage_id"], ""))

        for passage_id, grade in sorted(relevant.items()):
            if passage_id in retrieved_ids:
                continue
            rows.append(
                _row(
                    "retrieval",
                    query,
                    "E1",
                    (
                        f"Passage relevan {passage_id} (label {grade}) tidak muncul "
                        f"di top-{top_k}."
                    ),
                    evidence_passage_id=passage_id,
                    evidence_doc_id=doc_by_passage.get(passage_id, ""),
                    evidence_text=_passage_text(passages, passage_id),
                    retrieved_rank="1" if top_hit else "",
                    retrieved_passage_id=top_hit["passage_id"] if top_hit else "",
                    retrieved_doc_id=top_hit.get("doc_id", "") if top_hit else "",
                    retrieved_year=_hit_year(top_hit, passages) if top_hit else "",
                    retrieved_text=top_text,
                    relevance_label=str(grade),
                    notes=f"top-1 relevance={top_label or 'unjudged'}",
                )
            )

        if top_hit is not None:
            top_passage_id = top_hit["passage_id"]
            top_doc_id = top_hit.get("doc_id", "")
            top_grade = grades.get(top_passage_id)
            if top_grade == 0 and top_doc_id not in relevant_docs:
                rows.append(
                    _row(
                        "retrieval",
                        query,
                        "E2",
                        (
                            "Peringkat 1 berasal dari dokumen yang tidak memuat "
                            "passage relevan mana pun untuk query ini."
                        ),
                        evidence_passage_id=sorted(relevant)[0],
                        evidence_doc_id=doc_by_passage.get(sorted(relevant)[0], ""),
                        evidence_text=_passage_text(passages, sorted(relevant)[0]),
                        retrieved_rank="1",
                        retrieved_passage_id=top_passage_id,
                        retrieved_doc_id=top_doc_id,
                        retrieved_year=_hit_year(top_hit, passages),
                        retrieved_text=top_text,
                        relevance_label="0",
                        notes=f"wrong_doc={top_doc_id}",
                    )
                )

        as_of = query.get("as_of")
        if as_of is not None:
            for rank, hit in enumerate(hits, start=1):
                year = _hit_year(hit, passages)
                if not year or not year.isdigit() or int(year) <= int(as_of):
                    continue
                rows.append(
                    _row(
                        "retrieval",
                        query,
                        "E4",
                        (
                            f"Passage peringkat {rank} berasal dari tahun {year}, "
                            f"melewati as_of={as_of}."
                        ),
                        evidence_passage_id=sorted(relevant)[0],
                        evidence_doc_id=doc_by_passage.get(sorted(relevant)[0], ""),
                        evidence_text=_passage_text(passages, sorted(relevant)[0]),
                        retrieved_rank=str(rank),
                        retrieved_passage_id=hit["passage_id"],
                        retrieved_doc_id=hit.get("doc_id", ""),
                        retrieved_year=year,
                        retrieved_text=_passage_text(passages, hit["passage_id"]),
                        relevance_label=str(grades.get(hit["passage_id"], "")),
                    )
                )

    for index, row in enumerate(rows, start=1):
        row["error_id"] = f"ERR{index:04d}"
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze retrieval-only error taxonomy (E1/E2/E4)."
    )
    parser.add_argument(
        "--run", type=Path, default=Path("artifacts/runs/retrieval_b3_v2.json")
    )
    parser.add_argument("--qrels", type=Path, default=Path("benchmark/qrels.jsonl"))
    parser.add_argument(
        "--queries", type=Path, default=Path("benchmark/queries.jsonl")
    )
    parser.add_argument(
        "--passages",
        type=Path,
        nargs="+",
        default=[
            Path("data/processed/passages.jsonl"),
            Path("data/processed/passages_fixed.jsonl"),
        ],
    )
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--out", type=Path, default=Path("error_analysis.csv"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    rows = build_rows(
        run_path=args.run,
        qrels_path=args.qrels,
        queries_path=args.queries,
        passages=load_passages_many(args.passages),
        top_k=args.top_k,
    )
    write_csv(args.out, rows)
    counts = Counter(row["code"] for row in rows)
    print(f"rows: {len(rows)}")
    print("codes: " + ", ".join(f"{code}={count}" for code, count in sorted(counts.items())))
    print(f"written: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
