from __future__ import annotations

import argparse
import json
from pathlib import Path

from recipe_qa.training.dataset import (
    DEFAULT_QUOTAS,
    DEFAULT_REGISTRY,
    build_examples,
    load_inputs,
    write_dataset,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the LoRA training dataset.")
    parser.add_argument("--docs", type=Path, default=Path("data/processed/docs.jsonl"))
    parser.add_argument(
        "--passages",
        type=Path,
        default=Path("data/processed/passages.jsonl"),
    )
    parser.add_argument("--out", type=Path, default=Path("train/dataset.jsonl"))
    parser.add_argument(
        "--audit-out",
        type=Path,
        default=Path("train/dataset_audit.json"),
    )
    parser.add_argument(
        "--hash-out",
        type=Path,
        default=Path("train/dataset.sha256"),
    )
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--size", type=int, default=700)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--exclude-year", type=int, default=1824)
    parser.add_argument("--split", default="train")
    parser.add_argument("--ingredients", type=int, default=DEFAULT_QUOTAS["ingredients"])
    parser.add_argument("--directions", type=int, default=DEFAULT_QUOTAS["directions"])
    parser.add_argument("--metadata", type=int, default=DEFAULT_QUOTAS["metadata"])
    parser.add_argument("--no-recipe", type=int, default=DEFAULT_QUOTAS["no_recipe"])
    parser.add_argument(
        "--out-of-period",
        type=int,
        default=DEFAULT_QUOTAS["out_of_period"],
    )
    args = parser.parse_args(argv)

    quotas = {
        "ingredients": args.ingredients,
        "directions": args.directions,
        "metadata": args.metadata,
        "no_recipe": args.no_recipe,
        "out_of_period": args.out_of_period,
    }
    docs, passages, allowed_ids, source_doc_ids = load_inputs(
        args.docs,
        args.passages,
        split=args.split,
        exclude_year=args.exclude_year,
    )
    examples = build_examples(
        docs,
        passages,
        seed=args.seed,
        size=args.size,
        quotas=quotas,
        exclude_year=args.exclude_year,
        split=args.split,
        registry=args.registry,
    )
    result = write_dataset(
        examples,
        out_path=args.out,
        audit_path=args.audit_out,
        sha256_path=args.hash_out,
        allowed_ids=allowed_ids,
        source_doc_ids=source_doc_ids,
        exclude_year=args.exclude_year,
    )
    print(json.dumps(result.audit, indent=2, ensure_ascii=False))
    print(f"written: {result.path} ({result.total} examples)")
    print(f"sha256: {result.sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
