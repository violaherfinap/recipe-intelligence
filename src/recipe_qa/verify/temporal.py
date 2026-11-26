from __future__ import annotations

import re
from dataclasses import dataclass

from ..generation.schema import AnswerPayload

YEAR_RE = re.compile(r"\b(1[5-9]\d{2}|20\d{2})\b")


def claim_years(text: str) -> list[int]:
    return sorted({int(year) for year in YEAR_RE.findall(text)})


@dataclass(frozen=True)
class TemporalReport:
    as_of: int | None
    claims: int
    after_as_of: int
    evidence_after_as_of: int
    year_mismatches: int
    violations: list[str]

    @property
    def ok(self) -> bool:
        return self.after_as_of == 0 and self.evidence_after_as_of == 0

    def to_dict(self) -> dict:
        return {
            "as_of": self.as_of,
            "claims": self.claims,
            "after_as_of": self.after_as_of,
            "evidence_after_as_of": self.evidence_after_as_of,
            "year_mismatches": self.year_mismatches,
            "violations": self.violations,
            "ok": self.ok,
        }


def _source_year(item, by_id: dict) -> int | None:
    if item.source_year is not None:
        return item.source_year
    hit = by_id.get(item.passage_id)
    if hit is None:
        return None
    year = hit.passage.get("source_year")
    return int(year) if year is not None else None


def check_temporal(
    payload: AnswerPayload,
    hits: list,
    as_of: int | None = None,
) -> TemporalReport:
    if payload.abstain or not payload.claims:
        return TemporalReport(
            as_of=as_of,
            claims=len(payload.claims),
            after_as_of=0,
            evidence_after_as_of=0,
            year_mismatches=0,
            violations=[],
        )

    by_id = {hit.passage_id: hit for hit in hits}
    after_as_of = 0
    evidence_after_as_of = 0
    year_mismatches = 0
    violations: list[str] = []

    for claim in payload.claims:
        limit = claim.as_of if claim.as_of is not None else as_of
        years = claim_years(claim.claim)
        if limit is not None:
            newer = [year for year in years if year > limit]
            if newer:
                after_as_of += 1
                violations.append(f"{claim.claim_id}: claim years {newer} exceed as_of {limit}")
            for item in [*claim.evidence_for, *claim.evidence_against]:
                year = _source_year(item, by_id)
                if year is not None and year > limit:
                    evidence_after_as_of += 1
                    violations.append(
                        f"{claim.claim_id}: evidence {item.passage_id} year {year} "
                        f"exceeds as_of {limit}"
                    )
        if len(years) == 1:
            for item in [*claim.evidence_for, *claim.evidence_against]:
                year = _source_year(item, by_id)
                if year is not None and year != years[0]:
                    year_mismatches += 1
                    violations.append(
                        f"{claim.claim_id}: claim year {years[0]} but evidence "
                        f"{item.passage_id} year {year}"
                    )

    return TemporalReport(
        as_of=as_of,
        claims=len(payload.claims),
        after_as_of=after_as_of,
        evidence_after_as_of=evidence_after_as_of,
        year_mismatches=year_mismatches,
        violations=violations,
    )
