from __future__ import annotations

import csv
import json
import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from .schema import GoldCandidate, Qrel, Query, VerdictQrel

YEAR_RE = re.compile(r"\b(17\d{2}|18\d{2})\b")
INT_RE = re.compile(r"\b\d+\b")
PASSAGE_ID_RE = re.compile(r"#(?:ingredients|directions)#\d+")
DOC_ID_RE = re.compile(r"ye-old-american:")


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_queries(path: Path) -> list[Query]:
    return [Query.model_validate(row) for row in read_jsonl(path)]


def load_gold(path: Path) -> list[GoldCandidate]:
    return [GoldCandidate.model_validate(row) for row in read_jsonl(path)]


def load_qrels(path: Path) -> list[Qrel]:
    return [Qrel.model_validate(row) for row in read_jsonl(path)]


def load_verdict_qrels(path: Path) -> list[VerdictQrel]:
    return [VerdictQrel.model_validate(row) for row in read_jsonl(path)]


def load_passages(path: Path) -> dict[str, dict]:
    return {row["passage_id"]: row for row in read_jsonl(path)}


def load_split(path: Path) -> dict[str, str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload["assignments"]


def load_no_evidence(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def check_no_evidence_coverage(queries: list[Query], rows: list[dict]) -> list[str]:
    expected = {query.query_id for query in queries if query.slice == "no-evidence"}
    seen = {row.get("query_id", "") for row in rows}
    errors: list[str] = []
    missing = sorted(expected - seen)
    if missing:
        errors.append(f"no-evidence queries without a verification row: {missing}")
    extra = sorted(seen - expected)
    if extra:
        errors.append(f"verification rows for non no-evidence queries: {extra}")
    for row in rows:
        query_id = row.get("query_id", "")
        if query_id in expected and row.get("decision") != "absent":
            errors.append(
                f"{query_id}: no-evidence decision must be 'absent', got {row.get('decision')!r}"
            )
    return errors


def _is_year(token: str) -> bool:
    value = int(token)
    return 1700 <= value <= 1900


def query_leak_warnings(
    query: Query,
    gold: GoldCandidate,
    passages: dict[str, dict],
    titles: dict[str, str],
) -> list[str]:
    warnings: list[str] = []
    lowered = query.text.lower()

    if PASSAGE_ID_RE.search(query.text) or DOC_ID_RE.search(query.text):
        warnings.append(f"{query.query_id}: query text contains a passage/doc identifier")

    query_numbers = {token for token in INT_RE.findall(query.text) if not _is_year(token)}
    claim_numbers = {
        token
        for claim in query.gold_claims
        for token in INT_RE.findall(claim)
        if not _is_year(token)
    }
    overlap = sorted(query_numbers & claim_numbers)
    if overlap:
        warnings.append(f"{query.query_id}: query repeats answer number(s) {overlap}")

    asks_for_recipe = any(
        phrase in lowered
        for phrase in ("which recipe", "which two", "what recipe", "which of the recipes")
    )
    if asks_for_recipe:
        for doc_id in gold.doc_ids:
            title = titles.get(doc_id, "")
            if title and title.lower() in lowered:
                warnings.append(f"{query.query_id}: query contains gold recipe title {title!r}")

    return warnings


@dataclass
class BenchmarkReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_benchmark(
    queries_path: Path,
    gold_path: Path,
    passages_path: Path,
    split_path: Path,
    no_evidence_path: Path | None = None,
    docs_path: Path | None = None,
) -> BenchmarkReport:
    report = BenchmarkReport()
    queries = load_queries(queries_path)
    gold_rows = load_gold(gold_path)
    passages = load_passages(passages_path)
    split = load_split(split_path)

    titles: dict[str, str] = {}
    if docs_path is not None and docs_path.exists():
        titles = {row["doc_id"]: row.get("title", "") for row in read_jsonl(docs_path)}

    expected_slices = {"easy": 35, "multi-hop": 25, "temporal": 30, "no-evidence": 25}
    if len(queries) != 115:
        report.errors.append(f"expected 115 queries, got {len(queries)}")

    ids = [query.query_id for query in queries]
    if len(ids) != len(set(ids)):
        duplicates = [item for item, count in Counter(ids).items() if count > 1]
        report.errors.append(f"duplicate query_id: {duplicates}")
    expected_ids = [f"q{index:03d}" for index in range(1, 116)]
    if ids != expected_ids:
        report.errors.append("query_id must be q001..q115 in order")

    texts = [query.text.strip().lower() for query in queries]
    if len(texts) != len(set(texts)):
        report.errors.append("query texts are not unique")

    slice_counts = Counter(query.slice for query in queries)
    report.counts = dict(slice_counts)
    for slice_name, expected in expected_slices.items():
        if slice_counts.get(slice_name, 0) != expected:
            report.errors.append(
                f"slice {slice_name!r}: expected {expected}, got {slice_counts.get(slice_name, 0)}"
            )

    gold_by_query = {row.query_id: row for row in gold_rows}
    query_by_id = {query.query_id: query for query in queries}
    if len(gold_by_query) != len(gold_rows):
        report.errors.append("duplicate gold candidate rows")
    unknown_gold = sorted(set(gold_by_query) - set(query_by_id))
    if unknown_gold:
        report.errors.append(f"gold candidates for unknown queries: {unknown_gold}")

    for query in queries:
        if query.text.strip() != query.text:
            report.errors.append(f"{query.query_id}: leading/trailing whitespace in text")
        if not query.text[0].isupper():
            report.errors.append(f"{query.query_id}: query text should start uppercase")
        if len(query.text.split()) > 45:
            report.errors.append(f"{query.query_id}: query text is longer than 45 words")
        if query.as_of is not None and not (1700 <= query.as_of <= 2100):
            report.errors.append(f"{query.query_id}: as_of out of range")

        if query.filter and query.filter.year_min and query.filter.year_max:
            if query.filter.year_min > query.filter.year_max:
                report.errors.append(f"{query.query_id}: year_min > year_max")
        if query.as_of and query.filter and query.filter.year_max:
            if query.filter.year_max > query.as_of:
                report.errors.append(f"{query.query_id}: filter.year_max exceeds as_of")

        if query.slice == "no-evidence":
            if query.query_id in gold_by_query:
                report.errors.append(f"{query.query_id}: no-evidence query has gold candidates")
            continue

        gold = gold_by_query.get(query.query_id)
        if gold is None:
            report.errors.append(f"{query.query_id}: answerable query has no gold candidates")
            continue

        if not gold.passage_ids:
            report.errors.append(f"{query.query_id}: empty gold passage list")
        missing = [pid for pid in gold.passage_ids if pid not in passages]
        if missing:
            report.errors.append(f"{query.query_id}: unknown gold passages {missing}")
            continue
        non_test = [pid for pid in gold.passage_ids if passages[pid].get("split") != "test"]
        if non_test:
            report.errors.append(f"{query.query_id}: gold passages outside test split {non_test}")
        bad_split = [
            pid for pid in gold.passage_ids if split.get(passages[pid]["doc_id"]) != "test"
        ]
        if bad_split:
            report.errors.append(f"{query.query_id}: split.json disagrees for {bad_split}")

        if query.as_of is not None:
            after = [
                pid for pid in gold.passage_ids if passages[pid].get("source_year", 0) > query.as_of
            ]
            if after:
                report.errors.append(f"{query.query_id}: gold passages newer than as_of: {after}")

        years = {passages[pid].get("source_year") for pid in gold.passage_ids}
        books = {passages[pid].get("source_title") for pid in gold.passage_ids}
        doc_ids = {passages[pid]["doc_id"] for pid in gold.passage_ids}

        if query.slice in {"multi-hop", "temporal"} and len(doc_ids) < 2:
            report.errors.append(
                f"{query.query_id}: {query.slice} needs at least two distinct documents"
            )
        if query.slice == "temporal" and len(years) < 2:
            report.errors.append(
                f"{query.query_id}: temporal query needs at least two source years"
            )
        if query.slice == "temporal" and len(books) < 2:
            report.errors.append(f"{query.query_id}: temporal query needs at least two books")
        if query.slice == "easy" and len(gold.passage_ids) < 1:
            report.errors.append(f"{query.query_id}: easy query needs a gold passage")
        if not query.gold_claims:
            report.errors.append(f"{query.query_id}: answerable query has no gold claims")

        report.warnings.extend(query_leak_warnings(query, gold, passages, titles))

    if no_evidence_path is not None:
        if not no_evidence_path.exists():
            report.errors.append(f"missing no-evidence file: {no_evidence_path}")
        else:
            report.errors.extend(
                check_no_evidence_coverage(queries, load_no_evidence(no_evidence_path))
            )

    return report
