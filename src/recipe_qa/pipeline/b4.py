"""B4: B3 retrieval plus planner, bounded retry, verification, and abstain."""

from __future__ import annotations

import sys

from .common import pipeline_cli


def main(argv: list[str] | None = None) -> int:
    return pipeline_cli("configs/b4.yaml", argv)


if __name__ == "__main__":
    sys.exit(main())
