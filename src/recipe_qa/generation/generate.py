"""Local Qwen generator and JSON answer parsing."""

from __future__ import annotations

import json
from pathlib import Path

from ..config import ModelConfig
from .schema import AnswerPayload, Claim, EvidenceItem

_ALLOWED_REASONS = {
    "no_recipe",
    "not_specified",
    "out_of_period",
    "conflicting_sources",
    "format_error",
}
_ALLOWED_VERDICTS = {"SUPPORTED", "REFUTED", "NOT_ENOUGH_EVIDENCE"}


def extract_json_object(text: str) -> str | None:
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        else:
            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start : index + 1]
    return None


def _normalise_evidence(items) -> list[EvidenceItem]:
    if not isinstance(items, list):
        return []
    evidence: list[EvidenceItem] = []
    for item in items:
        if not isinstance(item, dict) or not item.get("passage_id"):
            continue
        evidence.append(
            EvidenceItem(
                passage_id=str(item.get("passage_id")),
                doc_id=str(item.get("doc_id", "")),
                source_year=item.get("source_year"),
                span=str(item.get("span", "")),
            )
        )
    return evidence


def _normalise_payload(data: dict, query_id: str) -> AnswerPayload:
    """Coerce a small model's near-JSON output into the output contract."""
    answer = str(data.get("answer") or "")
    claims_raw = data.get("claims") or []
    claims: list[Claim] = []
    if isinstance(claims_raw, list):
        for index, item in enumerate(claims_raw, start=1):
            if isinstance(item, str):
                claims.append(
                    Claim(
                        claim_id=f"c{index}",
                        claim=item,
                        verdict="NOT_ENOUGH_EVIDENCE",
                        as_of=data.get("as_of"),
                    )
                )
                continue
            if not isinstance(item, dict):
                continue
            verdict = item.get("verdict")
            if verdict not in _ALLOWED_VERDICTS:
                verdict = "NOT_ENOUGH_EVIDENCE"
            claims.append(
                Claim(
                    claim_id=str(item.get("claim_id") or f"c{index}"),
                    claim=str(item.get("claim") or item.get("text") or answer),
                    verdict=verdict,
                    as_of=item.get("as_of") or data.get("as_of"),
                    evidence_for=_normalise_evidence(item.get("evidence_for")),
                    evidence_against=_normalise_evidence(item.get("evidence_against")),
                )
            )

    abstain_raw = data.get("abstain", False)
    if isinstance(abstain_raw, dict):
        abstain = not bool(answer)
    else:
        abstain = bool(abstain_raw)

    reason_raw = data.get("abstain_reason")
    if isinstance(reason_raw, dict):
        reason_raw = reason_raw.get("reason")
    reason = reason_raw if reason_raw in _ALLOWED_REASONS else None
    if abstain and reason is None:
        reason = "not_specified"
    if not abstain:
        reason = None

    try:
        confidence = float(data.get("confidence", 0.5))
    except (TypeError, ValueError):
        confidence = 0.5
    confidence = max(0.0, min(1.0, confidence))

    return AnswerPayload(
        query_id=query_id,
        answer=answer,
        claims=claims,
        abstain=abstain,
        abstain_reason=reason,
        confidence=confidence,
        schema_valid=True,
    )


def parse_answer(text: str, query_id: str) -> AnswerPayload:
    raw = extract_json_object(text)
    if raw is None:
        return AnswerPayload(
            query_id=query_id,
            abstain=True,
            abstain_reason="format_error",
            confidence=0.0,
            schema_valid=False,
        )
    try:
        data = json.loads(raw)
    except Exception:
        return AnswerPayload(
            query_id=query_id,
            abstain=True,
            abstain_reason="format_error",
            confidence=0.0,
            schema_valid=False,
        )
    if not isinstance(data, dict):
        return AnswerPayload(
            query_id=query_id,
            abstain=True,
            abstain_reason="format_error",
            confidence=0.0,
            schema_valid=False,
        )
    try:
        payload = AnswerPayload.model_validate(data)
    except Exception:
        return _normalise_payload(data, query_id)
    if payload.query_id != query_id:
        payload = payload.model_copy(update={"query_id": query_id})
    return payload


def build_repair_prompt(prompt: str, invalid_output: str, max_chars: int = 2000) -> str:
    snippet = invalid_output.strip()[:max_chars]
    return (
        f"{prompt.rstrip()}\n\n"
        "The previous response could not be parsed as the required JSON object. "
        "Return ONLY one valid JSON object matching the schema. "
        "Do not use markdown fences or add explanations.\n"
        f"Previous response:\n{snippet}\n"
    )


def generate_with_repair(
    generate_fn,
    prompt: str,
    query_id: str,
    max_repairs: int = 0,
) -> tuple[AnswerPayload, str, int]:
    raw = generate_fn(prompt)
    payload = parse_answer(raw, query_id)
    repairs = 0
    while not payload.schema_valid and repairs < max_repairs:
        raw = generate_fn(build_repair_prompt(prompt, raw))
        payload = parse_answer(raw, query_id)
        repairs += 1
    return payload, raw, repairs


class AnswerGenerator:
    def __init__(self, config: ModelConfig) -> None:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        torch.set_num_threads(8)
        self.config = config
        self.tokenizer = AutoTokenizer.from_pretrained(config.name)
        dtype = {
            "float32": torch.float32,
            "float16": torch.float16,
            "bfloat16": torch.bfloat16,
        }.get(config.dtype, torch.float32)
        self.model = AutoModelForCausalLM.from_pretrained(config.name, torch_dtype=dtype)
        if config.adapter:
            from peft import PeftModel

            adapter_path = Path(config.adapter)
            if not adapter_path.exists():
                raise FileNotFoundError(f"adapter not found: {adapter_path}")
            self.model = PeftModel.from_pretrained(self.model, str(adapter_path))
        self.model.eval()

    def generate(self, prompt: str) -> str:
        import torch

        torch.manual_seed(self.config.seed)
        chat = self.tokenizer.apply_chat_template(
            [{"role": "user", "content": prompt}],
            tokenize=False,
            add_generation_prompt=True,
        )
        inputs = self.tokenizer(chat, return_tensors="pt")
        outputs = self.model.generate(
            **inputs,
            max_new_tokens=self.config.max_new_tokens,
            do_sample=True,
            temperature=self.config.temperature,
            top_p=self.config.top_p,
            repetition_penalty=self.config.repetition_penalty,
            pad_token_id=self.tokenizer.eos_token_id,
        )
        new_tokens = outputs[0][inputs["input_ids"].shape[1] :]
        return self.tokenizer.decode(new_tokens, skip_special_tokens=True)

    def answer(self, prompt: str, query_id: str) -> tuple[AnswerPayload, str]:
        raw = self.generate(prompt)
        return parse_answer(raw, query_id), raw

    def answer_with_repair(
        self,
        prompt: str,
        query_id: str,
        max_repairs: int = 0,
    ) -> tuple[AnswerPayload, str, int]:
        return generate_with_repair(self.generate, prompt, query_id, max_repairs)
