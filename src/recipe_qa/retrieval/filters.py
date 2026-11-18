"""Metadata filters for query-time passage selection."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np


def normalize_filter(spec) -> dict | None:
    if spec is None:
        return None
    if hasattr(spec, "model_dump"):
        spec = spec.model_dump()
    if not isinstance(spec, dict):
        return None
    cleaned = {key: value for key, value in spec.items() if value is not None}
    return cleaned or None


def passage_matches_filter(passage: dict, spec: dict | None) -> bool:
    if not spec:
        return True

    year = passage.get("source_year")
    year_min = spec.get("year_min")
    year_max = spec.get("year_max")
    if year_min is not None and (year is None or int(year) < int(year_min)):
        return False
    if year_max is not None and (year is None or int(year) > int(year_max)):
        return False

    book = spec.get("book")
    if book:
        source_title = str(passage.get("source_title") or "").lower()
        if str(book).lower() not in source_title:
            return False

    section = spec.get("section")
    if section:
        actual = str(passage.get("section") or "")
        allowed = {str(section)}
        if section == "directions":
            allowed.add("step")
        if section == "ingredients":
            allowed.add("summary")
        if actual not in allowed:
            return False

    return True


def filter_mask(passages: Iterable[dict], spec: dict | None) -> np.ndarray:
    return np.asarray(
        [passage_matches_filter(passage, spec) for passage in passages],
        dtype=bool,
    )
