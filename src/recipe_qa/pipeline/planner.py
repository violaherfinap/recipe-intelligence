"""Query planning for B4 with an LLM planner and a rule-based fallback."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import yaml
from jinja2 import Template
from pydantic import BaseModel, ConfigDict, Field

from ..config import PlannerConfig
from ..generation.generate import extract_json_object

_YEAR_RE = re.compile(r"\b(1[0-9]{3})\b")
_BOTH_RE = re.compile(r"\bboth\s+(.+?)\s+and\s+(.+?)(?=[?.!,;]|$)", re.IGNORECASE)
_PLANNER_REGISTRY = Path("prompts/registry/planner_v1.yaml")


@dataclass(frozen=True)
class Subquery:
    text: str
    filter: dict | None = None

    def to_dict(self) -> dict:
        return {"text": self.text, "filter": self.filter}


@dataclass(frozen=True)
class Plan:
    subqueries: tuple[Subquery, ...]
    rationale: str = ""

    def to_dict(self) -> dict:
        return {
            "rationale": self.rationale,
            "subqueries": [subquery.to_dict() for subquery in self.subqueries],
        }


class _PlannerSubquery(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text: str
    filter: dict | None = None


class _PlannerPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    subqueries: list[_PlannerSubquery] = Field(default_factory=list)
    rationale: str = ""


def _clean_filter(spec) -> dict | None:
    if spec is None:
        return None
    if hasattr(spec, "model_dump"):
        spec = spec.model_dump()
    if not isinstance(spec, dict):
        return None
    cleaned = {key: value for key, value in spec.items() if value is not None}
    return cleaned or None


def _valid_subquery_text(text: str) -> bool:
    stripped = text.strip()
    if not stripped or "\n" in stripped:
        return False
    words = stripped.split()
    if len(words) > 16:
        return False
    if stripped.endswith(".") and len(words) > 6:
        return False
    lowered = stripped.lower()
    if any(marker in lowered for marker in ("select ", " from ", " where ", "```")):
        return False
    if any(
        phrase in lowered
        for phrase in ("we need", "would need", "might have", "typically contain")
    ):
        return False
    return True


def render_planner_prompt(
    query: str,
    as_of: int | None,
    base_filter: dict | None,
    max_subqueries: int,
) -> str:
    registry = yaml.safe_load(_PLANNER_REGISTRY.read_text(encoding="utf-8"))
    values = {
        "query": query,
        "as_of": as_of if as_of is not None else "not specified",
        "filter_json": json.dumps(base_filter or {}, ensure_ascii=False),
        "max_subqueries": max_subqueries,
    }
    system = Template(str(registry.get("system", ""))).render(**values)
    user = Template(str(registry.get("user_template", ""))).render(**values)
    return f"{system.strip()}\n\n{user.strip()}\n"


class Planner:
    def __init__(self, config: PlannerConfig, llm=None) -> None:
        self.config = config
        self.llm = llm

    def plan(self, query: str, as_of: int | None = None, filter_spec=None) -> Plan:
        base_filter = _clean_filter(filter_spec)
        if not self.config.enabled:
            return Plan((Subquery(query, base_filter),), "disabled")
        if self.config.mode == "llm" and self.llm is not None:
            try:
                return self._plan_llm(query, as_of, base_filter)
            except Exception:
                pass
        return self._plan_rule(query, base_filter)

    def _plan_llm(self, query: str, as_of: int | None, base_filter: dict | None) -> Plan:
        prompt = render_planner_prompt(
            query,
            as_of,
            base_filter,
            self.config.max_subqueries,
        )
        raw = self.llm(prompt)
        raw_json = extract_json_object(raw)
        if raw_json is None:
            raise ValueError("planner returned no JSON object")
        payload = _PlannerPayload.model_validate(json.loads(raw_json))
        subqueries = []
        for item in payload.subqueries[: self.config.max_subqueries]:
            text = item.text.strip()
            if not _valid_subquery_text(text):
                raise ValueError("planner returned an unusable subquery")
            filter_value = dict(base_filter or {})
            filter_value.update(_clean_filter(item.filter) or {})
            subqueries.append(Subquery(text, filter_value or None))
        if not subqueries:
            raise ValueError("planner returned no usable subqueries")
        return Plan(tuple(subqueries), payload.rationale or "llm")

    def _plan_rule(self, query: str, base_filter: dict | None) -> Plan:
        years = sorted({int(value) for value in _YEAR_RE.findall(query)})
        if len(years) >= 2 and self.config.max_subqueries >= 2:
            subqueries = []
            for year in years[: self.config.max_subqueries]:
                filter_value = dict(base_filter or {})
                filter_value["year_min"] = year
                filter_value["year_max"] = year
                subqueries.append(Subquery(query, filter_value))
            return Plan(tuple(subqueries), "temporal-year-decomposition")

        match = _BOTH_RE.search(query)
        if match and self.config.max_subqueries >= 2:
            entities = [match.group(1).strip(), match.group(2).strip()]
            if len({entity.lower() for entity in entities}) > 1:
                prefix = query[: match.start()].strip()
                tail = query[match.end() :].strip()
                suffix = tail[0] if tail and tail[0] in "?.!,;" else "?"
                subqueries = [
                    Subquery(f"{prefix} {entity}{suffix}", base_filter)
                    for entity in entities
                ]
                return Plan(tuple(subqueries), "multi-entity-decomposition")

        return Plan((Subquery(query, base_filter),), "single")
