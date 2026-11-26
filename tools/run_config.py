from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from recipe_qa.config import load_system_config
from recipe_qa.corpus.build import read_jsonl
from recipe_qa.generation.generate import AnswerGenerator
from recipe_qa.pipeline.common import run_query
from recipe_qa.retrieval.search import Retriever


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[int(round(fraction * (len(ordered) - 1)))]


def read_query_ids(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def summarize(rows: list[dict]) -> dict:
    def block(items: list[dict]) -> dict:
        valid = sum(1 for row in items if row.get("schema_valid"))
        abstain = sum(1 for row in items if (row.get("answer") or {}).get("abstain"))
        latencies = [float(row.get("latency_ms") or 0.0) for row in items]
        verification = [
            row["verification"] for row in items if row.get("verification")
        ]
        return {
            "n": len(items),
            "schema_valid": valid,
            "schema_valid_rate": valid / len(items) if items else 0.0,
            "abstain": abstain,
            "abstain_rate": abstain / len(items) if items else 0.0,
            "verification": {
                "n": len(verification),
                "supported": sum(int(item.get("supported") or 0) for item in verification),
                "refuted": sum(int(item.get("refuted") or 0) for item in verification),
                "dropped": sum(int(item.get("dropped") or 0) for item in verification),
                "abstained": sum(1 for item in verification if item.get("abstained")),
            },
            "latency_ms": {
                "p50": percentile(latencies, 0.50),
                "p95": percentile(latencies, 0.95),
                "mean": sum(latencies) / len(latencies) if latencies else 0.0,
            },
        }

    by_slice: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_slice[row.get("slice", "unknown")].append(row)
    return {
        "overall": block(rows),
        "per_slice": {name: block(items) for name, items in sorted(by_slice.items())},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one system config over a query list.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--queries", type=Path, default=Path("benchmark/queries.jsonl"))
    parser.add_argument("--query-ids", nargs="*", default=None)
    parser.add_argument("--query-ids-file", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--no-generate", action="store_true")
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)

    config = load_system_config(args.config)
    queries = list(read_jsonl(args.queries))
    query_rows = {row["query_id"]: row for row in queries}

    wanted: list[str] | None = None
    if args.query_ids_file:
        wanted = read_query_ids(args.query_ids_file)
    elif args.query_ids:
        wanted = args.query_ids
    if wanted is not None:
        missing = [query_id for query_id in wanted if query_id not in query_rows]
        if missing:
            raise SystemExit(f"unknown query ids: {missing}")
        query_rows = {query_id: query_rows[query_id] for query_id in wanted}
    selected = list(query_rows.values())
    if args.limit:
        selected = selected[: args.limit]

    retriever = Retriever(config.retrieval) if config.retrieval.mode != "none" else None
    generator = None if args.no_generate else AnswerGenerator(config.model)
    verifier = None
    if config.verification.enabled and not args.no_generate:
        from recipe_qa.verify.nli import NliVerifier

        verifier = NliVerifier(config.verification.nli_model)

    rows: list[dict] = []
    for row in selected:
        result = run_query(
            config,
            row,
            retriever=retriever,
            generator=generator,
            verifier=verifier,
        )
        result["slice"] = row.get("slice")
        rows.append(result)
        print(
            f"{row['query_id']} schema_valid={result.get('schema_valid')} "
            f"latency_ms={result.get('latency_ms')}",
            flush=True,
        )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    results_path = args.out_dir / "results.jsonl"
    with results_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    summary = {
        "config": config.id,
        "config_path": str(args.config),
        "queries": len(rows),
        **summarize(rows),
    }
    (args.out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
