"""Prompt registry rendering and evidence formatting."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from jinja2 import Template

from ..corpus.build import read_jsonl
from .schema import AnswerPayload


def load_registry(path: Path) -> dict:
    import yaml

    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_examples(path: Path, max_examples: int = 5) -> list[dict]:
    if not path.exists():
        return []
    return list(read_jsonl(path))[:max_examples]


def format_evidence(hits: list) -> str:
    if not hits:
        return "(no evidence retrieved)"
    lines: list[str] = []
    for hit in hits:
        passage = hit.passage if hasattr(hit, "passage") else hit
        lines.append(
            f"[{passage.get('passage_id')}] "
            f"year={passage.get('source_year')} "
            f"book={passage.get('source_title')} "
            f"section={passage.get('section')}\n"
            f"{passage.get('text', '').strip()}"
        )
    return "\n\n".join(lines)


def format_examples(examples: list[dict]) -> str:
    if not examples:
        return "(no examples)"
    blocks: list[str] = []
    for index, example in enumerate(examples, start=1):
        payload = {
            "query_id": example.get("query_id", f"ex_{index:03d}"),
            "answer": example.get("answer", ""),
            "claims": example.get("claims", []),
            "abstain": example.get("abstain", False),
            "abstain_reason": example.get("abstain_reason"),
            "confidence": example.get("confidence", 0.8),
            "schema_valid": True,
        }
        blocks.append(
            f"Example {index}:\n"
            f"Question: {example.get('query', '')}\n"
            f"Answer JSON: {json.dumps(payload, ensure_ascii=False)}"
        )
    return "\n\n".join(blocks)


def render_prompt(
    registry_path: Path,
    query: str,
    as_of: int | None,
    evidence_block: str,
    examples: list[dict] | None = None,
    few_shot: bool = False,
) -> tuple[str, dict]:
    registry = load_registry(registry_path)
    examples = examples or []
    few_shot_block = format_examples(examples) if few_shot else ""
    values = {
        "query": query,
        "as_of": as_of if as_of is not None else "not specified",
        "evidence_block": evidence_block,
        "few_shot_block": few_shot_block,
        "schema": AnswerPayload.model_json_schema(),
    }
    system = Template(str(registry.get("system", ""))).render(**values)
    user = Template(str(registry.get("user_template", ""))).render(**values)
    prompt = f"{system.strip()}\n\n{user.strip()}\n"
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    meta = {
        "id": registry.get("id"),
        "version": registry.get("version"),
        "hash": prompt_hash,
    }
    return prompt, meta
