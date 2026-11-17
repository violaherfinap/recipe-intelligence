from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from ..eval.agreement import AgreementReport, compare_relevance, compare_verdict
from .schema import Qrel, Query, VerdictQrel
from .validate import read_jsonl, write_jsonl

AdjudicationKind = Literal["relevance", "verdict"]
RELEVANCE_LABELS = {"0", "1", "2"}
VERDICT_LABELS = {"SUPPORTED", "REFUTED", "NOT_ENOUGH_EVIDENCE"}


@dataclass(frozen=True)
class AdjudicationDecision:
    kind: AdjudicationKind
    query_id: str
    item_id: str
    label_c: str
    label_d: str
    final: str
    notes: str = ""

    @property
    def key(self) -> tuple[str, str, str]:
        return self.kind, self.query_id, self.item_id


@dataclass
class FinalizeReport:
    qrels: list[Qrel] = field(default_factory=list)
    verdicts: list[VerdictQrel] = field(default_factory=list)
    relevance: AgreementReport | None = None
    verdict: AgreementReport | None = None
    relevance_labels: dict[int, int] = field(default_factory=dict)
    verdict_labels: dict[str, int] = field(default_factory=dict)
    conflicts: int = 0
    resolved: int = 0
    missing_c: int = 0
    missing_d: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _validate_decision(row: dict) -> AdjudicationDecision:
    kind = str(row.get("kind", ""))
    if kind not in {"relevance", "verdict"}:
        raise ValueError(f"invalid decision kind: {kind!r}")

    final = str(row.get("final", ""))
    allowed = RELEVANCE_LABELS if kind == "relevance" else VERDICT_LABELS
    if final not in allowed:
        raise ValueError(f"invalid final {kind} label: {final!r}")

    query_id = str(row.get("query_id", ""))
    item_id = str(row.get("item_id", ""))
    if not query_id or not item_id:
        raise ValueError("decision needs query_id and item_id")

    return AdjudicationDecision(
        kind=kind,
        query_id=query_id,
        item_id=item_id,
        label_c=str(row.get("label_c", "")),
        label_d=str(row.get("label_d", "")),
        final=final,
        notes=str(row.get("notes", "")),
    )


def load_decisions(path: Path | None) -> dict[tuple[str, str, str], AdjudicationDecision]:
    if path is None or not path.exists():
        return {}
    decisions: dict[tuple[str, str, str], AdjudicationDecision] = {}
    for row in read_jsonl(path):
        decision = _validate_decision(row)
        if decision.key in decisions:
            raise ValueError(f"duplicate adjudication decision: {decision.key}")
        decisions[decision.key] = decision
    return decisions


def _decision_note(
    current: Qrel | VerdictQrel,
    other: Qrel | VerdictQrel | None,
    decision: AdjudicationDecision | None,
    label: str,
    missing: str,
) -> str:
    if other is None:
        return f"missing {missing} label; used {label}"

    left = getattr(current, "relevance", getattr(current, "verdict", ""))
    right = getattr(other, "relevance", getattr(other, "verdict", ""))
    if str(left) == str(right):
        return current.notes

    note = f"adjudicated: C={left}; D={right}; final={label}"
    if decision is not None and decision.notes:
        note = f"{note}; {decision.notes}"
    return note


def _resolve_pair(
    kind: AdjudicationKind,
    query_id: str,
    item_id: str,
    label_c: str | None,
    label_d: str | None,
    decisions: dict[tuple[str, str, str], AdjudicationDecision],
    used: set[tuple[str, str, str]],
    allow_missing: bool,
    report: FinalizeReport,
) -> str | None:
    if label_c is None:
        report.missing_c += 1
        if not allow_missing:
            report.errors.append(f"{kind} {query_id}/{item_id}: missing C label")
            return None
        report.warnings.append(f"{kind} {query_id}/{item_id}: missing C label; using D")
        return label_d
    if label_d is None:
        report.missing_d += 1
        if not allow_missing:
            report.errors.append(f"{kind} {query_id}/{item_id}: missing D label")
            return None
        report.warnings.append(f"{kind} {query_id}/{item_id}: missing D label; using C")
        return label_c

    key = (kind, query_id, item_id)
    decision = decisions.get(key)
    if label_c == label_d:
        if decision is not None:
            report.warnings.append(f"{kind} {query_id}/{item_id}: decision for non-conflict ignored")
            used.add(key)
        return label_c

    report.conflicts += 1
    if decision is None:
        report.errors.append(f"{kind} {query_id}/{item_id}: unresolved conflict C={label_c} D={label_d}")
        return None

    used.add(key)
    if decision.label_c != label_c or decision.label_d != label_d:
        report.errors.append(
            f"{kind} {query_id}/{item_id}: stale decision "
            f"(file C={decision.label_c} D={decision.label_d}, "
            f"actual C={label_c} D={label_d})"
        )
        return None

    report.resolved += 1
    return decision.final


def _relevance_note(
    row: Qrel,
    other: Qrel | None,
    decision: AdjudicationDecision | None,
    label: str,
    missing: str,
) -> str:
    return _decision_note(row, other, decision, label, missing)


def _verdict_note(
    row: VerdictQrel,
    other: VerdictQrel | None,
    decision: AdjudicationDecision | None,
    label: str,
    missing: str,
) -> str:
    return _decision_note(row, other, decision, label, missing)


def build_final_qrels(
    rows_c: list[Qrel],
    rows_d: list[Qrel],
    pool_rows: list[dict],
    doc_version: str,
    decisions: dict[tuple[str, str, str], AdjudicationDecision] | None = None,
    annotator: str = "D",
    allow_missing: bool = False,
    report: FinalizeReport | None = None,
) -> tuple[list[Qrel], FinalizeReport]:
    report = report or FinalizeReport()
    decisions = decisions or {}
    used: set[tuple[str, str, str]] = set()

    first = {(row.query_id, row.passage_id): row for row in rows_c}
    second = {(row.query_id, row.passage_id): row for row in rows_d}
    if len(first) != len(rows_c):
        report.errors.append("duplicate C relevance rows")
    if len(second) != len(rows_d):
        report.errors.append("duplicate D relevance rows")

    pool = {(row["query_id"], row["passage_id"]): row for row in pool_rows}
    if len(pool) != len(pool_rows):
        report.errors.append("duplicate pool keys")

    extra_c = sorted(first.keys() - pool.keys())
    extra_d = sorted(second.keys() - pool.keys())
    if extra_c:
        report.errors.append(f"C relevance rows outside pool: {extra_c[:10]}")
    if extra_d:
        report.errors.append(f"D relevance rows outside pool: {extra_d[:10]}")

    final_rows: list[Qrel] = []
    for query_id, passage_id in sorted(pool):
        item_id = passage_id
        row_c = first.get((query_id, passage_id))
        row_d = second.get((query_id, passage_id))
        label_c = None if row_c is None else str(row_c.relevance)
        label_d = None if row_d is None else str(row_d.relevance)
        final = _resolve_pair(
            "relevance",
            query_id,
            item_id,
            label_c,
            label_d,
            decisions,
            used,
            allow_missing,
            report,
        )
        if final is None:
            continue

        source = row_c or row_d
        assert source is not None
        other = row_d if source is row_c else row_c
        decision = decisions.get(("relevance", query_id, passage_id))
        pool_row = pool[(query_id, passage_id)]
        if source.doc_id != pool_row.get("doc_id"):
            report.errors.append(f"{query_id}/{passage_id}: doc_id does not match pool")
        if source.doc_version != doc_version:
            report.errors.append(f"{query_id}/{passage_id}: doc_version does not match corpus")
        if other is not None and other.doc_id != source.doc_id:
            report.errors.append(f"{query_id}/{passage_id}: C/D doc_id mismatch")
        if other is not None and other.doc_version != doc_version:
            report.errors.append(f"{query_id}/{passage_id}: D doc_version does not match corpus")

        final_rows.append(
            Qrel(
                query_id=query_id,
                passage_id=passage_id,
                doc_id=pool_row.get("doc_id", source.doc_id),
                doc_version=source.doc_version,
                relevance=int(final),
                annotator=annotator,
                notes=_relevance_note(
                    source,
                    other,
                    decision,
                    final,
                    "pass 2" if row_c is not None else "pass 1",
                ),
            )
        )

    unused = {key for key in decisions if key[0] == "relevance"} - used
    for decision_kind, query_id, item_id in sorted(unused):
        report.errors.append(
            f"{decision_kind} {query_id}/{item_id}: decision has no matching conflict"
        )

    report.relevance_labels = dict(sorted(Counter(row.relevance for row in final_rows).items()))
    return final_rows, report


def _expected_verdict_keys(queries: list[Query]) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    for query in queries:
        for index, _claim in enumerate(query.gold_claims, start=1):
            keys.add((query.query_id, f"c{index}"))
    return keys


def build_final_verdicts(
    rows_c: list[VerdictQrel],
    rows_d: list[VerdictQrel],
    queries: list[Query],
    decisions: dict[tuple[str, str, str], AdjudicationDecision] | None = None,
    annotator: str = "D",
    allow_missing: bool = False,
    report: FinalizeReport | None = None,
) -> tuple[list[VerdictQrel], FinalizeReport]:
    report = report or FinalizeReport()
    decisions = decisions or {}
    used: set[tuple[str, str, str]] = set()

    first = {(row.query_id, row.claim_id): row for row in rows_c}
    second = {(row.query_id, row.claim_id): row for row in rows_d}
    if len(first) != len(rows_c):
        report.errors.append("duplicate C verdict rows")
    if len(second) != len(rows_d):
        report.errors.append("duplicate D verdict rows")

    expected = _expected_verdict_keys(queries)
    extra_c = sorted(first.keys() - expected)
    extra_d = sorted(second.keys() - expected)
    if extra_c:
        report.errors.append(f"C verdict rows outside expected claims: {extra_c[:10]}")
    if extra_d:
        report.errors.append(f"D verdict rows outside expected claims: {extra_d[:10]}")

    final_rows: list[VerdictQrel] = []
    for query_id, claim_id in sorted(expected):
        row_c = first.get((query_id, claim_id))
        row_d = second.get((query_id, claim_id))
        label_c = None if row_c is None else row_c.verdict
        label_d = None if row_d is None else row_d.verdict
        final = _resolve_pair(
            "verdict",
            query_id,
            claim_id,
            label_c,
            label_d,
            decisions,
            used,
            allow_missing,
            report,
        )
        if final is None:
            continue

        source = row_c or row_d
        assert source is not None
        other = row_d if source is row_c else row_c
        decision = decisions.get(("verdict", query_id, claim_id))
        final_rows.append(
            VerdictQrel(
                query_id=query_id,
                claim_id=claim_id,
                verdict=final,
                annotator=annotator,
                notes=_verdict_note(
                    source,
                    other,
                    decision,
                    final,
                    "pass 2" if row_c is not None else "pass 1",
                ),
            )
        )

    unused = {key for key in decisions if key[0] == "verdict"} - used
    for decision_kind, query_id, item_id in sorted(unused):
        report.errors.append(
            f"{decision_kind} {query_id}/{item_id}: decision has no matching conflict"
        )

    report.verdict_labels = dict(sorted(Counter(row.verdict for row in final_rows).items()))
    return final_rows, report


def build_final_benchmark(
    rows_qrels_c: list[Qrel],
    rows_qrels_d: list[Qrel],
    rows_verdict_c: list[VerdictQrel],
    rows_verdict_d: list[VerdictQrel],
    pool_rows: list[dict],
    queries: list[Query],
    passages: dict[str, dict],
    doc_version: str,
    decisions: dict[tuple[str, str, str], AdjudicationDecision] | None = None,
    annotator: str = "D",
    allow_missing: bool = False,
) -> FinalizeReport:
    report = FinalizeReport()
    report.relevance = compare_relevance(rows_qrels_c, rows_qrels_d)
    report.verdict = compare_verdict(rows_verdict_c, rows_verdict_d)

    qrels, report = build_final_qrels(
        rows_c=rows_qrels_c,
        rows_d=rows_qrels_d,
        pool_rows=pool_rows,
        doc_version=doc_version,
        decisions=decisions,
        annotator=annotator,
        allow_missing=allow_missing,
        report=report,
    )
    verdicts, report = build_final_verdicts(
        rows_c=rows_verdict_c,
        rows_d=rows_verdict_d,
        queries=queries,
        decisions=decisions,
        annotator=annotator,
        allow_missing=allow_missing,
        report=report,
    )
    report.qrels = qrels
    report.verdicts = verdicts

    qrels_by_query: dict[str, list[Qrel]] = {}
    for row in qrels:
        qrels_by_query.setdefault(row.query_id, []).append(row)
        passage = passages.get(row.passage_id)
        if passage is None:
            report.errors.append(f"{row.query_id}/{row.passage_id}: passage not found")
            continue
        if passage.get("split") != "test":
            report.errors.append(f"{row.query_id}/{row.passage_id}: passage is not in test split")

    for query in queries:
        rows = qrels_by_query.get(query.query_id, [])
        if not rows:
            report.errors.append(f"{query.query_id}: no final qrels")
            continue
        if query.slice == "no-evidence" and any(row.relevance for row in rows):
            report.errors.append(f"{query.query_id}: no-evidence query has non-zero labels")
        if query.slice != "no-evidence" and not any(row.relevance == 2 for row in rows):
            report.errors.append(f"{query.query_id}: answerable query has no relevance-2 passage")

    return report


def split_doc_ids(passages: dict[str, dict], split: str = "test") -> list[str]:
    return sorted(
        {
            row["doc_id"]
            for row in passages.values()
            if row.get("split") == split
        }
    )


def write_test_docs(path: Path, doc_ids: list[str]) -> None:
    _write_text(path, "".join(f"{doc_id}\n" for doc_id in doc_ids))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest(path: Path, files: list[Path], base: Path) -> list[str]:
    lines: list[str] = []
    for file_path in files:
        try:
            relative = file_path.resolve().relative_to(base.resolve()).as_posix()
        except ValueError:
            relative = file_path.name
        lines.append(f"{sha256_file(file_path)}  {relative}")
    _write_text(path, "\n".join(lines) + "\n")
    return lines


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp")
    tmp_path.write_text(text, encoding="utf-8", newline="\n")
    tmp_path.replace(path)


def write_jsonl_atomic(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp")
    write_jsonl(tmp_path, rows)
    tmp_path.replace(path)
