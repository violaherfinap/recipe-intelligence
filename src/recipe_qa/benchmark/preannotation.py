from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ParsedAnswers:
    rows: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def parse_answers(text: str) -> ParsedAnswers:
    """Parse pipe-delimited preannotation answers.

    Expected line format: ``query_id|passage_id|0/1/2|optional reason``.
    """
    parsed = ParsedAnswers()
    seen: dict[tuple[str, str], int] = {}

    for line_number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("|", 3)
        if len(parts) < 3:
            parsed.errors.append(
                f"line {line_number}: expected query_id|passage_id|label[|reason]"
            )
            continue
        query_id, passage_id, label = (part.strip() for part in parts[:3])
        reason = parts[3].strip() if len(parts) == 4 else ""
        key = (query_id, passage_id)
        if key in seen:
            parsed.errors.append(
                f"line {line_number}: duplicate key {key} (first at line {seen[key]})"
            )
            continue
        seen[key] = line_number
        if label not in {"0", "1", "2"}:
            parsed.errors.append(
                f"line {line_number}: relevance must be 0, 1, or 2; got {label!r}"
            )
            continue
        parsed.rows.append(
            {
                "query_id": query_id,
                "passage_id": passage_id,
                "relevance": int(label),
                "notes": reason,
            }
        )

    return parsed


def validate_answers(rows: list[dict], expected_keys: set[tuple[str, str]]) -> list[str]:
    errors: list[str] = []
    seen = {(row["query_id"], row["passage_id"]) for row in rows}
    missing = sorted(expected_keys - seen)
    extra = sorted(seen - expected_keys)
    if missing:
        errors.append(f"missing answer keys: {missing[:10]} ({len(missing)} total)")
    if extra:
        errors.append(f"answer keys outside export: {extra[:10]} ({len(extra)} total)")
    return errors
