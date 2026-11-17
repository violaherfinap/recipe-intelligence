from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

from ..benchmark.schema import Qrel, VerdictQrel


def _label(value: Any) -> str:
    return str(value)


@dataclass(frozen=True)
class AgreementResult:
    n: int
    observed: float | None
    expected: float | None
    kappa: float | None
    labels_a: dict[str, int] = field(default_factory=dict)
    labels_b: dict[str, int] = field(default_factory=dict)

    @property
    def defined(self) -> bool:
        return self.kappa is not None


@dataclass(frozen=True)
class Disagreement:
    query_id: str
    item_id: str
    label_c: str
    label_d: str


@dataclass
class AgreementReport:
    kind: str
    n: int
    observed: float | None
    expected: float | None
    kappa: float | None
    labels_c: dict[str, int] = field(default_factory=dict)
    labels_d: dict[str, int] = field(default_factory=dict)
    only_c: list[tuple[str, str]] = field(default_factory=list)
    only_d: list[tuple[str, str]] = field(default_factory=list)
    disagreements: list[Disagreement] = field(default_factory=list)

    @property
    def complete(self) -> bool:
        return not self.only_c and not self.only_d

    @property
    def ok(self) -> bool:
        return self.complete and self.kappa is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "n": self.n,
            "observed": self.observed,
            "expected": self.expected,
            "kappa": self.kappa,
            "labels_c": self.labels_c,
            "labels_d": self.labels_d,
            "only_c": [list(key) for key in self.only_c],
            "only_d": [list(key) for key in self.only_d],
            "disagreements": [
                {
                    "query_id": item.query_id,
                    "item_id": item.item_id,
                    "label_c": item.label_c,
                    "label_d": item.label_d,
                }
                for item in self.disagreements
            ],
        }


def cohen_kappa(labels_a: Sequence[Any], labels_b: Sequence[Any]) -> AgreementResult:
    if len(labels_a) != len(labels_b):
        raise ValueError("label sequences must have the same length")

    n = len(labels_a)
    if n == 0:
        return AgreementResult(n=0, observed=None, expected=None, kappa=None)

    first = [_label(label) for label in labels_a]
    second = [_label(label) for label in labels_b]
    counts_a = Counter(first)
    counts_b = Counter(second)

    observed = sum(left == right for left, right in zip(first, second, strict=True)) / n
    expected = sum(
        (counts_a[label] / n) * (counts_b[label] / n)
        for label in counts_a.keys() | counts_b.keys()
    )
    denominator = 1.0 - expected
    kappa = None if abs(denominator) < 1e-12 else (observed - expected) / denominator

    return AgreementResult(
        n=n,
        observed=observed,
        expected=expected,
        kappa=kappa,
        labels_a=dict(sorted(counts_a.items())),
        labels_b=dict(sorted(counts_b.items())),
    )


def _relevance_index(rows: Iterable[Qrel]) -> dict[tuple[str, str], Qrel]:
    index: dict[tuple[str, str], Qrel] = {}
    for row in rows:
        key = (row.query_id, row.passage_id)
        if key in index:
            raise ValueError(f"duplicate relevance key: {key}")
        index[key] = row
    return index


def _verdict_index(rows: Iterable[VerdictQrel]) -> dict[tuple[str, str], VerdictQrel]:
    index: dict[tuple[str, str], VerdictQrel] = {}
    for row in rows:
        key = (row.query_id, row.claim_id)
        if key in index:
            raise ValueError(f"duplicate verdict key: {key}")
        index[key] = row
    return index


def compare_relevance(rows_c: Iterable[Qrel], rows_d: Iterable[Qrel]) -> AgreementReport:
    first = _relevance_index(rows_c)
    second = _relevance_index(rows_d)
    keys = sorted(first.keys() | second.keys())
    only_c = [key for key in keys if key not in second]
    only_d = [key for key in keys if key not in first]
    compared = [key for key in keys if key in first and key in second]

    result = cohen_kappa(
        [first[key].relevance for key in compared],
        [second[key].relevance for key in compared],
    )
    disagreements = [
        Disagreement(
            query_id=key[0],
            item_id=key[1],
            label_c=str(first[key].relevance),
            label_d=str(second[key].relevance),
        )
        for key in compared
        if first[key].relevance != second[key].relevance
    ]

    return AgreementReport(
        kind="relevance",
        n=result.n,
        observed=result.observed,
        expected=result.expected,
        kappa=result.kappa,
        labels_c=result.labels_a,
        labels_d=result.labels_b,
        only_c=only_c,
        only_d=only_d,
        disagreements=disagreements,
    )


def compare_verdict(
    rows_c: Iterable[VerdictQrel], rows_d: Iterable[VerdictQrel]
) -> AgreementReport:
    first = _verdict_index(rows_c)
    second = _verdict_index(rows_d)
    keys = sorted(first.keys() | second.keys())
    only_c = [key for key in keys if key not in second]
    only_d = [key for key in keys if key not in first]
    compared = [key for key in keys if key in first and key in second]

    result = cohen_kappa(
        [first[key].verdict for key in compared],
        [second[key].verdict for key in compared],
    )
    disagreements = [
        Disagreement(
            query_id=key[0],
            item_id=key[1],
            label_c=first[key].verdict,
            label_d=second[key].verdict,
        )
        for key in compared
        if first[key].verdict != second[key].verdict
    ]

    return AgreementReport(
        kind="verdict",
        n=result.n,
        observed=result.observed,
        expected=result.expected,
        kappa=result.kappa,
        labels_c=result.labels_a,
        labels_d=result.labels_b,
        only_c=only_c,
        only_d=only_d,
        disagreements=disagreements,
    )
