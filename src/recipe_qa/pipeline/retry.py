"""Bounded rule-based query reformulation for B4 retries."""

from __future__ import annotations

from dataclasses import dataclass

from ..config import RetryConfig

_EXPANSIONS = ("recipe", "ingredients directions")


@dataclass(frozen=True)
class RetryPlan:
    queries: tuple[str, ...]

    def to_dict(self) -> dict:
        return {"queries": list(self.queries)}


class RetryPolicy:
    def __init__(self, config: RetryConfig) -> None:
        self.config = config

    def plan(self, query: str) -> RetryPlan:
        attempts = max(0, int(self.config.max_retries))
        if not self.config.enabled or attempts == 0:
            return RetryPlan((query,))
        queries = [query]
        for attempt in range(attempts):
            suffix = _EXPANSIONS[attempt % len(_EXPANSIONS)]
            candidate = f"{query} {suffix}"
            if candidate not in queries:
                queries.append(candidate)
        return RetryPlan(tuple(queries))
