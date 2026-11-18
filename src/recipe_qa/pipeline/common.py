"""Shared pipeline execution for B0-B3."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from ..config import SystemConfig, load_system_config
from ..corpus.build import read_jsonl
from ..generation.generate import AnswerGenerator
from ..generation.prompt import format_evidence, load_examples, render_prompt
from ..generation.schema import AnswerPayload, Claim, EvidenceItem
from ..retrieval.search import Retriever


def registry_path(config: SystemConfig) -> Path:
    return Path("prompts/registry") / f"{config.prompt.registry_id}.yaml"


def examples_path() -> Path:
    return Path("prompts/examples.jsonl")


def load_query_row(path: Path, query_id: str) -> dict:
    for row in read_jsonl(path):
        if row.get("query_id") == query_id:
            return row
    raise SystemExit(f"query_id {query_id!r} not found in {path}")


def run_query(
    config: SystemConfig,
    query_row: dict,
    retriever: Retriever | None = None,
    generator: AnswerGenerator | None = None,
) -> dict:
    started = time.perf_counter()
    query_text = query_row["text"]
    query_id = query_row.get("query_id", "adhoc")
    as_of = query_row.get("as_of")
    filter_spec = query_row.get("filter")

    hits = []
    if config.retrieval.mode != "none":
        retriever = retriever or Retriever(config.retrieval)
        hits = retriever.retrieve(query_text, filter_spec=filter_spec)

    evidence = format_evidence(hits) if hits else "(no evidence retrieved)"
    examples = (
        load_examples(examples_path(), config.prompt.max_examples)
        if config.prompt.few_shot
        else []
    )
    prompt, prompt_meta = render_prompt(
        registry_path(config),
        query_text,
        as_of,
        evidence,
        examples=examples,
        few_shot=config.prompt.few_shot,
    )

    answer: AnswerPayload | None = None
    raw_output: str | None = None
    if config.retrieval.mode != "none" and not hits and config.abstain.enabled:
        answer = AnswerPayload(
            query_id=query_id,
            abstain=True,
            abstain_reason="no_recipe",
            confidence=0.0,
            schema_valid=True,
        )
    elif generator is not None:
        answer, raw_output = generator.answer(prompt, query_id)
        if answer is not None and not answer.abstain and not answer.claims and hits:
            top = hits[0]
            answer = answer.model_copy(
                update={
                    "claims": [
                        Claim(
                            claim_id="c1",
                            claim=answer.answer or query_text,
                            verdict="SUPPORTED",
                            as_of=as_of,
                            evidence_for=[
                                EvidenceItem(
                                    passage_id=top.passage_id,
                                    doc_id=top.doc_id,
                                    source_year=top.passage.get("source_year"),
                                    span=str(top.passage.get("text", ""))[:500],
                                )
                            ],
                            evidence_against=[],
                        )
                    ]
                }
            )

    latency_ms = (time.perf_counter() - started) * 1000.0
    return {
        "query_id": query_id,
        "config": config.id,
        "question": query_text,
        "retrieved": [hit.to_dict() for hit in hits],
        "prompt": prompt_meta,
        "answer": answer.model_dump() if answer else None,
        "raw_output": raw_output,
        "schema_valid": answer.schema_valid if answer else None,
        "latency_ms": round(latency_ms, 2),
    }


def pipeline_cli(default_config: str, argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path(default_config))
    parser.add_argument("--query", default=None, help="ad-hoc query text")
    parser.add_argument("--query-id", default=None, help="query id from --queries")
    parser.add_argument("--queries", type=Path, default=Path("benchmark/queries.jsonl"))
    parser.add_argument("--no-generate", action="store_true")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    config = load_system_config(args.config)
    if args.query_id:
        query_row = load_query_row(args.queries, args.query_id)
    elif args.query:
        query_row = {"query_id": "adhoc", "text": args.query}
    else:
        parser.error("provide --query or --query-id")

    retriever = Retriever(config.retrieval) if config.retrieval.mode != "none" else None
    generator = None if args.no_generate else AnswerGenerator(config.model)
    result = run_query(config, query_row, retriever=retriever, generator=generator)

    text = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    # Windows consoles may use cp1252; escape non-ASCII on stdout only.
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0
