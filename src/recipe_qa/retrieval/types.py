"""Small shared types for retrieval results."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Hit:
    passage_id: str
    doc_id: str
    score: float
    passage: dict = field(repr=False)
    rank: int = 0

    def to_dict(self) -> dict:
        passage = self.passage
        return {
            "rank": self.rank,
            "passage_id": self.passage_id,
            "doc_id": self.doc_id,
            "score": float(self.score),
            "section": passage.get("section"),
            "source_year": passage.get("source_year"),
            "source_title": passage.get("source_title", ""),
            "split": passage.get("split"),
            "text": passage.get("text", ""),
        }
