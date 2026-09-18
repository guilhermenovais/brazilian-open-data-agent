"""Unit tests for StepBudget and the outcome clamp (quickstart.md Scenarios 2-3)."""

from qa_agent.capabilities import _clamp_outcome
from qa_agent.step_budget import StepBudget


def test_try_reserve_allows_exactly_ten_then_refuses() -> None:
    budget = StepBudget(limit=10)
    for _ in range(10):
        assert budget.try_reserve() is True
    assert budget.try_reserve() is False


def test_try_reserve_refusal_does_not_increment_attempts_further() -> None:
    budget = StepBudget(limit=10)
    for _ in range(10):
        budget.try_reserve()
    budget.try_reserve()
    budget.try_reserve()
    assert budget.attempts == 10


def test_record_success_increments_successes() -> None:
    budget = StepBudget(limit=10)
    budget.try_reserve()
    budget.record_success()
    budget.try_reserve()
    budget.record_success()
    assert budget.successes == 2


def test_clamp_forces_none_when_zero_successes_even_if_reported_full() -> None:
    budget = StepBudget(limit=10)
    budget.try_reserve()  # one attempt, no record_success() — e.g. it raised ModelRetry
    assert _clamp_outcome(reported="full", budget=budget) == "none"


def test_clamp_keeps_reported_outcome_when_at_least_one_success() -> None:
    budget = StepBudget(limit=10)
    budget.try_reserve()
    budget.record_success()
    assert _clamp_outcome(reported="full", budget=budget) == "full"
    assert _clamp_outcome(reported="partial", budget=budget) == "partial"
