from __future__ import annotations

from recipe_qa.config import RetryConfig
from recipe_qa.pipeline.retry import RetryPolicy


def test_retry_disabled_returns_original_only():
    policy = RetryPolicy(RetryConfig(enabled=False, max_retries=2))
    assert policy.plan("old recipe").queries == ("old recipe",)


def test_retry_bounded_variants_are_distinct():
    policy = RetryPolicy(RetryConfig(enabled=True, max_retries=2))
    plan = policy.plan("old recipe")
    assert plan.queries == (
        "old recipe",
        "old recipe recipe",
        "old recipe ingredients directions",
    )


def test_retry_zero_budget_returns_original_only():
    policy = RetryPolicy(RetryConfig(enabled=True, max_retries=0))
    assert policy.plan("old recipe").queries == ("old recipe",)


def test_retry_negative_budget_returns_original_only():
    policy = RetryPolicy(RetryConfig(enabled=True, max_retries=-1))
    assert policy.plan("old recipe").queries == ("old recipe",)


def test_retry_plan_is_serializable():
    policy = RetryPolicy(RetryConfig(enabled=True, max_retries=1))
    assert policy.plan("old recipe").to_dict() == {
        "queries": ["old recipe", "old recipe recipe"]
    }
