from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from .annotation import JudgmentKey
from .schema import Qrel

DECISION_ACCEPT = "accept"
DECISION_SKIP = "skip"


def parse_decisions(raw: str, count: int) -> list[str]:
    tokens = raw.lower().split()
    if count <= 0:
        raise ValueError("jumlah kandidat harus lebih dari nol")
    if tokens == ["all"]:
        return [DECISION_ACCEPT] * count
    if len(tokens) != count:
        raise ValueError(f"perlu {count} keputusan, dapat {len(tokens)}")
    decisions: list[str] = []
    for token in tokens:
        if token in {"a", "accept"}:
            decisions.append(DECISION_ACCEPT)
        elif token in {"s", "skip"}:
            decisions.append(DECISION_SKIP)
        elif token in {"0", "1", "2"}:
            decisions.append(token)
        else:
            raise ValueError(f"token tidak dikenal: {token}")
    return decisions


def reviewed_progress(
    draft: Iterable[Qrel],
    reviewed: Iterable[Qrel],
) -> dict[str, tuple[int, int]]:
    draft_keys = {(row.query_id, row.passage_id) for row in draft}
    reviewed_keys = {JudgmentKey(row.query_id, row.passage_id) for row in reviewed}
    total_by_query = Counter(query_id for query_id, _ in draft_keys)
    done_by_query = Counter(
        query_id for query_id, passage_id in draft_keys if JudgmentKey(query_id, passage_id) in reviewed_keys
    )
    return {
        query_id: (done_by_query.get(query_id, 0), total)
        for query_id, total in sorted(total_by_query.items())
    }


def combine_review_notes(
    draft_notes: str,
    review_notes: str,
    draft_relevance: int,
    final_relevance: int,
) -> str:
    parts: list[str] = []
    if draft_notes.strip():
        parts.append(draft_notes.strip())
    if review_notes.strip():
        parts.append(f"review: {review_notes.strip()}")
    if final_relevance != draft_relevance:
        parts.append(f"override: {draft_relevance}->{final_relevance}")
    return " | ".join(parts)
