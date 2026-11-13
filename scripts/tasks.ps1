param(
    [Parameter(Position = 0)]
    [ValidateSet("setup", "corpus", "index", "bm25", "dense", "test", "lint", "smoke", "all")]
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
    "lint"   { uv run ruff check src tests }
    "smoke"  { uv run python -m recipe_qa.index.cli smoke --query "tomato soup" }
    "all" {
        uv run python -m recipe_qa.corpus.cli build
        uv run python -m recipe_qa.index.cli all
        uv run pytest
        uv run ruff check src tests
    }
}
