"""Build a blinded annotation pool from gold evidence and dense retrieval."""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from ..index.build import QUERY_PREFIX
from .schema import GoldCandidate, PoolCandidate, PoolMeta
from .validate import load_passages, load_queries, read_jsonl, write_jsonl


@dataclass
class PoolBuildResult:
    """Counts returned by :func:`build_pool`."""

    queries: int
    candidates: int
    gold: int
    dense: int
    negatives: int


def _load_gold(path: Path) -> dict[str, GoldCandidate]:
    candidates = [GoldCandidate.model_validate(row) for row in read_jsonl(path)]
    return {candidate.query_id: candidate for candidate in candidates}


def build_pool(
    queries_path: Path,
    gold_path: Path,
    passages_path: Path,
    out_path: Path,
    meta_path: Path,
    dense_dir: Path = Path("indexes"),
    model_name: str = "BAAI/bge-small-en-v1.5",
    split: str = "test",
    dense_k: int = 10,
    negatives: int = 5,
    seed: int = 42,
    batch_size: int = 32,
) -> PoolBuildResult:
    """Create the blinded pool and its separate provenance file."""
    queries = load_queries(queries_path)
    gold = _load_gold(gold_path)
    passages = load_passages(passages_path)

    dense_path = dense_dir / "dense.npy"
    meta_file = dense_dir / "dense_meta.parquet"
    if not dense_path.exists() or not meta_file.exists():
        raise FileNotFoundError(
            f"dense index not found in {dense_dir}; run `make index` first"
        )

    embeddings = np.load(dense_path)
    meta = pd.read_parquet(meta_file).reset_index(drop=True)
    if len(meta) != len(embeddings):
        raise ValueError("dense.npy and dense_meta.parquet have different lengths")

    split_mask = meta["split"].to_numpy() == split
    rows = np.flatnonzero(split_mask)
    if len(rows) == 0:
        raise ValueError(f"no passages with split={split!r}")
    split_embeddings = embeddings[rows]
    split_meta = meta.iloc[rows].reset_index(drop=True)
    split_ids = split_meta["passage_id"].tolist()
    split_id_set = set(split_ids)

    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name, device="cpu")
    query_vectors = model.encode(
        [QUERY_PREFIX + query.text for query in queries],
        batch_size=batch_size,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=True,
    )
    scores = query_vectors @ split_embeddings.T
    top_indices = np.argsort(-scores, axis=1)[:, :dense_k]

    pool_rows: list[dict] = []
    meta_rows: list[dict] = []
    counts = {"gold": 0, "dense": 0, "negative": 0}

    for query_index, query in enumerate(queries):
        chosen: dict[str, PoolCandidate] = {}
        query_gold = gold.get(query.query_id)
        if query_gold is not None:
            for passage_id in query_gold.passage_ids:
                passage = passages.get(passage_id)
                if passage is None:
                    raise ValueError(f"{query.query_id}: unknown gold passage {passage_id}")
                if passage.get("split") != split:
                    raise ValueError(
                        f"{query.query_id}: gold passage {passage_id} is not in {split}"
                    )
                chosen[passage_id] = PoolCandidate(
                    query_id=query.query_id,
                    passage_id=passage_id,
                    doc_id=passage["doc_id"],
                )
                meta_rows.append(
                    PoolMeta(
                        query_id=query.query_id,
                        passage_id=passage_id,
                        source="gold",
                        rank=None,
                        score=None,
                    ).model_dump()
                )
                counts["gold"] += 1

        for rank, index in enumerate(top_indices[query_index], start=1):
            passage_id = split_ids[int(index)]
            if passage_id in chosen:
                continue
            passage = passages[passage_id]
            chosen[passage_id] = PoolCandidate(
                query_id=query.query_id,
                passage_id=passage_id,
                doc_id=passage["doc_id"],
            )
            meta_rows.append(
                PoolMeta(
                    query_id=query.query_id,
                    passage_id=passage_id,
                    source="dense",
                    rank=rank,
                    score=float(scores[query_index, int(index)]),
                ).model_dump()
            )
            counts["dense"] += 1

        candidates = [pid for pid in split_ids if pid not in chosen]
        rng = random.Random(seed + int(query.query_id[1:]))
        sample_size = min(negatives, len(candidates))
        for passage_id in rng.sample(candidates, sample_size):
            if passage_id not in split_id_set:
                continue
            passage = passages[passage_id]
            chosen[passage_id] = PoolCandidate(
                query_id=query.query_id,
                passage_id=passage_id,
                doc_id=passage["doc_id"],
            )
            meta_rows.append(
                PoolMeta(
                    query_id=query.query_id,
                    passage_id=passage_id,
                    source="negative",
                    rank=None,
                    score=None,
                ).model_dump()
            )
            counts["negative"] += 1

        pool_rows.extend(
            candidate.model_dump()
            for candidate in sorted(chosen.values(), key=lambda item: item.passage_id)
        )

    write_jsonl(out_path, pool_rows)
    write_jsonl(meta_path, meta_rows)
    return PoolBuildResult(
        queries=len(queries),
        candidates=len(pool_rows),
        gold=counts["gold"],
        dense=counts["dense"],
        negatives=counts["negative"],
    )
