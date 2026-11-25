"""Typed configuration for the B0-B6 system and retrieval experiments."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

Chunking = Literal["fixed", "section", "hierarchical"]
RetrievalMode = Literal["none", "dense", "bm25", "hybrid", "hybrid_rerank"]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ModelConfig(_Model):
    name: str = "Qwen/Qwen2.5-0.5B-Instruct"
    dtype: str = "float32"
    max_new_tokens: int = 220
    temperature: float = 0.2
    top_p: float = 0.9
    repetition_penalty: float = 1.05
    seed: int = 1


class PromptConfig(_Model):
    registry_id: str = "structured_v1"
    few_shot: bool = False
    max_examples: int = 5


class RetrievalConfig(_Model):
    mode: RetrievalMode = "none"
    chunking: Chunking = "section"
    top_k_dense: int = 50
    top_k_bm25: int = 0
    fusion: Literal["none", "rrf"] = "none"
    rrf_k: int = 60
    rerank: bool = False
    rerank_top_n: int = 50
    final_k: int = 10
    filters: bool = False
    model_name: str = "BAAI/bge-small-en-v1.5"
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L6-v2"
    index_dir: str | None = None
    passages: str | None = None


class VerificationConfig(_Model):
    enabled: bool = False
    nli_model: str = "cross-encoder/nli-deberta-v3-base"
    nli_threshold: float = 0.5
    max_repair_rounds: int = 2
    keep_refuted: bool = False
    abstain_on_unsupported: bool = True


class AbstainConfig(_Model):
    enabled: bool = False
    sufficiency: bool = False
    sufficiency_threshold: float = 0.35


class AgentConfig(_Model):
    enabled: bool = False


class BudgetConfig(_Model):
    context_tokens: int = 2000


class SystemConfig(_Model):
    id: str
    parent: str | None = None
    model: ModelConfig = Field(default_factory=ModelConfig)
    prompt: PromptConfig = Field(default_factory=PromptConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    verification: VerificationConfig = Field(default_factory=VerificationConfig)
    abstain: AbstainConfig = Field(default_factory=AbstainConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    budget: BudgetConfig = Field(default_factory=BudgetConfig)


class RetrievalExperimentConfig(_Model):
    id: str
    retrieval: RetrievalConfig


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_system_config(path: Path) -> SystemConfig:
    return SystemConfig.model_validate(load_yaml(path))


def load_retrieval_config(path: Path) -> RetrievalExperimentConfig:
    return RetrievalExperimentConfig.model_validate(load_yaml(path))


def flatten_config(value, prefix: str = "") -> dict[str, object]:
    """Flatten nested config dicts for precise equality checks."""
    if isinstance(value, dict):
        flat: dict[str, object] = {}
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else key
            flat.update(flatten_config(child, child_prefix))
        return flat
    if isinstance(value, list):
        return {prefix: tuple(value)}
    return {prefix: value}
