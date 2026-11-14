"""Benchmark contracts and helpers."""

from .schema import (
    GoldCandidate,
    PoolCandidate,
    PoolMeta,
    Qrel,
    Query,
    QueryFilter,
    VerdictQrel,
)
from .validate import (
    BenchmarkReport,
    load_gold,
    load_no_evidence,
    load_passages,
    load_qrels,
    load_queries,
    load_split,
    read_jsonl,
    validate_benchmark,
    write_jsonl,
)

__all__ = [
    "BenchmarkReport",
    "GoldCandidate",
    "PoolCandidate",
    "PoolMeta",
    "Qrel",
    "Query",
    "QueryFilter",
    "VerdictQrel",
    "load_gold",
    "load_no_evidence",
    "load_passages",
    "load_qrels",
    "load_queries",
    "load_split",
    "read_jsonl",
    "validate_benchmark",
    "write_jsonl",
]
