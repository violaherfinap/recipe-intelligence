"""High-level retrieval over one index (dense, BM25, hybrid, or hybrid+rerank)."""

from __future__ import annotations

from pathlib import Path

import bm25s
import numpy as np
import pandas as pd

from ..config import RetrievalConfig
from ..corpus.build import read_jsonl
from ..index.build import QUERY_PREFIX, tokenize_for_index
from .filters import normalize_filter, passage_matches_filter
from .fusion import reciprocal_rank_fusion
from .rerank import Reranker
from .types import Hit

INDEX_DIRS = {
    "section": Path("indexes"),
    "fixed": Path("indexes/fixed"),
    "hierarchical": Path("indexes/hierarchical"),
}
PASSAGE_PATHS = {
    "section": Path("data/processed/passages.jsonl"),
    "fixed": Path("data/processed/passages_fixed.jsonl"),
    "hierarchical": Path("data/processed/passages_hierarchical.jsonl"),
}


def resolve_index_dir(chunking: str, override: str | None = None) -> Path:
    if override:
        return Path(override)
    if chunking not in INDEX_DIRS:
        raise ValueError(f"unknown chunking mode: {chunking}")
    return INDEX_DIRS[chunking]


def resolve_passages_path(chunking: str, override: str | None = None) -> Path:
    if override:
        return Path(override)
    if chunking not in PASSAGE_PATHS:
        raise ValueError(f"unknown chunking mode: {chunking}")
    return PASSAGE_PATHS[chunking]


class BM25Searcher:
    def __init__(self, index_dir: Path, passages: list[dict]) -> None:
        self.index_dir = index_dir
        self.passages = passages
        self.retriever = bm25s.BM25.load(str(index_dir / "bm25"))

    def search(self, query: str, k: int, spec: dict | None = None) -> list[Hit]:
        query_tokens = tokenize_for_index(query)
        if not query_tokens or k <= 0:
            return []
        pool = min(max(k * 10, 200), len(self.passages))
        results, scores = self.retriever.retrieve([query_tokens], k=pool)
        hits: list[Hit] = []
        for index, score in zip(results[0], scores[0], strict=False):
            passage = self.passages[int(index)]
            if not passage_matches_filter(passage, spec):
                continue
            hits.append(
                Hit(
                    passage_id=passage["passage_id"],
                    doc_id=passage["doc_id"],
                    score=float(score),
                    passage=passage,
                    rank=len(hits) + 1,
                )
            )
            if len(hits) >= k:
                break
        return hits


class DenseSearcher:
    def __init__(self, index_dir: Path, passages: list[dict], model_name: str) -> None:
        import torch
        from sentence_transformers import SentenceTransformer

        torch.set_num_threads(8)
        self.index_dir = index_dir
        self.embeddings = np.load(index_dir / "dense.npy")
        self.meta = pd.read_parquet(index_dir / "dense_meta.parquet")
        self.ids = list(self.meta["passage_id"])
        self.by_id = {passage["passage_id"]: passage for passage in passages}
        self.model = SentenceTransformer(model_name, device="cpu")

    def search(self, query: str, k: int, spec: dict | None = None) -> list[Hit]:
        if k <= 0:
            return []
        query_vector = self.model.encode(
            [QUERY_PREFIX + query],
            normalize_embeddings=True,
            convert_to_numpy=True,
        )[0]
        scores = self.embeddings @ query_vector
        if spec:
            mask = np.asarray(
                [
                    passage_matches_filter(self.by_id.get(passage_id, {}), spec)
                    for passage_id in self.ids
                ],
                dtype=bool,
            )
            scores = np.where(mask, scores, -np.inf)

        top_indices = np.argsort(-scores)[:k]
        hits: list[Hit] = []
        for index in top_indices:
            score = float(scores[int(index)])
            if not np.isfinite(score):
                continue
            passage_id = self.ids[int(index)]
            passage = self.by_id.get(passage_id)
            if passage is None:
                continue
            hits.append(
                Hit(
                    passage_id=passage_id,
                    doc_id=passage["doc_id"],
                    score=score,
                    passage=passage,
                    rank=len(hits) + 1,
                )
            )
        return hits


class Retriever:
    def __init__(self, config: RetrievalConfig) -> None:
        self.config = config
        self.index_dir = resolve_index_dir(config.chunking, config.index_dir)
        self.passages_path = resolve_passages_path(config.chunking, config.passages)
        if not self.passages_path.exists():
            raise FileNotFoundError(
                f"passages file not found: {self.passages_path}. "
                "Build it first with `python -m recipe_qa.corpus.cli passages`."
            )
        if not self.index_dir.exists():
            raise FileNotFoundError(
                f"index directory not found: {self.index_dir}. "
                "Build it first with `python -m recipe_qa.index.cli all`."
            )
        self.passages = list(read_jsonl(self.passages_path))

        self.dense: DenseSearcher | None = None
        self.bm25: BM25Searcher | None = None
        self.reranker: Reranker | None = None

        if config.mode in {"dense", "hybrid", "hybrid_rerank"}:
            self.dense = DenseSearcher(self.index_dir, self.passages, config.model_name)
        if config.mode in {"bm25", "hybrid", "hybrid_rerank"}:
            self.bm25 = BM25Searcher(self.index_dir, self.passages)
        if config.rerank:
            self.reranker = Reranker(config.reranker_model)

    def retrieve(self, query: str, filter_spec=None) -> list[Hit]:
        mode = self.config.mode
        if mode == "none":
            return []

        spec = normalize_filter(filter_spec) if self.config.filters else None

        if mode == "dense":
            assert self.dense is not None
            k = max(self.config.final_k, self.config.top_k_dense or 0)
            return self.dense.search(query, k, spec)[: self.config.final_k]

        if mode == "bm25":
            assert self.bm25 is not None
            k = max(self.config.final_k, self.config.top_k_bm25 or 0)
            return self.bm25.search(query, k, spec)[: self.config.final_k]

        assert self.dense is not None and self.bm25 is not None
        dense_hits = self.dense.search(
            query,
            self.config.top_k_dense or self.config.final_k,
            spec,
        )
        bm25_hits = self.bm25.search(
            query,
            self.config.top_k_bm25 or self.config.final_k,
            spec,
        )

        fused = reciprocal_rank_fusion(
            [
                [hit.passage_id for hit in dense_hits],
                [hit.passage_id for hit in bm25_hits],
            ],
            k=self.config.rrf_k,
        )
        by_id = {hit.passage_id: hit for hit in [*dense_hits, *bm25_hits]}
        candidates: list[Hit] = []
        for passage_id, score in fused:
            source = by_id.get(passage_id)
            if source is None:
                continue
            candidates.append(
                Hit(
                    passage_id=passage_id,
                    doc_id=source.doc_id,
                    score=float(score),
                    passage=source.passage,
                    rank=len(candidates) + 1,
                )
            )

        if self.reranker is not None:
            candidates = candidates[: self.config.rerank_top_n]
            return self.reranker.rerank(query, candidates, top_n=self.config.final_k)

        return candidates[: self.config.final_k]

    def close(self) -> None:
        """Release model references (useful for repeated CLI runs)."""
        self.dense = None
        self.bm25 = None
        self.reranker = None
