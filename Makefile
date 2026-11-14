PYTHON := uv run python

.PHONY: setup corpus index bm25 dense test lint smoke all

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

all: corpus index test
