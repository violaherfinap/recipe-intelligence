param(
    [Parameter(Position = 0)]
    [ValidateSet(
        "setup", "corpus", "index", "bm25", "dense", "test", "lint", "smoke",
        "benchmark", "pool", "all", "passages-fixed", "passages-hierarchical",
        "index-fixed", "index-hierarchical", "b2-smoke", "b3-smoke", "retrieval-smoke"
    )]
    [string]$Task = "all"
)

$ErrorActionPreference = "Stop"

switch ($Task) {
    "setup"  { uv sync --extra dev }
    "corpus" { uv run python -m recipe_qa.corpus.cli build }
    "index"  { uv run python -m recipe_qa.index.cli all }
    "bm25"   { uv run python -m recipe_qa.index.cli bm25 }
    "dense"  { uv run python -m recipe_qa.index.cli dense }
    "test"   { uv run pytest }
    "lint"   { uv run ruff check src tests tools }
    "smoke"  { uv run python -m recipe_qa.index.cli smoke --query "tomato soup" }
    "benchmark" { uv run python tools/validate_benchmark.py --strict }
    "pool"   { uv run python tools/build_pool.py }
    "passages-fixed" { uv run python -m recipe_qa.corpus.cli passages --mode fixed --out data/processed/passages_fixed.jsonl }
    "passages-hierarchical" { uv run python -m recipe_qa.corpus.cli passages --mode hierarchical --out data/processed/passages_hierarchical.jsonl }
    "index-fixed" { uv run python -m recipe_qa.index.cli all --passages data/processed/passages_fixed.jsonl --out indexes/fixed }
    "index-hierarchical" { uv run python -m recipe_qa.index.cli all --passages data/processed/passages_hierarchical.jsonl --out indexes/hierarchical }
    "b2-smoke" { uv run python -m recipe_qa.pipeline.b2 --query-id q001 --no-generate }
    "b3-smoke" { uv run python -m recipe_qa.pipeline.b3 --query-id q001 --no-generate }
    "retrieval-smoke" { uv run python -m recipe_qa.retrieval.cli --config configs/retrieval_hybrid_rerank.yaml --limit 10 }
    "all" {
        uv run python -m recipe_qa.corpus.cli build
        uv run python -m recipe_qa.index.cli all
        uv run pytest
        uv run ruff check src tests
    }
}
