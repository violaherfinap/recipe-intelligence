from __future__ import annotations

from pathlib import Path

from recipe_qa.config import flatten_config, load_yaml

ROOT = Path("configs")


def diff_keys(left: dict, right: dict) -> set[str]:
    left_flat = flatten_config(left)
    right_flat = flatten_config(right)
    keys = set(left_flat) | set(right_flat)
    return {
        key
        for key in keys
        if left_flat.get(key) != right_flat.get(key)
        and key not in {"id", "parent"}
    }


def config(name: str) -> dict:
    return load_yaml(ROOT / f"{name}.yaml")


def test_b0_b1_diff_is_prompt_and_abstain():
    assert diff_keys(config("b0"), config("b1")) == {
        "prompt.few_shot",
        "abstain.enabled",
    }


def test_b1_b2_diff_is_retrieval_mode_and_rag_prompt():
    # B2/B3 use a zero-shot RAG prompt: the 0.5B model copies long few-shot
    # examples instead of answering the new question. B1 remains few-shot.
    assert diff_keys(config("b1"), config("b2")) == {
        "retrieval.mode",
        "prompt.few_shot",
    }


def test_b2_b3_diff_is_retrieval_only():
    allowed = {
        "retrieval.chunking",
        "retrieval.mode",
        "retrieval.top_k_bm25",
        "retrieval.fusion",
        "retrieval.rrf_k",
        "retrieval.rerank",
        "retrieval.rerank_top_n",
        "retrieval.final_k",
        "retrieval.filters",
    }
    assert diff_keys(config("b2"), config("b3")) <= allowed
    assert diff_keys(config("b2"), config("b3"))


def test_b3_b4_diff_is_grounding_planner_retry():
    allowed = {
        "verification.enabled",
        "verification.nli_model",
        "verification.nli_threshold",
        "verification.max_repair_rounds",
        "verification.keep_refuted",
        "verification.abstain_on_unsupported",
        "abstain.sufficiency",
        "abstain.sufficiency_threshold",
        "planner.enabled",
        "planner.mode",
        "planner.max_subqueries",
        "retry.enabled",
        "retry.max_retries",
        "retry.min_sufficiency",
    }
    assert diff_keys(config("b3"), config("b4")) <= allowed
    assert diff_keys(config("b3"), config("b4"))
