from __future__ import annotations

import argparse
import json
from pathlib import Path

from recipe_qa.retrieval.search import INDEX_DIRS, PASSAGE_PATHS


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = int(round(fraction * (len(ordered) - 1)))
    return ordered[position]


def load_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def directory_bytes(path: Path) -> int:
    return sum(child.stat().st_size for child in path.rglob("*") if child.is_file())


def summarize(mode: str, run_path: Path) -> dict:
    passages = {
        row["passage_id"]: row for row in load_jsonl(PASSAGE_PATHS[mode])
    }
    run = json.loads(run_path.read_text(encoding="utf-8"))
    totals: list[int] = []
    hit_tokens: list[int] = []
    unique_docs: list[int] = []
    for hits in run["rankings"].values():
        counts = [
            int(passages[hit["passage_id"]]["token_count"])
            for hit in hits
            if hit["passage_id"] in passages
        ]
        totals.append(sum(counts))
        hit_tokens.extend(counts)
        unique_docs.append(len({hit["doc_id"] for hit in hits}))
    index_dir = INDEX_DIRS[mode]
    manifest = json.loads((index_dir / "manifest.json").read_text(encoding="utf-8"))
    return {
        "mode": mode,
        "queries": len(totals),
        "passage_count": manifest["passage_count"],
        "index_bytes": directory_bytes(index_dir),
        "dense_npy_bytes": (index_dir / "dense.npy").stat().st_size,
        "context_tokens": {
            "mean": sum(totals) / len(totals) if totals else 0.0,
            "p50": percentile([float(value) for value in totals], 0.50),
            "p95": percentile([float(value) for value in totals], 0.95),
            "max": max(totals) if totals else 0,
        },
        "hit_tokens": {
            "mean": sum(hit_tokens) / len(hit_tokens) if hit_tokens else 0.0,
            "max": max(hit_tokens) if hit_tokens else 0,
        },
        "unique_docs_per_query": {
            "mean": sum(unique_docs) / len(unique_docs) if unique_docs else 0.0,
            "min": min(unique_docs) if unique_docs else 0,
            "max": max(unique_docs) if unique_docs else 0,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize A1 context/index stats.")
    parser.add_argument("--runs", type=Path, default=Path("artifacts/runs"))
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    summary = [
        summarize(mode, args.runs / f"a1_{mode}_full.json")
        for mode in ("fixed", "section", "hierarchical")
    ]
    payload = json.dumps(summary, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
