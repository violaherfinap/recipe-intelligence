"""Retrieval primitives: dense, BM25, RRF fusion, reranking, filters."""

from .fusion import reciprocal_rank_fusion
from .search import BM25Searcher, DenseSearcher, Retriever
from .types import Hit

__all__ = [
    "BM25Searcher",
    "DenseSearcher",
    "Hit",
    "Retriever",
    "reciprocal_rank_fusion",
]
