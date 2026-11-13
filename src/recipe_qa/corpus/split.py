"""Deterministic, year-stratified train/dev/test split."""

from __future__ import annotations

import random
from collections import defaultdict
from collections.abc import Iterable, Mapping

from .schema import Doc, SplitName

RATIOS: dict[SplitName, float] = {"train": 0.70, "dev": 0.15, "test": 0.15}


def _allocate(n: int) -> tuple[int, int, int]:
    """Return (train, dev, test) sizes for one stratum."""
    if n <= 0:
        return 0, 0, 0
    if n == 1:
        return 1, 0, 0
    if n == 2:
        return 1, 1, 0

    train = int(n * RATIOS["train"])
    dev = int(n * RATIOS["dev"])
    test = n - train - dev

    if dev == 0:
        dev = 1
        train -= 1
    if test == 0:
        test = 1
        train -= 1

    # Guard against pathological small strata.
    if train < 1:
        train = 1
        if dev > test:
            dev -= 1
        else:
            test -= 1
    return train, dev, test


def assign_splits(
    docs: Iterable[Doc],
    seed: int = 42,
) -> dict[str, SplitName]:
    """Assign every doc_id to exactly one split, stratified by source_year.

    The result is deterministic for a fixed set of doc_ids and seed.
    """
    by_year: dict[int, list[str]] = defaultdict(list)
    for doc in sorted(docs, key=lambda item: item.doc_id):
        by_year[doc.source_year].append(doc.doc_id)

    rng = random.Random(seed)
    assignments: dict[str, SplitName] = {}

    for year in sorted(by_year):
        ids = by_year[year][:]
        rng.shuffle(ids)
        n_train, n_dev, _ = _allocate(len(ids))
        train_ids = ids[:n_train]
        dev_ids = ids[n_train : n_train + n_dev]
        test_ids = ids[n_train + n_dev :]
        assignments.update({doc_id: "train" for doc_id in train_ids})
        assignments.update({doc_id: "dev" for doc_id in dev_ids})
        assignments.update({doc_id: "test" for doc_id in test_ids})

    return assignments


def split_summary(
    assignments: Mapping[str, SplitName],
    docs: Iterable[Doc],
    seed: int,
) -> dict:
    """Build the JSON payload written to split.json."""
    by_split: dict[str, int] = {"train": 0, "dev": 0, "test": 0}
    by_year: dict[str, dict[str, int]] = {}
    year_lookup = {doc.doc_id: doc.source_year for doc in docs}

    for doc_id, split in assignments.items():
        by_split[split] += 1
        year = str(year_lookup[doc_id])
        by_year.setdefault(year, {"train": 0, "dev": 0, "test": 0})
        by_year[year][split] += 1

    return {
        "seed": seed,
        "ratios": dict(RATIOS),
        "counts": by_split,
        "by_year": dict(sorted(by_year.items())),
        "assignments": dict(sorted(assignments.items())),
    }
