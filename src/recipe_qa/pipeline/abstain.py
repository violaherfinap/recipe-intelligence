from __future__ import annotations

from dataclasses import dataclass

from ..generation.schema import AnswerPayload


@dataclass(frozen=True)
class AbstainPolicy:
    on_no_hits: bool = True
    on_citation_failure: bool = False
    on_temporal_violation: bool = False
    on_unsupported: bool = True
    require_evidence: bool = False


@dataclass(frozen=True)
class AbstainDecision:
    abstain: bool
    reason: str | None
    triggers: list[str]

    def to_dict(self) -> dict:
        return {
            "abstain": self.abstain,
            "reason": self.reason,
            "triggers": self.triggers,
        }


def _trigger_for(
    citations, temporal, verification, policy: AbstainPolicy
) -> tuple[str, str] | None:
    if policy.on_citation_failure and citations is not None:
        if citations.unknown_passages:
            return "citation_failure", "unknown_citation"
        if policy.require_evidence and citations.missing_evidence:
            return "citation_failure", "missing_evidence"
    if policy.on_temporal_violation and temporal is not None and not temporal.ok:
        return "temporal_violation", "temporal_violation"
    if policy.on_unsupported and verification is not None and verification.get("abstained"):
        return "not_specified", "unsupported_claims"
    return None


def decide_abstain(
    payload: AnswerPayload,
    hits: list,
    citations=None,
    temporal=None,
    verification: dict | None = None,
    policy: AbstainPolicy | None = None,
) -> tuple[AnswerPayload, AbstainDecision]:
    active = policy or AbstainPolicy()

    if payload.abstain:
        reason = payload.abstain_reason or ("no_recipe" if not hits else "not_specified")
        return payload, AbstainDecision(True, reason, ["upstream_abstain"])

    triggers: list[str] = []
    if payload.schema_valid is False:
        reason = "format_error"
        triggers.append("format_error")
    elif active.on_no_hits and not hits:
        reason = "no_recipe"
        triggers.append("no_hits")
    else:
        found = _trigger_for(citations, temporal, verification, active)
        if found is None:
            return payload, AbstainDecision(False, None, [])
        reason, trigger = found
        triggers.append(trigger)

    updated = payload.model_copy(
        update={
            "abstain": True,
            "abstain_reason": reason,
            "answer": "",
            "claims": [],
        }
    )
    return updated, AbstainDecision(True, reason, triggers)
