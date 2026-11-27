from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest

from recipe_qa.generation.schema import AnswerPayload
from recipe_qa.training.dataset import (
    KIND_ORDER,
    build_examples,
    load_inputs,
    split_template_holdout,
    write_dataset,
)

REGISTRY = Path("prompts/registry/structured_v1.yaml")


def _doc(doc_id: str, split: str, year: int) -> dict:
    return {
        "doc_id": doc_id,
        "title": f"Recipe {doc_id}",
        "source_title": f"Book {year}",
        "source_year": year,
        "split": split,
        "sections": {
            "ingredients": ["one egg", "one cup milk"],
            "directions": ["Beat the egg.", "Add the milk.", "Bake it."],
        },
    }


def _passage(doc_id: str, split: str, year: int, section: str) -> dict:
    return {
        "passage_id": f"{doc_id}#{section}#0",
        "doc_id": doc_id,
        "section": section,
        "idx": 0,
        "text": f"{section} text for {doc_id}",
        "source_title": f"Book {year}",
        "source_year": year,
        "split": split,
        "token_count": 10,
    }


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )


def _fixture(tmp_path: Path) -> tuple[dict[str, dict], list[dict]]:
    docs = {
        "d1": _doc("d1", "train", 1851),
        "d2": _doc("d2", "train", 1896),
        "d3": _doc("d3", "train", 1824),
        "d4": _doc("d4", "test", 1851),
        "d5": _doc("d5", "dev", 1851),
        "d6": _doc("d6", "train", 1871),
        "d7": _doc("d7", "train", 1887),
        "d8": _doc("d8", "train", 1796),
    }
    passages = []
    for doc in docs.values():
        for section in ("ingredients", "directions"):
            passages.append(
                _passage(doc["doc_id"], doc["split"], doc["source_year"], section)
            )
    return docs, passages


def test_build_examples_filters_split_and_year_deterministically() -> None:
    docs, passages = _fixture(Path("."))
    quotas = dict.fromkeys(KIND_ORDER, 1)
    first = build_examples(
        docs,
        passages,
        seed=42,
        size=5,
        quotas=quotas,
        registry=REGISTRY,
    )
    second = build_examples(
        docs,
        passages,
        seed=42,
        size=5,
        quotas=quotas,
        registry=REGISTRY,
    )
    assert [row["example_id"] for row in first] == [
        row["example_id"] for row in second
    ]
    assert [row["prompt"] for row in first] == [row["prompt"] for row in second]
    assert [row["target_json"] for row in first] == [
        row["target_json"] for row in second
    ]
    assert len(first) == 5
    for row in first:
        assert row["split"] == "train"
        assert row["source_year"] != 1824
        AnswerPayload.model_validate(row["target"])
        assert row["target"]["query_id"] == "q"
        assert row["template_id"].startswith(f"{row['kind']}_")
        assert row["evidence_passage_ids"]
        assert all("d3" not in passage_id for passage_id in row["evidence_passage_ids"])
        assert all("d4" not in passage_id for passage_id in row["evidence_passage_ids"])
        assert all("d5" not in passage_id for passage_id in row["evidence_passage_ids"])


def test_write_dataset_audit_has_no_violations(tmp_path: Path) -> None:
    docs, passages = _fixture(tmp_path)
    docs_path = tmp_path / "docs.jsonl"
    passages_path = tmp_path / "passages.jsonl"
    _write_jsonl(docs_path, list(docs.values()))
    _write_jsonl(passages_path, passages)
    loaded_docs, loaded_passages, allowed_ids, source_doc_ids = load_inputs(
        docs_path,
        passages_path,
    )
    examples = build_examples(
        loaded_docs,
        loaded_passages,
        seed=42,
        size=5,
        quotas=dict.fromkeys(KIND_ORDER, 1),
        registry=REGISTRY,
    )
    result = write_dataset(
        examples,
        out_path=tmp_path / "dataset.jsonl",
        audit_path=tmp_path / "audit.json",
        sha256_path=tmp_path / "dataset.sha256",
        allowed_ids=allowed_ids,
        source_doc_ids=source_doc_ids,
        exclude_year=1824,
    )
    assert result.total == 5
    assert result.audit["forbidden_years"] == []
    assert result.audit["bad_evidence_ids"] == []
    assert result.audit["bad_source_docs"] == []
    assert result.audit["invalid_targets"] == []
    assert result.audit["dataset_sha256"] == result.sha256
    assert (tmp_path / "dataset.sha256").read_text(encoding="utf-8").startswith(
        result.sha256
    )


def test_committed_dataset_is_leak_free() -> None:
    dataset_path = Path("train/dataset.jsonl")
    required = [
        dataset_path,
        Path("data/processed/docs.jsonl"),
        Path("data/processed/passages.jsonl"),
        Path("benchmark/queries.jsonl"),
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        pytest.skip(f"required artifacts missing: {missing}")

    docs = {
        str(row["doc_id"]): row
        for row in (
            json.loads(line)
            for line in Path("data/processed/docs.jsonl").read_text(
                encoding="utf-8"
            ).splitlines()
            if line.strip()
        )
    }
    passages = {
        str(row["passage_id"]): row
        for row in (
            json.loads(line)
            for line in Path("data/processed/passages.jsonl").read_text(
                encoding="utf-8"
            ).splitlines()
            if line.strip()
        )
    }
    test_docs = {
        doc_id for doc_id, doc in docs.items() if doc.get("split") == "test"
    }
    queries = [
        json.loads(line)
        for line in Path("benchmark/queries.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]
    query_texts = {row["text"] for row in queries}
    examples = [
        json.loads(line)
        for line in dataset_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    expected_hash = Path("train/dataset.sha256").read_text(encoding="utf-8").split()[0]
    assert hashlib.sha256(dataset_path.read_bytes()).hexdigest() == expected_hash
    assert 600 <= len(examples) <= 800
    assert Counter(row["kind"] for row in examples) == Counter(
        {
            "ingredients": 270,
            "directions": 270,
            "metadata": 100,
            "no_recipe": 30,
            "out_of_period": 30,
        }
    )
    for row in examples:
        assert row["split"] == "train"
        assert row["target"]["query_id"] == "q"
        assert row["template_id"].startswith(f"{row['kind']}_")
        assert int(row["source_year"]) != 1824
        assert row["source_doc_id"] in docs
        assert docs[row["source_doc_id"]].get("split") == "train"
        assert row["source_doc_id"] not in test_docs
        assert row["query"] not in query_texts
        for passage_id in row["evidence_passage_ids"]:
            passage = passages[passage_id]
            assert passage["split"] == "train"
            assert int(passage["source_year"]) != 1824
            assert passage["doc_id"] not in test_docs
            assert passage["doc_id"] == row["source_doc_id"] or row["kind"] == "no_recipe"


def test_split_template_holdout_is_disjoint_and_deterministic() -> None:
    examples = []
    for kind in ("ingredients", "directions"):
        for template in ("a", "b"):
            for index in range(2):
                examples.append(
                    {
                        "example_id": f"{kind}_{template}_{index}",
                        "kind": kind,
                        "template_id": f"{kind}_{template}",
                        "source_doc_id": f"{kind}_{template}_{index}",
                    }
                )

    train, val, val_templates = split_template_holdout(examples, seed=42)
    again_train, again_val, again_templates = split_template_holdout(
        examples,
        seed=42,
    )

    assert val_templates == again_templates
    assert [row["example_id"] for row in train] == [
        row["example_id"] for row in again_train
    ]
    assert [row["example_id"] for row in val] == [
        row["example_id"] for row in again_val
    ]
    assert len(val_templates) == 2
    assert {row["template_id"] for row in train}.isdisjoint(
        {row["template_id"] for row in val}
    )
    assert {row["source_doc_id"] for row in train}.isdisjoint(
        {row["source_doc_id"] for row in val}
    )
    assert {row["kind"] for row in val} == {"ingredients", "directions"}


def test_split_template_holdout_requires_two_templates_per_kind() -> None:
    examples = [
        {
            "example_id": "ingredients_only_0",
            "kind": "ingredients",
            "template_id": "ingredients_only",
            "source_doc_id": "d1",
        }
    ]

    with pytest.raises(ValueError, match="at least two templates"):
        split_template_holdout(examples, seed=42)
