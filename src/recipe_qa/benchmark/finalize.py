from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field

from pydantic import ValidationError

from .schema import Qrel, Query


@dataclass
class FinalizeReport:
    manual: int = 0
    reviewed: int = 0
    merged: int = 0
    queries: int = 0
    labels: dict[int, int] = field(default_factory=dict)
    overrides: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _key(row: dict) -> tuple[str, str]:
    return row["query_id"], row["passage_id"]


def _duplicate_keys(rows: list[dict]) -> list[tuple[str, str]]:
    counts = Counter(_key(row) for row in rows)
    return [key for key, count in counts.items() if count > 1]


def merge_qrel_rows(manual_rows: list[dict], reviewed_rows: list[dict]) -> list[dict]:
    merged = [*manual_rows, *reviewed_rows]
    return sorted(merged, key=_key)


def validate_final_qrels(
    manual_rows: list[dict],
    reviewed_rows: list[dict],
    draft_rows: list[dict],
    pool_rows: list[dict],
    queries: list[Query],
    passages: dict[str, dict],
    doc_version: str,
    annotator: str = "C",
) -> FinalizeReport:
    report = FinalizeReport(
        manual=len(manual_rows),
        reviewed=len(reviewed_rows),
        queries=len(queries),
    )

    manual_duplicates = _duplicate_keys(manual_rows)
    reviewed_duplicates = _duplicate_keys(reviewed_rows)
    if manual_duplicates:
        report.errors.append(f"duplicate manual qrels: {manual_duplicates[:10]}")
    if reviewed_duplicates:
        report.errors.append(f"duplicate reviewed qrels: {reviewed_duplicates[:10]}")

    manual_keys = {_key(row) for row in manual_rows}
    reviewed_keys = {_key(row) for row in reviewed_rows}
    draft_keys = {_key(row) for row in draft_rows}
    pool_keys = {_key(row) for row in pool_rows}
    union_keys = manual_keys | reviewed_keys
    report.merged = len(union_keys)

    overlap = manual_keys & reviewed_keys
    if overlap:
        report.errors.append(f"manual/reviewed overlap: {sorted(overlap)[:10]}")
    missing_reviewed = sorted(draft_keys - reviewed_keys)
    extra_reviewed = sorted(reviewed_keys - draft_keys)
    if missing_reviewed:
        report.errors.append(f"draft keys missing from reviewed: {missing_reviewed[:10]}")
    if extra_reviewed:
        report.errors.append(f"reviewed keys outside draft: {extra_reviewed[:10]}")
    missing_pool = sorted(union_keys - pool_keys)
    extra_pool = sorted(pool_keys - union_keys)
    if missing_pool:
        report.errors.append(f"final keys missing from pool: {missing_pool[:10]}")
    if extra_pool:
        report.errors.append(f"pool keys missing from final: {extra_pool[:10]}")

    query_ids = {query.query_id for query in queries}
    final_query_ids = {query_id for query_id, _ in union_keys}
    missing_queries = sorted(query_ids - final_query_ids)
    extra_queries = sorted(final_query_ids - query_ids)
    if missing_queries:
        report.errors.append(f"queries without qrels: {missing_queries}")
    if extra_queries:
        report.errors.append(f"qrels for unknown queries: {extra_queries}")

    by_query: dict[str, list[dict]] = defaultdict(list)
    for row in [*manual_rows, *reviewed_rows]:
        by_query[row["query_id"]].append(row)
        try:
            qrel = Qrel.model_validate(row)
        except ValidationError as exc:
            report.errors.append(f"{_key(row)}: invalid qrel: {exc}")
            continue
        if qrel.annotator != annotator:
            report.errors.append(f"{_key(row)}: annotator must be {annotator!r}")
        if qrel.doc_version != doc_version:
            report.errors.append(f"{_key(row)}: doc_version does not match corpus commit")
        passage = passages.get(qrel.passage_id)
        if passage is None:
            report.errors.append(f"{_key(row)}: passage not found")
            continue
        if qrel.doc_id != passage.get("doc_id"):
            report.errors.append(f"{_key(row)}: doc_id does not match passage")
        if passage.get("split") != "test":
            report.errors.append(f"{_key(row)}: passage is not in test split")

    for query in queries:
        rows = by_query.get(query.query_id, [])
        if not rows:
            report.errors.append(f"{query.query_id}: no qrels")
            continue
        relevances = [row.get("relevance") for row in rows]
        if query.slice == "no-evidence" and any(relevances):
            report.errors.append(f"{query.query_id}: no-evidence query has non-zero labels")
        if query.slice != "no-evidence" and 2 not in relevances:
            report.errors.append(f"{query.query_id}: answerable query has no relevance-2 passage")
        if query.slice == "multi-hop":
            twos = [row for row in rows if row.get("relevance") == 2]
            doc_ids = {row.get("doc_id") for row in twos}
            if len(twos) < 2 or len(doc_ids) < 2:
                report.warnings.append(
                    f"{query.query_id}: multi-hop has {len(twos)} relevance-2 passages "
                    f"across {len(doc_ids)} documents"
                )

    report.labels = dict(
        sorted(Counter(row.get("relevance") for row in [*manual_rows, *reviewed_rows]).items())
    )
    draft_relevances = {_key(row): row.get("relevance") for row in draft_rows}
    report.overrides = sum(
        1
        for row in reviewed_rows
        if _key(row) in draft_relevances
        and row.get("relevance") != draft_relevances[_key(row)]
    )
    return report
