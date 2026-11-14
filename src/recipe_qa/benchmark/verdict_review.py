from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

VERDICT_SHORTCUTS = {
    "s": "SUPPORTED",
    "supported": "SUPPORTED",
    "r": "REFUTED",
    "refuted": "REFUTED",
    "n": "NOT_ENOUGH_EVIDENCE",
    "nei": "NOT_ENOUGH_EVIDENCE",
    "not_enough_evidence": "NOT_ENOUGH_EVIDENCE",
}


def _parse_verdict(value: str) -> str:
    verdict = VERDICT_SHORTCUTS.get(value.lower())
    if verdict is None:
        allowed = ", ".join(sorted(VERDICT_SHORTCUTS))
        raise ValueError(f"unknown verdict {value!r}; use one of: {allowed}")
    return verdict


def parse_verdict_decisions(text: str, claim_ids: Sequence[str]) -> dict[str, str]:
    normalized = re.sub(r"\s*=\s*", "=", text.strip())
    tokens = normalized.replace(",", " ").split()
    if not tokens:
        raise ValueError("no verdicts given")

    head = tokens[0].lower()
    if head.startswith("all=") or head == "all":
        if head.startswith("all="):
            if len(tokens) != 1:
                raise ValueError("use 'all=<verdict>'")
            value = tokens[0].split("=", 1)[1]
        else:
            if len(tokens) != 2:
                raise ValueError("use 'all=<verdict>'")
            value = tokens[1]
        return {claim_id: _parse_verdict(value) for claim_id in claim_ids}

    decisions: dict[str, str] = {}
    for token in tokens:
        if "=" not in token:
            raise ValueError(f"expected claim=verdict, got {token!r}")
        raw_claim_id, raw_verdict = token.split("=", 1)
        claim_id = raw_claim_id.lower()
        if claim_id.isdigit():
            claim_id = f"c{claim_id}"
        if claim_id not in claim_ids:
            raise ValueError(f"unknown claim {claim_id!r}")
        if claim_id in decisions:
            raise ValueError(f"duplicate verdict for {claim_id}")
        decisions[claim_id] = _parse_verdict(raw_verdict)

    missing = [claim_id for claim_id in claim_ids if claim_id not in decisions]
    if missing:
        raise ValueError(f"missing verdict for {', '.join(missing)}")
    return decisions


def parse_answer_sheet(
    text: str,
    claim_ids_by_query: Mapping[str, Sequence[str]],
) -> dict[str, dict[str, str]]:
    answers: dict[str, dict[str, str]] = {}
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split(maxsplit=1)
        query_id = parts[0].rstrip(":").lower()
        if query_id not in claim_ids_by_query:
            raise ValueError(f"line {line_number}: unknown query {query_id!r}")
        if query_id in answers:
            raise ValueError(f"line {line_number}: duplicate query {query_id}")
        if len(parts) == 1:
            raise ValueError(f"line {line_number}: missing verdicts for {query_id}")
        try:
            answers[query_id] = parse_verdict_decisions(
                parts[1], claim_ids_by_query[query_id]
            )
        except ValueError as exc:
            raise ValueError(f"line {line_number}: {exc}") from exc
    if not answers:
        raise ValueError("answer sheet is empty")
    return answers
