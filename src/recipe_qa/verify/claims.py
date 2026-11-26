"""Claim verification and grounding policy."""

from __future__ import annotations

from dataclasses import dataclass

from ..generation.schema import AnswerPayload, Claim, EvidenceItem
from .nli import NliScores, Scorer
from .premise import premise_text


@dataclass(frozen=True)
class VerificationReport:
    enabled: bool
    model: str
    threshold: float
    claims_before: int
    supported: int
    refuted: int
    dropped: int
    abstained: bool

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "model": self.model,
            "threshold": self.threshold,
            "claims_before": self.claims_before,
            "supported": self.supported,
            "refuted": self.refuted,
            "dropped": self.dropped,
            "abstained": self.abstained,
        }


def _evidence(hit, span_limit: int = 500) -> EvidenceItem:
    passage = hit.passage
    return EvidenceItem(
        passage_id=hit.passage_id,
        doc_id=hit.doc_id,
        source_year=passage.get("source_year"),
        span=str(passage.get("text", ""))[:span_limit],
    )


def _score_hit(
    scorer: Scorer,
    premise: str,
    hypothesis: str,
    cache: dict[str, NliScores],
    key: str,
) -> NliScores:
    if key not in cache:
        cache[key] = scorer(premise, hypothesis)
    return cache[key]


def _candidate_hits(claim: Claim, hits: list, top_n: int) -> list:
    cited = [item.passage_id for item in claim.evidence_for + claim.evidence_against]
    by_id = {hit.passage_id: hit for hit in hits}
    ordered = [by_id[passage_id] for passage_id in cited if passage_id in by_id]
    ordered.extend(hits[:top_n])
    seen: set[str] = set()
    unique = []
    for hit in ordered:
        if hit.passage_id in seen:
            continue
        seen.add(hit.passage_id)
        unique.append(hit)
    return unique


def verify_claims(
    payload: AnswerPayload,
    hits: list,
    scorer: Scorer,
    threshold: float = 0.5,
    model: str = "",
    keep_refuted: bool = False,
    abstain_on_unsupported: bool = True,
    drop_unsupported: bool = True,
    top_n: int = 3,
    premise_context: bool = False,
) -> tuple[AnswerPayload, VerificationReport]:
    if payload.abstain or not payload.claims:
        report = VerificationReport(
            enabled=True,
            model=model,
            threshold=threshold,
            claims_before=len(payload.claims),
            supported=0,
            refuted=0,
            dropped=0,
            abstained=payload.abstain,
        )
        return payload, report

    updated: list[Claim] = []
    supported = 0
    refuted = 0
    dropped = 0
    by_id = {hit.passage_id: hit for hit in hits}

    def premise_for(hit) -> str:
        if premise_context:
            return premise_text(hit.passage)
        return str(hit.passage.get("text", ""))

    for claim in payload.claims:
        cited_for = [
            hit
            for hit in (by_id[item.passage_id] for item in claim.evidence_for if item.passage_id in by_id)
            if str(hit.passage.get("text", "")).strip()
        ]
        cited_against = [
            hit
            for hit in (
                by_id[item.passage_id]
                for item in claim.evidence_against
                if item.passage_id in by_id
            )
            if str(hit.passage.get("text", "")).strip()
        ]

        best_entailment = 0.0
        best_contradiction = 0.0
        entail_hit = None
        contradict_hit = None
        score_cache: dict[str, NliScores] = {}

        for hit in _candidate_hits(claim, hits, top_n):
            premise = str(hit.passage.get("text", ""))
            if not premise.strip():
                continue
            scores = _score_hit(
                scorer, premise_for(hit), claim.claim, score_cache, hit.passage_id
            )
            if scores.entailment > best_entailment:
                best_entailment = scores.entailment
                entail_hit = hit
            if scores.contradiction > best_contradiction:
                best_contradiction = scores.contradiction
                contradict_hit = hit

        cited_support = 0.0
        cited_support_hit = None
        for hit in cited_for:
            scores = _score_hit(
                scorer, premise_for(hit), claim.claim, score_cache, hit.passage_id
            )
            if scores.entailment > cited_support:
                cited_support = scores.entailment
                cited_support_hit = hit

        cited_refute = 0.0
        cited_refute_hit = None
        for hit in cited_against:
            scores = _score_hit(
                scorer, premise_for(hit), claim.claim, score_cache, hit.passage_id
            )
            if scores.contradiction > cited_refute:
                cited_refute = scores.contradiction
                cited_refute_hit = hit

        if cited_support >= threshold:
            verdict = "SUPPORTED"
            evidence_for = [_evidence(cited_support_hit)] if cited_support_hit else []
            evidence_against = []
            supported += 1
        elif cited_refute >= threshold:
            verdict = "REFUTED"
            evidence_for = []
            evidence_against = [_evidence(cited_refute_hit)] if cited_refute_hit else []
            refuted += 1
        elif best_entailment >= threshold and best_entailment >= best_contradiction:
            verdict = "SUPPORTED"
            evidence_for = [_evidence(entail_hit)] if entail_hit is not None else []
            evidence_against = []
            supported += 1
        elif best_contradiction >= threshold and best_contradiction > best_entailment:
            verdict = "REFUTED"
            evidence_for = []
            evidence_against = (
                [_evidence(contradict_hit)] if contradict_hit is not None else []
            )
            refuted += 1
        else:
            verdict = "NOT_ENOUGH_EVIDENCE"
            evidence_for = []
            evidence_against = []

        checked = claim.model_copy(
            update={
                "verdict": verdict,
                "evidence_for": evidence_for,
                "evidence_against": evidence_against,
            }
        )
        if verdict == "SUPPORTED":
            updated.append(checked)
        elif verdict == "REFUTED" and keep_refuted:
            updated.append(checked)
        elif verdict == "NOT_ENOUGH_EVIDENCE" and not drop_unsupported:
            updated.append(checked)
        else:
            dropped += 1

    abstained = False
    answer = payload.answer
    abstain_reason = payload.abstain_reason
    if abstain_on_unsupported and dropped and not any(
        claim.verdict == "SUPPORTED" for claim in updated
    ):
        abstained = True
        answer = ""
        abstain_reason = "not_specified"
        updated = []
    elif dropped:
        answer = " ".join(claim.claim for claim in updated)

    result = payload.model_copy(
        update={
            "claims": updated,
            "answer": answer,
            "abstain": abstained or payload.abstain,
            "abstain_reason": abstain_reason,
        }
    )
    report = VerificationReport(
        enabled=True,
        model=model,
        threshold=threshold,
        claims_before=len(payload.claims),
        supported=supported,
        refuted=refuted,
        dropped=dropped,
        abstained=abstained,
    )
    return result, report
