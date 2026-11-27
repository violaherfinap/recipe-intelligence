"""Build a leak-free LoRA training set from train-split recipe passages."""

from __future__ import annotations

import hashlib
import json
import random
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from ..corpus.build import read_jsonl
from ..generation.prompt import format_evidence, render_prompt
from ..generation.schema import AnswerPayload

KIND_ORDER = ("ingredients", "directions", "metadata", "no_recipe", "out_of_period")
DEFAULT_QUOTAS = {
    "ingredients": 270,
    "directions": 270,
    "metadata": 100,
    "no_recipe": 30,
    "out_of_period": 30,
}
DEFAULT_REGISTRY = Path("prompts/registry/structured_v1.yaml")

QUESTION_TEMPLATES = {
    "ingredients": (
        ("ingredients_what", "What ingredients are used in {title}?"),
        ("ingredients_which", "Which ingredients does {title} require?"),
        ("ingredients_list", "List the ingredients for {title}."),
        ("ingredients_goes_into", "What goes into {title}?"),
    ),
    "directions": (
        ("directions_prepared", "How is {title} prepared?"),
        ("directions_steps", "What are the steps to make {title}?"),
        ("directions_method", "Describe the method for {title}."),
        ("directions_cook", "How do you cook {title}?"),
    ),
    "metadata": (
        ("metadata_year_book", "In which year and book was {title} published?"),
        ("metadata_when_book", "When was {title} published, and in which book?"),
        (
            "metadata_source",
            "What is the publication year and source book for {title}?",
        ),
        ("metadata_cookbook", "In what year and cookbook did {title} appear?"),
    ),
    "no_recipe": (
        ("no_recipe_what", "What ingredients are used in {dish}?"),
        ("no_recipe_which", "Which ingredients does {dish} require?"),
        ("no_recipe_list", "List the ingredients for {dish}."),
        ("no_recipe_goes_into", "What goes into {dish}?"),
    ),
    "out_of_period": (
        ("out_of_period_prepared", "How was {title} prepared in 1900?"),
        ("out_of_period_steps", "What were the steps to make {title} in 1900?"),
        ("out_of_period_method", "Describe the method for {title} in 1900."),
        ("out_of_period_cook", "How do you cook {title} in 1900?"),
    ),
}

FICTIONAL_DISHES = (
    "moonlight pudding",
    "solar jelly",
    "star anise cake",
    "cloud souffle",
    "amber custard",
    "harvest marble cake",
    "orchard snow",
    "copper kettle stew",
    "lantern biscuits",
    "midnight preserve",
    "garden comet tart",
    "velvet barley soup",
    "sunrise fritters",
    "silver pear pie",
    "meadow dumplings",
    "cinnamon comet cakes",
    "harbor pudding",
    "orchard lantern pie",
    "spiced comet custard",
    "riverbank biscuits",
    "golden meadow cake",
    "winter lantern jelly",
    "summer comet tart",
    "quiet orchard pudding",
    "copper moon cakes",
    "honeyed harbor bread",
    "peach lantern preserve",
    "herb garden fritters",
    "saffron cloud cake",
    "market day pudding",
    "lattice pear tart",
    "smoked orchard soup",
    "rosewater comet cakes",
    "country fair custard",
    "cider house bread",
    "candlelight biscuits",
    "farmhouse marigold cake",
    "autumn harbor pie",
    "spring meadow jelly",
    "maple lantern pudding",
    "walnut comet tart",
    "orchard sunrise cake",
    "harvest moon fritters",
    "cinnamon harbor bread",
    "plum lantern preserve",
    "snowy orchard custard",
    "copper meadow cake",
    "riverside pear pudding",
    "golden harbor biscuits",
    "twilight garden tart",
)


@dataclass(frozen=True)
class DatasetBuildResult:
    path: Path
    audit_path: Path
    sha256_path: Path
    total: int
    sha256: str
    audit: dict


def _clean_item(value: str) -> str:
    item = re.sub(r"^\s*[-*]\s*", "", str(value).strip())
    item = re.sub(r"^\s*\d+[.)]\s*", "", item)
    return item.strip().rstrip(".").strip()


def _items(values, limit: int) -> list[str]:
    cleaned = [_clean_item(value) for value in values or []]
    return [value for value in cleaned if value][:limit]


def _answer_ingredients(title: str, items: list[str]) -> str:
    if not items:
        raise ValueError("ingredients are empty")
    joined = ", ".join(items)
    return f"{title} uses {joined}."


def _answer_directions(title: str, items: list[str]) -> str:
    if not items:
        raise ValueError("directions are empty")
    parts = []
    for index, item in enumerate(items, start=1):
        prefix = "First" if index == 1 else "Then" if index == 2 else "Finally"
        parts.append(f"{prefix}: {item}.")
    return " ".join(parts)


def _pick_template(kind: str, counter: int) -> tuple[str, str]:
    templates = QUESTION_TEMPLATES[kind]
    return templates[(counter - 1) % len(templates)]


def _target(
    *,
    answer: str,
    abstain: bool,
    abstain_reason: str | None,
    confidence: float,
) -> dict:
    payload = {
        "query_id": "q",
        "answer": answer,
        "abstain": abstain,
        "abstain_reason": abstain_reason,
        "confidence": confidence,
        "schema_valid": True,
    }
    AnswerPayload.model_validate(payload)
    return payload


def _group_passages(
    passages: list[dict],
    *,
    split: str,
    exclude_year: int,
) -> tuple[dict[str, dict[str, dict]], set[str]]:
    by_doc: dict[str, dict[str, dict]] = defaultdict(dict)
    allowed_ids: set[str] = set()
    for passage in passages:
        if passage.get("split") != split:
            continue
        if int(passage.get("source_year") or 0) == exclude_year:
            continue
        allowed_ids.add(str(passage["passage_id"]))
        section = passage.get("section")
        if section in {"ingredients", "directions"}:
            by_doc[str(passage["doc_id"])].setdefault(str(section), passage)
    return dict(by_doc), allowed_ids


def _candidate_docs(
    docs: dict[str, dict],
    by_doc: dict[str, dict[str, dict]],
    *,
    split: str,
    exclude_year: int,
) -> list[str]:
    candidates = []
    for doc_id in sorted(by_doc):
        sections = by_doc[doc_id]
        if "ingredients" not in sections or "directions" not in sections:
            continue
        doc = docs.get(doc_id)
        if doc is None:
            continue
        if doc.get("split") != split:
            continue
        if int(doc.get("source_year") or 0) == exclude_year:
            continue
        candidates.append(doc_id)
    return candidates


def _make_example(
    *,
    example_id: str,
    kind: str,
    doc: dict,
    evidence_passage: dict,
    question: str,
    template_id: str,
    as_of: int | None,
    target: dict,
    registry: Path,
    split: str,
) -> dict:
    evidence = format_evidence([evidence_passage])
    prompt, prompt_meta = render_prompt(
        registry,
        question,
        as_of,
        evidence,
        few_shot=False,
    )
    return {
        "example_id": example_id,
        "kind": kind,
        "split": split,
        "source_doc_id": str(doc["doc_id"]),
        "source_title": str(doc.get("source_title") or ""),
        "source_year": int(doc.get("source_year") or 0),
        "query": question,
        "template_id": template_id,
        "as_of": as_of,
        "evidence_passage_ids": [str(evidence_passage["passage_id"])],
        "evidence_sections": [str(evidence_passage.get("section") or "")],
        "prompt_id": prompt_meta.get("id"),
        "prompt_version": prompt_meta.get("version"),
        "prompt": prompt,
        "target": target,
        "target_json": json.dumps(target, ensure_ascii=False, separators=(",", ":")),
    }


def build_examples(
    docs: dict[str, dict],
    passages: list[dict],
    *,
    seed: int = 42,
    size: int = 700,
    quotas: dict[str, int] | None = None,
    exclude_year: int = 1824,
    split: str = "train",
    registry: Path = DEFAULT_REGISTRY,
) -> list[dict]:
    quotas = dict(quotas or DEFAULT_QUOTAS)
    if set(quotas) != set(KIND_ORDER):
        raise ValueError(f"quotas must define exactly {KIND_ORDER}")
    if sum(quotas.values()) != size:
        raise ValueError("quota total must equal size")

    by_doc, allowed_ids = _group_passages(
        passages,
        split=split,
        exclude_year=exclude_year,
    )
    candidates = _candidate_docs(
        docs,
        by_doc,
        split=split,
        exclude_year=exclude_year,
    )
    if len(candidates) < size:
        raise ValueError(f"need {size} candidate docs, found {len(candidates)}")

    rng = random.Random(seed)
    rng.shuffle(candidates)
    distractor_ids = sorted(allowed_ids)
    passages_by_id = {str(passage["passage_id"]): passage for passage in passages}

    remaining = dict(quotas)
    examples: list[dict] = []
    counters: Counter[str] = Counter()
    for doc_id in candidates:
        kind = next((name for name in KIND_ORDER if remaining[name] > 0), None)
        if kind is None:
            break
        doc = docs[doc_id]
        sections = by_doc[doc_id]
        title = str(doc.get("title") or doc_id)
        source_year = int(doc.get("source_year") or 0)
        next_counter = counters[kind] + 1
        example_id = f"{kind}_{next_counter:04d}"
        template_id, template = _pick_template(kind, next_counter)

        if kind == "ingredients":
            evidence = sections["ingredients"]
            items = _items((doc.get("sections") or {}).get("ingredients"), limit=8)
            try:
                answer = _answer_ingredients(title, items)
            except ValueError:
                continue
            target = _target(
                answer=answer,
                abstain=False,
                abstain_reason=None,
                confidence=0.85,
            )
            question = template.format(title=title)
            as_of = source_year
        elif kind == "directions":
            evidence = sections["directions"]
            items = _items((doc.get("sections") or {}).get("directions"), limit=3)
            try:
                answer = _answer_directions(title, items)
            except ValueError:
                continue
            target = _target(
                answer=answer,
                abstain=False,
                abstain_reason=None,
                confidence=0.8,
            )
            question = template.format(title=title)
            as_of = source_year
        elif kind == "metadata":
            evidence = sections["directions"]
            answer = f"{title} was published in {source_year} in {doc.get('source_title')}."
            target = _target(
                answer=answer,
                abstain=False,
                abstain_reason=None,
                confidence=0.9,
            )
            question = template.format(title=title)
            as_of = source_year
        elif kind == "no_recipe":
            dish = FICTIONAL_DISHES[(next_counter - 1) % len(FICTIONAL_DISHES)]
            own_ids = {str(passage["passage_id"]) for passage in sections.values()}
            distractor_id = rng.choice(distractor_ids)
            while distractor_id in own_ids:
                distractor_id = rng.choice(distractor_ids)
            evidence = passages_by_id[distractor_id]
            target = _target(
                answer="",
                abstain=True,
                abstain_reason="no_recipe",
                confidence=0.0,
            )
            question = template.format(dish=dish)
            as_of = None
        else:
            evidence = sections["directions"]
            target = _target(
                answer="",
                abstain=True,
                abstain_reason="out_of_period",
                confidence=0.0,
            )
            question = template.format(title=title)
            as_of = 1900

        counters[kind] = next_counter
        remaining[kind] -= 1
        examples.append(
            _make_example(
                example_id=example_id,
                kind=kind,
                doc=doc,
                evidence_passage=evidence,
                question=question,
                template_id=template_id,
                as_of=as_of,
                target=target,
                registry=registry,
                split=split,
            )
        )

    missing = {kind: count for kind, count in remaining.items() if count > 0}
    if missing:
        raise ValueError(f"could not fill quotas: {missing}")

    examples.sort(key=lambda row: row["example_id"])
    return examples


def split_template_holdout(
    examples: list[dict],
    *,
    seed: int = 42,
) -> tuple[list[dict], list[dict], list[str]]:
    templates_by_kind: dict[str, set[str]] = defaultdict(set)
    for example in examples:
        templates_by_kind[str(example["kind"])].add(str(example["template_id"]))
    for kind, templates in templates_by_kind.items():
        if len(templates) < 2:
            raise ValueError(f"kind {kind} needs at least two templates")

    rng = random.Random(seed)
    val_templates = {
        rng.choice(sorted(templates))
        for _, templates in sorted(templates_by_kind.items())
    }
    train = [row for row in examples if row["template_id"] not in val_templates]
    val = [row for row in examples if row["template_id"] in val_templates]
    if not train or not val:
        raise ValueError("template holdout produced an empty split")
    train_docs = {str(row["source_doc_id"]) for row in train}
    val_docs = {str(row["source_doc_id"]) for row in val}
    if train_docs & val_docs:
        raise ValueError("template holdout leaked source documents across splits")
    return train, val, sorted(val_templates)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit_examples(
    examples: list[dict],
    *,
    allowed_ids: set[str],
    source_doc_ids: set[str],
    exclude_year: int,
    dataset_sha256: str | None = None,
) -> dict:
    kind_counts = Counter(row["kind"] for row in examples)
    template_counts = Counter(row["template_id"] for row in examples)
    year_counts = Counter(int(row["source_year"]) for row in examples)
    section_counts = Counter(
        section for row in examples for section in row["evidence_sections"]
    )
    bad_evidence = sorted(
        {
            passage_id
            for row in examples
            for passage_id in row["evidence_passage_ids"]
            if passage_id not in allowed_ids
        }
    )
    bad_docs = sorted(
        {row["source_doc_id"] for row in examples if row["source_doc_id"] not in source_doc_ids}
    )
    forbidden_years = sorted(
        {
            int(row["source_year"])
            for row in examples
            if int(row["source_year"]) == exclude_year
        }
    )
    invalid_targets = []
    for row in examples:
        try:
            AnswerPayload.model_validate(row["target"])
        except Exception as exc:
            invalid_targets.append({"example_id": row["example_id"], "error": str(exc)})
    return {
        "total": len(examples),
        "kinds": dict(sorted(kind_counts.items())),
        "templates": dict(sorted(template_counts.items())),
        "years": {str(year): count for year, count in sorted(year_counts.items())},
        "evidence_sections": dict(sorted(section_counts.items())),
        "unique_source_docs": len({row["source_doc_id"] for row in examples}),
        "excluded_year": exclude_year,
        "forbidden_years": forbidden_years,
        "bad_evidence_ids": bad_evidence,
        "bad_source_docs": bad_docs,
        "invalid_targets": invalid_targets,
        "dataset_sha256": dataset_sha256,
    }


def write_dataset(
    examples: list[dict],
    *,
    out_path: Path,
    audit_path: Path,
    sha256_path: Path,
    allowed_ids: set[str],
    source_doc_ids: set[str],
    exclude_year: int,
) -> DatasetBuildResult:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in examples:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    digest = _sha256(out_path)
    sha256_path.parent.mkdir(parents=True, exist_ok=True)
    sha256_path.write_text(f"{digest}  {out_path.name}\n", encoding="utf-8")
    audit = audit_examples(
        examples,
        allowed_ids=allowed_ids,
        source_doc_ids=source_doc_ids,
        exclude_year=exclude_year,
        dataset_sha256=digest,
    )
    audit_path.write_text(
        json.dumps(audit, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return DatasetBuildResult(
        path=out_path,
        audit_path=audit_path,
        sha256_path=sha256_path,
        total=len(examples),
        sha256=digest,
        audit=audit,
    )


def load_inputs(
    docs_path: Path,
    passages_path: Path,
    *,
    split: str = "train",
    exclude_year: int = 1824,
) -> tuple[dict[str, dict], list[dict], set[str], set[str]]:
    docs = {str(row["doc_id"]): row for row in read_jsonl(docs_path)}
    passages = list(read_jsonl(passages_path))
    by_doc, allowed_ids = _group_passages(
        passages,
        split=split,
        exclude_year=exclude_year,
    )
    candidates = _candidate_docs(
        docs,
        by_doc,
        split=split,
        exclude_year=exclude_year,
    )
    return docs, passages, allowed_ids, set(candidates)
