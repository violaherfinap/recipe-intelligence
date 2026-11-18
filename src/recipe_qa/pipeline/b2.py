"""B2: dense retrieval over fixed chunks, top-5, then generate."""

from __future__ import annotations

import sys

from .common import pipeline_cli


def main(argv: list[str] | None = None) -> int:
    return pipeline_cli("configs/b2.yaml", argv)


if __name__ == "__main__":
    sys.exit(main())
