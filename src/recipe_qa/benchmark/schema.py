from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Slice = Literal["easy", "multi-hop", "temporal", "no-evidence"]
Section = Literal["ingredients", "directions"]
Verdict = Literal["SUPPORTED", "REFUTED", "NOT_ENOUGH_EVIDENCE"]


class QueryFilter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    year_min: int | None = None
    year_max: int | None = None
    book: str | None = None
    section: Section | None = None


class Query(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query_id: str = Field(pattern=r"^q\d{3}$")
    text: str = Field(min_length=10)
    slice: Slice
    scope: str | None = None
    as_of: int | None = None
    filter: QueryFilter | None = None
    gold_claims: list[str] = Field(default_factory=list)
    notes: str = ""
    author: str = "B"

    @model_validator(mode="after")
    def _temporal_requires_as_of(self) -> Query:
        if self.slice == "temporal" and self.as_of is None:
            raise ValueError("temporal queries must declare as_of")
        if self.slice == "no-evidence" and self.gold_claims:
            raise ValueError("no-evidence queries must not declare gold claims")
        return self


class GoldCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query_id: str = Field(pattern=r"^q\d{3}$")
    passage_ids: list[str] = Field(min_length=1)
    doc_ids: list[str] = Field(min_length=1)
    source: Literal["author"] = "author"


class PoolCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query_id: str = Field(pattern=r"^q\d{3}$")
    passage_id: str
    doc_id: str


class PoolMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query_id: str = Field(pattern=r"^q\d{3}$")
    passage_id: str
    source: Literal["gold", "dense", "negative", "retrieval"]
    run_id: str | None = None
    chunking: str | None = None
    rank: int | None = None
    score: float | None = None


class Qrel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query_id: str = Field(pattern=r"^q\d{3}$")
    passage_id: str
    doc_id: str
    doc_version: str = Field(min_length=40)
    relevance: Literal[0, 1, 2]
    annotator: str = Field(min_length=1)
    notes: str = ""


class VerdictQrel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query_id: str = Field(pattern=r"^q\d{3}$")
    claim_id: str = Field(min_length=1)
    verdict: Verdict
    annotator: str = Field(min_length=1)
    notes: str = ""
