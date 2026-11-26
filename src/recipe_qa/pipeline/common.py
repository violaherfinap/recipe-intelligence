"""Shared pipeline execution for B0-B3."""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

from ..config import SystemConfig, load_system_config
from ..corpus.build import read_jsonl
from ..generation.generate import AnswerGenerator
from ..generation.prompt import format_evidence, load_examples, render_prompt
from ..generation.schema import AnswerPayload, Claim, EvidenceItem
from ..retrieval.search import Retriever
from ..verify.citations import check_citations
from ..verify.claims import verify_claims
from ..verify.sufficiency import should_abstain, sufficiency
from ..verify.temporal import check_temporal
from .abstain import AbstainPolicy, decide_abstain
from .planner import Planner
from .retry import RetryPolicy


def registry_path(config: SystemConfig) -> Path:
    return Path("prompts/registry") / f"{config.prompt.registry_id}.yaml"


def examples_path() -> Path:
    return Path("prompts/examples.jsonl")


def load_query_row(path: Path, query_id: str) -> dict:
    for row in read_jsonl(path):
        if row.get("query_id") == query_id:
            return row
    raise SystemExit(f"query_id {query_id!r} not found in {path}")


_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def _meaningful_sentence(sentence: str) -> bool:
    return len(sentence) >= 4 and bool(re.search(r"[A-Za-z]", sentence))


def _sentence_claims(
    answer_text: str,
    query_text: str,
    hits: list,
    as_of: int | None,
    limit: int = 4,
) -> list[Claim]:
    text = answer_text.strip() or query_text
    sentences = [
        part.strip()
        for part in _SENTENCE_RE.split(text)
        if part.strip() and _meaningful_sentence(part.strip())
    ]
    sentences = sentences[:limit] or [query_text]
    evidence = [
        EvidenceItem(
            passage_id=hit.passage_id,
            doc_id=hit.doc_id,
            source_year=hit.passage.get("source_year"),
            span=str(hit.passage.get("text", ""))[:500],
        )
        for hit in hits[:3]
    ]
    return [
        Claim(
            claim_id=f"c{index}",
            claim=sentence,
            verdict="SUPPORTED",
            as_of=as_of,
            evidence_for=evidence,
            evidence_against=[],
        )
        for index, sentence in enumerate(sentences, start=1)
    ]


def _rank_hits(hits: list) -> list:
    for index, hit in enumerate(hits, start=1):
        hit.rank = index
    return hits


def _merge_hits(groups: list[list], limit: int) -> list:
    limit = max(1, int(limit))
    merged = []
    seen: set[str] = set()
    max_length = max((len(group) for group in groups), default=0)
    for position in range(max_length):
        for group in groups:
            if position >= len(group):
                continue
            hit = group[position]
            if hit.passage_id in seen:
                continue
            seen.add(hit.passage_id)
            merged.append(hit)
            if len(merged) >= limit:
                return _rank_hits(merged)
    return _rank_hits(merged)


def _retrieve_with_planner(
    retriever: Retriever,
    config: SystemConfig,
    query_text: str,
    as_of: int | None,
    filter_spec,
    generator=None,
) -> tuple[list, dict | None]:
    if not config.planner.enabled:
        return retriever.retrieve(query_text, filter_spec=filter_spec), None
    llm = getattr(generator, "generate", None)
    plan = Planner(config.planner, llm=llm).plan(
        query_text,
        as_of=as_of,
        filter_spec=filter_spec,
    )
    groups = [
        retriever.retrieve(subquery.text, filter_spec=subquery.filter)
        for subquery in plan.subqueries
    ]
    return _merge_hits(groups, config.retrieval.final_k), plan.to_dict()


def _retrieve_with_retry(
    retriever: Retriever,
    config: SystemConfig,
    query_text: str,
    filter_spec,
    hits: list,
) -> tuple[list, dict | None]:
    if not config.retry.enabled:
        return hits, None
    threshold = config.retry.min_sufficiency
    initial_score = sufficiency(query_text, hits).score
    if hits and initial_score >= threshold:
        return hits, {
            "enabled": True,
            "threshold": threshold,
            "initial_score": initial_score,
            "attempts": [],
            "recovered": False,
        }
    attempts = []
    recovered = False
    for variant in RetryPolicy(config.retry).plan(query_text).queries[1:]:
        variant_hits = retriever.retrieve(variant, filter_spec=filter_spec)
        merged = _merge_hits(
            [hits, variant_hits],
            max(1, len(hits) + len(variant_hits)),
        )
        merged.sort(key=lambda hit: hit.score, reverse=True)
        hits = _rank_hits(merged[: max(1, config.retrieval.final_k)])
        score = sufficiency(query_text, hits).score
        attempts.append({"query": variant, "hits": len(variant_hits), "score": score})
        if hits and score >= threshold:
            recovered = True
            break
    return hits, {
        "enabled": True,
        "threshold": threshold,
        "initial_score": initial_score,
        "attempts": attempts,
        "recovered": recovered,
    }


def run_query(
    config: SystemConfig,
    query_row: dict,
    retriever: Retriever | None = None,
    generator: AnswerGenerator | None = None,
    verifier=None,
) -> dict:
    started = time.perf_counter()
    query_text = query_row["text"]
    query_id = query_row.get("query_id", "adhoc")
    as_of = query_row.get("as_of")
    filter_spec = query_row.get("filter")

    hits = []
    plan_meta: dict | None = None
    retry_meta: dict | None = None
    if config.retrieval.mode != "none":
        retriever = retriever or Retriever(config.retrieval)
        hits, plan_meta = _retrieve_with_planner(
            retriever,
            config,
            query_text,
            as_of,
            filter_spec,
            generator=generator,
        )
        hits, retry_meta = _retrieve_with_retry(
            retriever,
            config,
            query_text,
            filter_spec,
            hits,
        )

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
    repairs = 0
    sufficiency_meta: dict | None = None
    verification_meta: dict | None = None
    citations_meta: dict | None = None
    temporal_meta: dict | None = None
    abstain_meta: dict | None = None

    if config.abstain.enabled and config.abstain.sufficiency:
        result = sufficiency(query_text, hits)
        abstained = bool(hits) and should_abstain(
            result, config.abstain.sufficiency_threshold
        )
        sufficiency_meta = {
            "score": result.score,
            "top_score": result.top_score,
            "coverage": result.coverage,
            "top_passage_id": result.top_passage_id,
            "threshold": config.abstain.sufficiency_threshold,
            "abstained": abstained,
        }
        if abstained:
            answer = AnswerPayload(
                query_id=query_id,
                abstain=True,
                abstain_reason="not_specified",
                confidence=0.0,
                schema_valid=True,
            )

    if answer is None and config.retrieval.mode != "none" and not hits and config.abstain.enabled:
        answer = AnswerPayload(
            query_id=query_id,
            abstain=True,
            abstain_reason="no_recipe",
            confidence=0.0,
            schema_valid=True,
        )
    elif answer is None and generator is not None:
        max_repairs = (
            config.verification.max_repair_rounds if config.verification.enabled else 0
        )
        if max_repairs:
            answer, raw_output, repairs = generator.answer_with_repair(
                prompt,
                query_id,
                max_repairs,
            )
        else:
            answer, raw_output = generator.answer(prompt, query_id)

    if answer is not None and not answer.abstain and not answer.claims and hits:
        if config.verification.enabled:
            claims = _sentence_claims(answer.answer, query_text, hits, as_of)
        else:
            top = hits[0]
            claims = [
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
        answer = answer.model_copy(update={"claims": claims})

    if config.verification.enabled and answer is not None and not answer.abstain:
        if verifier is None:
            from ..verify.nli import NliVerifier

            verifier = NliVerifier(config.verification.nli_model)
        answer, report = verify_claims(
            answer,
            hits,
            verifier.score,
            threshold=config.verification.nli_threshold,
            model=config.verification.nli_model,
            keep_refuted=config.verification.keep_refuted,
            abstain_on_unsupported=config.verification.abstain_on_unsupported,
            premise_context=config.verification.premise_context,
        )
        verification_meta = report.to_dict()

    if (
        answer is not None
        and config.abstain.enabled
        and (config.abstain.citations or config.abstain.temporal)
    ):
        citation_report = check_citations(answer, hits)
        temporal_report = check_temporal(answer, hits, as_of=as_of)
        if config.abstain.citations:
            citations_meta = citation_report.to_dict()
        if config.abstain.temporal:
            temporal_meta = temporal_report.to_dict()
        policy = AbstainPolicy(
            on_citation_failure=config.abstain.citations,
            on_temporal_violation=config.abstain.temporal,
            require_evidence=config.abstain.require_evidence,
        )
        answer, decision = decide_abstain(
            answer,
            hits,
            citations=citation_report,
            temporal=temporal_report,
            verification=verification_meta,
            policy=policy,
        )
        abstain_meta = decision.to_dict()

    latency_ms = (time.perf_counter() - started) * 1000.0
    result = {
        "query_id": query_id,
        "config": config.id,
        "question": query_text,
        "retrieved": [hit.to_dict() for hit in hits],
        "prompt": prompt_meta,
        "answer": answer.model_dump() if answer else None,
        "raw_output": raw_output,
        "repairs": repairs,
        "sufficiency": sufficiency_meta,
        "verification": verification_meta,
        "schema_valid": answer.schema_valid if answer else None,
        "latency_ms": round(latency_ms, 2),
    }
    if plan_meta is not None:
        result["plan"] = plan_meta
    if retry_meta is not None:
        result["retry"] = retry_meta
    if citations_meta is not None:
        result["citations"] = citations_meta
    if temporal_meta is not None:
        result["temporal"] = temporal_meta
    if abstain_meta is not None:
        result["abstain"] = abstain_meta
    return result


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
