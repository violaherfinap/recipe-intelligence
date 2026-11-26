"""Output contract for generated answers."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Verdict = Literal["SUPPORTED", "REFUTED", "NOT_ENOUGH_EVIDENCE"]
AbstainReason = Literal[
    "no_recipe",
    "not_specified",
    "out_of_period",
    "conflicting_sources",
    "format_error",
    "citation_failure",
    "temporal_violation",
]


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passage_id: str
    doc_id: str
    source_year: int | None = None
    span: str = ""


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_id: str
    claim: str
    verdict: Verdict
    as_of: int | None = None
    evidence_for: list[EvidenceItem] = Field(default_factory=list)
    evidence_against: list[EvidenceItem] = Field(default_factory=list)


class AnswerPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query_id: str
    answer: str = ""
    claims: list[Claim] = Field(default_factory=list)
    abstain: bool = False
    abstain_reason: AbstainReason | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    schema_valid: bool = True
