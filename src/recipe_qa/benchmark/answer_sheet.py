from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from .annotation import order_candidates
from .schema import PoolCandidate, Qrel, Query, VerdictQrel

RELEVANCE_FIELDS = [
    "no",
    "query_id",
    "slice",
    "as_of",
    "scope",
    "query",
    "passage_no",
    "passage_id",
    "doc_id",
    "title",
    "year",
    "section",
    "passage_text",
    "relevance",
    "notes",
]

VERDICT_FIELDS = [
    "no",
    "query_id",
    "slice",
    "query",
    "claim_id",
    "claim",
    "evidence",
    "verdict",
    "notes",
]

RELEVANCE_LABELS = {"0", "1", "2"}
VERDICT_LABELS = {"SUPPORTED", "REFUTED", "NOT_ENOUGH_EVIDENCE"}


@dataclass
class AnswerSheetReport:
    rows: int = 0
    queries: int = 0
    labels: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def build_relevance_rows(
    queries: list[Query],
    pool: dict[str, list[PoolCandidate]],
    passages: dict[str, dict],
    annotator: str = "D",
) -> list[dict]:
    rows: list[dict] = []
    number = 0
    for query in queries:
        ordered = order_candidates(pool.get(query.query_id, []), annotator)
        for passage_no, candidate in enumerate(ordered, start=1):
            passage = passages.get(candidate.passage_id)
            if passage is None:
                raise ValueError(f"{query.query_id}: unknown passage {candidate.passage_id}")
            number += 1
            rows.append(
                {
                    "no": number,
                    "query_id": query.query_id,
                    "slice": query.slice,
                    "as_of": "" if query.as_of is None else query.as_of,
                    "scope": query.scope or "",
                    "query": query.text,
                    "passage_no": passage_no,
                    "passage_id": candidate.passage_id,
                    "doc_id": candidate.doc_id,
                    "title": passage.get("source_title", ""),
                    "year": passage.get("source_year", ""),
                    "section": passage.get("section", ""),
                    "passage_text": passage.get("text", "").strip(),
                    "relevance": "",
                    "notes": "",
                }
            )
    return rows


def build_verdict_rows(
    queries: list[Query],
    qrels: list[Qrel],
    passages: dict[str, dict],
) -> list[dict]:
    by_query: dict[str, list[Qrel]] = {}
    for row in qrels:
        by_query.setdefault(row.query_id, []).append(row)

    rows: list[dict] = []
    number = 0
    for query in queries:
        if not query.gold_claims:
            continue
        evidence = sorted(
            (row for row in by_query.get(query.query_id, []) if row.relevance >= 2),
            key=lambda row: (-row.relevance, row.passage_id),
        )
        evidence_text: list[str] = []
        for row in evidence:
            passage = passages.get(row.passage_id)
            if passage is None:
                continue
            evidence_text.append(f"[{row.passage_id}]\n{passage.get('text', '').strip()}")
        evidence_cell = "\n\n".join(evidence_text)

        for index, claim in enumerate(query.gold_claims, start=1):
            number += 1
            rows.append(
                {
                    "no": number,
                    "query_id": query.query_id,
                    "slice": query.slice,
                    "query": query.text,
                    "claim_id": f"c{index}",
                    "claim": claim,
                    "evidence": evidence_cell,
                    "verdict": "",
                    "notes": "",
                }
            )
    return rows


def apply_relevance_labels(rows: list[dict], qrels: list[Qrel]) -> int:
    labels = {(row.query_id, row.passage_id): row for row in qrels}
    applied = 0
    for row in rows:
        qrel = labels.get((row["query_id"], row["passage_id"]))
        if qrel is None:
            continue
        row["relevance"] = str(qrel.relevance)
        row["notes"] = qrel.notes
        applied += 1
    return applied


def write_sheet(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp")
    with tmp_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            extrasaction="ignore",
            lineterminator="\r\n",
        )
        writer.writeheader()
        writer.writerows(rows)
    tmp_path.replace(path)


def read_sheet(path: Path, required: list[str]) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing CSV header")
        missing = [field for field in required if field not in reader.fieldnames]
        if missing:
            raise ValueError(f"{path}: missing columns {missing}")

        rows: list[dict] = []
        for line_number, row in enumerate(reader, start=2):
            values = [value for key, value in row.items() if key is not None and value is not None]
            if not any(str(value).strip() for value in values):
                continue
            row["_line"] = line_number
            rows.append(row)
    return rows


def _sheet_value(row: dict, field: str) -> str:
    value = row.get(field, "")
    return "" if value is None else str(value).strip()


def _expected_claim_keys(queries: list[Query]) -> dict[tuple[str, str], str]:
    expected: dict[tuple[str, str], str] = {}
    for query in queries:
        for index, claim in enumerate(query.gold_claims, start=1):
            expected[(query.query_id, f"c{index}")] = claim
    return expected


def import_relevance_sheet(
    sheet_path: Path,
    pool: dict[str, list[PoolCandidate]],
    passages: dict[str, dict],
    doc_version: str,
    annotator: str = "D",
) -> tuple[list[Qrel], AnswerSheetReport]:
    report = AnswerSheetReport()
    rows = read_sheet(sheet_path, ["query_id", "passage_id", "relevance"])
    report.rows = len(rows)

    pool_by_key = {
        (candidate.query_id, candidate.passage_id): candidate
        for candidates in pool.values()
        for candidate in candidates
    }
    seen: dict[tuple[str, str], int] = {}
    qrels: list[Qrel] = []

    for row in rows:
        line = row["_line"]
        query_id = _sheet_value(row, "query_id")
        passage_id = _sheet_value(row, "passage_id")
        key = (query_id, passage_id)
        if not query_id or not passage_id:
            report.errors.append(f"line {line}: query_id and passage_id are required")
            continue
        if key in seen:
            report.errors.append(f"line {line}: duplicate key {key} (first at line {seen[key]})")
            continue
        seen[key] = line

        candidate = pool_by_key.get(key)
        if candidate is None:
            report.errors.append(f"line {line}: key {key} is not in the pool")
            continue

        label = _sheet_value(row, "relevance")
        if label not in RELEVANCE_LABELS:
            report.errors.append(f"line {line}: relevance must be 0, 1, or 2; got {label!r}")
            continue

        sheet_doc_id = _sheet_value(row, "doc_id")
        if sheet_doc_id and sheet_doc_id != candidate.doc_id:
            report.errors.append(f"line {line}: doc_id does not match pool")
            continue

        passage = passages.get(passage_id)
        if passage is None:
            report.errors.append(f"line {line}: passage {passage_id} not found")
            continue
        if passage.get("split") != "test":
            report.errors.append(f"line {line}: passage {passage_id} is not in test split")
            continue

        qrels.append(
            Qrel(
                query_id=query_id,
                passage_id=passage_id,
                doc_id=candidate.doc_id,
                doc_version=doc_version,
                relevance=int(label),
                annotator=annotator,
                notes=_sheet_value(row, "notes"),
            )
        )

    missing = sorted(set(pool_by_key) - set(seen))
    extra = sorted(set(seen) - set(pool_by_key))
    if missing:
        report.errors.append(f"missing pool keys: {missing[:10]} ({len(missing)} total)")
    if extra:
        report.errors.append(f"keys outside pool: {extra[:10]} ({len(extra)} total)")

    report.queries = len({row.query_id for row in qrels})
    report.labels = dict(sorted(Counter(str(row.relevance) for row in qrels).items()))
    return sorted(qrels, key=lambda row: (row.query_id, row.passage_id)), report


def import_verdict_sheet(
    sheet_path: Path,
    queries: list[Query],
    annotator: str = "D",
) -> tuple[list[VerdictQrel], AnswerSheetReport]:
    report = AnswerSheetReport()
    rows = read_sheet(sheet_path, ["query_id", "claim_id", "verdict"])
    report.rows = len(rows)

    expected = _expected_claim_keys(queries)
    seen: dict[tuple[str, str], int] = {}
    verdicts: list[VerdictQrel] = []

    for row in rows:
        line = row["_line"]
        query_id = _sheet_value(row, "query_id")
        claim_id = _sheet_value(row, "claim_id")
        key = (query_id, claim_id)
        if not query_id or not claim_id:
            report.errors.append(f"line {line}: query_id and claim_id are required")
            continue
        if key in seen:
            report.errors.append(f"line {line}: duplicate key {key} (first at line {seen[key]})")
            continue
        seen[key] = line

        claim = expected.get(key)
        if claim is None:
            report.errors.append(f"line {line}: key {key} is not an expected claim")
            continue

        sheet_claim = _sheet_value(row, "claim")
        if sheet_claim and sheet_claim != claim:
            report.errors.append(f"line {line}: claim text was edited")
            continue

        label = _sheet_value(row, "verdict")
        if label not in VERDICT_LABELS:
            report.errors.append(
                f"line {line}: verdict must be SUPPORTED, REFUTED, or "
                f"NOT_ENOUGH_EVIDENCE; got {label!r}"
            )
            continue

        verdicts.append(
            VerdictQrel(
                query_id=query_id,
                claim_id=claim_id,
                verdict=label,
                annotator=annotator,
                notes=_sheet_value(row, "notes"),
            )
        )

    missing = sorted(set(expected) - set(seen))
    extra = sorted(set(seen) - set(expected))
    if missing:
        report.errors.append(f"missing claim keys: {missing[:10]} ({len(missing)} total)")
    if extra:
        report.errors.append(f"claim keys outside benchmark: {extra[:10]} ({len(extra)} total)")

    report.queries = len({row.query_id for row in verdicts})
    report.labels = dict(sorted(Counter(row.verdict for row in verdicts).items()))
    return sorted(verdicts, key=lambda row: (row.query_id, row.claim_id)), report
