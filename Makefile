PYTHON := uv run python

.PHONY: setup corpus index bm25 dense test lint smoke benchmark pool all passages-fixed passages-hierarchical index-fixed index-hierarchical b2-smoke b3-smoke retrieval-smoke

setup:
	uv sync --extra dev

corpus:
	$(PYTHON) -m recipe_qa.corpus.cli build

index:
	$(PYTHON) -m recipe_qa.index.cli all

bm25:
	$(PYTHON) -m recipe_qa.index.cli bm25

dense:
	$(PYTHON) -m recipe_qa.index.cli dense

test:
	uv run pytest

lint:
	uv run ruff check src tests tools

smoke:
	$(PYTHON) -m recipe_qa.index.cli smoke --query "tomato soup"

benchmark:
	$(PYTHON) tools/validate_benchmark.py --strict

pool:
	$(PYTHON) tools/build_pool.py

passages-fixed:
	$(PYTHON) -m recipe_qa.corpus.cli passages --mode fixed --out data/processed/passages_fixed.jsonl

passages-hierarchical:
	$(PYTHON) -m recipe_qa.corpus.cli passages --mode hierarchical --out data/processed/passages_hierarchical.jsonl

index-fixed:
	$(PYTHON) -m recipe_qa.index.cli all --passages data/processed/passages_fixed.jsonl --out indexes/fixed

index-hierarchical:
	$(PYTHON) -m recipe_qa.index.cli all --passages data/processed/passages_hierarchical.jsonl --out indexes/hierarchical

b2-smoke:
	$(PYTHON) -m recipe_qa.pipeline.b2 --query-id q001 --no-generate

b3-smoke:
	$(PYTHON) -m recipe_qa.pipeline.b3 --query-id q001 --no-generate

retrieval-smoke:
	$(PYTHON) -m recipe_qa.retrieval.cli --config configs/retrieval_hybrid_rerank.yaml --limit 10

all: corpus index test
