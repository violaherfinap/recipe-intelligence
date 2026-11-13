"""Shared data contracts for the corpus and index build."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SplitName = Literal["train", "dev", "test"]


class Doc(BaseModel):
    """One cleaned historical recipe."""

    model_config = ConfigDict(extra="forbid")

    doc_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    slug: str = Field(min_length=1)
    collection: str = Field(min_length=1)
    culture: str = ""
    author: str = ""
    source_title: str = ""
    source_url: str = ""
    source_year: int
    license: str = ""
    sections: dict[str, list[str]]
    text_clean: str = Field(min_length=1)
    sha256: str = Field(min_length=64, max_length=64)
    commit_sha: str = ""
    split: SplitName | None = None


class Passage(BaseModel):
    """A section-aware retrieval passage taken from a document."""

    model_config = ConfigDict(extra="forbid")

    passage_id: str = Field(min_length=1)
    doc_id: str = Field(min_length=1)
    section: str = Field(min_length=1)
    idx: int = Field(ge=0)
    text: str = Field(min_length=1)
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)
    token_count: int = Field(gt=0)
    source_year: int
    source_title: str = ""
    split: SplitName
