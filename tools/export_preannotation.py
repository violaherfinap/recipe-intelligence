from __future__ import annotations

import argparse
import json
from pathlib import Path

from recipe_qa.benchmark.annotation import JudgmentKey, load_judged, load_pool
from recipe_qa.benchmark.validate import load_passages_many, load_queries, write_jsonl

PROMPT_HEADER = """\
Anda membantu membuat draft relevance qrels untuk benchmark resep sejarah.
Nilai setiap passage terhadap query, bukan terhadap dokumen secara keseluruhan.

Skala:
0 = tidak relevan, atau hanya berbagi kata umum; resep/dokumen lain.
1 = relevan parsial: memberi konteks, bahan terkait, atau satu bagian jawaban.
2 = passage langsung menjawab atau menyelesaikan klaim query.

Aturan:
- Nilai berdasarkan isi passage dan query. Jangan memakai pengetahuan luar korpus.
- Multi-hop: passage yang menyelesaikan salah satu klaim tetap 2.
- Passage ingredients yang memuat nilai yang ditanyakan (takaran/jumlah/daftar bahan) = 2.
- Passage ingredients yang hanya menyebut bahan terkait saat query menanyakan prosedur = 1.
- Passage dari resep/dokumen lain = 0.
- Fixed/section/hierarchical tidak mengubah skala; nilailah isinya.
- Jika ragu antara 0 dan 1, pilih 0; jika ragu antara 1 dan 2, pilih 1.

Format jawaban, satu baris per passage, tanpa teks lain:
query_id|passage_id|0/1/2|alasan singkat
"""


def _query_header(query) -> str:
    return (
        f"{query.query_id} | {query.slice} | as_of={query.as_of} | "
        f"scope={query.scope or '-'}\nQ: {query.text}"
    )


def _passage_block(number: int, candidate, passage: dict) -> str:
    title = passage.get("source_title", "")
    year = passage.get("source_year", "?")
    section = passage.get("section", "")
    return (
        f"\n[{number}] {candidate.query_id} | {candidate.passage_id} | "
        f"{candidate.doc_id} | {title} ({year}) | {section}\n"
        f"{passage.get('text', '').strip()}"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export unjudged pool candidates and LLM prompt batches."
    )
    parser.add_argument("--queries", type=Path, default=Path("benchmark/queries.jsonl"))
    parser.add_argument("--pool", type=Path, default=Path("benchmark/pool_v2.jsonl"))
    parser.add_argument(
        "--passages",
        type=Path,
        nargs="+",
        default=[
            Path("data/processed/passages.jsonl"),
            Path("data/processed/passages_fixed.jsonl"),
        ],
    )
    parser.add_argument(
        "--seed",
        type=Path,
        default=Path("benchmark/work/w2-c/qrels_v2_c_seed.jsonl"),
    )
    parser.add_argument("--out-dir", type=Path, default=Path("benchmark/work/w2-c"))
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="number of queries per prompt file",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    queries = load_queries(args.queries)
    pool = load_pool(args.pool)
    passages = load_passages_many(args.passages)
    judged = load_judged(args.seed)

    keys: list[dict] = []
    by_query: dict[str, list] = {}
    for query in queries:
        candidates = [
            candidate
            for candidate in pool.get(query.query_id, [])
            if JudgmentKey(query.query_id, candidate.passage_id) not in judged
        ]
        if not candidates:
            continue
        by_query[query.query_id] = candidates
        for candidate in candidates:
            passage = passages.get(candidate.passage_id)
            if passage is None:
                print(f"ERROR missing passage: {candidate.query_id} {candidate.passage_id}")
                return 1
            keys.append(
                {
                    "query_id": candidate.query_id,
                    "passage_id": candidate.passage_id,
                    "doc_id": candidate.doc_id,
                    "section": passage.get("section", ""),
                }
            )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.out_dir / "keys.jsonl", keys)

    query_ids = [query.query_id for query in queries if query.query_id in by_query]
    batches: list[str] = []
    for batch_index in range(0, len(query_ids), args.batch_size):
        batch_query_ids = query_ids[batch_index : batch_index + args.batch_size]
        lines = [PROMPT_HEADER]
        number = 1
        for query_id in batch_query_ids:
            query = next(item for item in queries if item.query_id == query_id)
            lines.append("\n" + "=" * 78 + "\n" + _query_header(query) + "\n")
            for candidate in by_query[query_id]:
                lines.append(_passage_block(number, candidate, passages[candidate.passage_id]))
                number += 1
        filename = f"prompt_{batch_index // args.batch_size + 1:03d}.txt"
        path = args.out_dir / filename
        path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        batches.append(filename)

    manifest = {
        "seed": str(args.seed),
        "pool": str(args.pool),
        "passages": [str(path) for path in args.passages],
        "queries": len(query_ids),
        "candidates": len(keys),
        "batch_size": args.batch_size,
        "batches": batches,
    }
    (args.out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
