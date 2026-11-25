"""Prompt rendering and local generation."""

from .generate import AnswerGenerator, extract_json_object, parse_answer
from .prompt import (
    format_evidence,
    format_examples,
    load_examples,
    load_registry,
    render_prompt,
)
from .schema import AnswerPayload, Claim, EvidenceItem

__all__ = [
    "AnswerGenerator",
    "AnswerPayload",
    "Claim",
    "EvidenceItem",
    "extract_json_object",
    "format_evidence",
    "format_examples",
    "load_examples",
    "load_registry",
    "parse_answer",
    "render_prompt",
]
