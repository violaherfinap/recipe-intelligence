from __future__ import annotations

import re
from dataclasses import dataclass

from ..generation.schema import AnswerPayload

_WHITESPACE_RE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text).strip().lower()


@dataclass(frozen=True)
class CitationReport:
    claims: int
    cited: int
    unknown_passages: list[str]
    span_mismatches: int
    missing_evidence: int
    coverage: float

    @property
    def ok(self) -> bool:
        return not self.unknown_passages and self.span_mismatches == 0

    def to_dict(self) -> dict:
        return {
            "claims": self.claims,
            "cited": self.cited,
            "coverage": self.coverage,
            "unknown_passages": self.unknown_passages,
            "span_mismatches": self.span_mismatches,
            "missing_evidence": self.missing_evidence,
            "ok": self.ok,
        }


def check_citations(
    payload: AnswerPayload,
    hits: list,
    span_chars: int = 80,
) -> CitationReport:
    if payload.abstain or not payload.claims:
        return CitationReport(
            claims=len(payload.claims),
            cited=0,
            unknown_passages=[],
            span_mismatches=0,
            missing_evidence=0,
            coverage=0.0,
        )

    by_id = {hit.passage_id: hit for hit in hits}
    unknown: set[str] = set()
    cited = 0
    span_mismatches = 0
    missing_evidence = 0

    for claim in payload.claims:
        evidence = [*claim.evidence_for, *claim.evidence_against]
        if evidence:
            cited += 1
        else:
            missing_evidence += 1
        for item in evidence:
            hit = by_id.get(item.passage_id)
            if hit is None:
                unknown.add(item.passage_id)
                continue
            span = _normalize(item.span)
            if not span:
                continue
            source = _normalize(str(hit.passage.get("text", "")))
            if span[:span_chars] not in source:
                span_mismatches += 1

    claims = len(payload.claims)
    return CitationReport(
        claims=claims,
        cited=cited,
        unknown_passages=sorted(unknown),
        span_mismatches=span_mismatches,
        missing_evidence=missing_evidence,
        coverage=cited / claims,
    )
