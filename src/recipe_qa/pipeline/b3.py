"""B3: BM25 + dense fusion, cross-encoder rerank, top-10, then generate."""

from __future__ import annotations

import sys

from .common import pipeline_cli


def main(argv: list[str] | None = None) -> int:
    return pipeline_cli("configs/b3.yaml", argv)


if __name__ == "__main__":
    sys.exit(main())
