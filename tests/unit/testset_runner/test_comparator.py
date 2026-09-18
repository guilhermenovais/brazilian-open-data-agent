"""Unit tests for compare_runs's transition-bucket logic and hash-gating
(data-model.md's ComparisonEntry.transition rule)."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from testset_runner.comparator import compare_runs
from testset_runner.exceptions import IncompatibleRunsError
from testset_runner.models import (
    QuestionResult,
    RunSummary,
    TargetConfiguration,
    Testset,
    TestRun,
)


class InMemoryRunStore:
    def __init__(self, runs: dict[str, TestRun]) -> None:
        self._runs = runs

    def save(self, run: TestRun) -> str:
        self._runs[run.run_id] = run
        return run.run_id

    def load(self, path: str | Path) -> TestRun:
        return self._runs[str(path)]


def _result(n: int, status: str) -> QuestionResult:
    return QuestionResult(
        n=n,
        question=f"Question {n}",
        expected="10",
        category="single-lookup",
        actual_answer="10",
        agent_outcome="full",
        dataset_key="sample",
        steps=[],
        match_status=status,
    )


def _run(run_id: str, content_hash: str, statuses: dict[int, str]) -> TestRun:
    results = [_result(n, status) for n, status in statuses.items()]
    summary = RunSummary(
        total_questions=len(results),
        match_rate=0.0,
        by_status={},
        by_category={},
        target_unreachable=False,
    )
    return TestRun(
        run_id=run_id,
        created_at=datetime.now(timezone.utc),
        testset=Testset(path="t.json", content_hash=content_hash, questions=[]),
        target=TargetConfiguration(model_name="fake"),
        results=results,
        summary=summary,
    )


def _compare(statuses_a: dict[int, str], statuses_b: dict[int, str]):
    run_a = _run("a", "hash1", statuses_a)
    run_b = _run("b", "hash1", statuses_b)
    store = InMemoryRunStore({"a": run_a, "b": run_b})
    return compare_runs("a", "b", store=store)


@pytest.mark.parametrize(
    "status_a,status_b,expected_transition",
    [
        ("matched", "matched", "still_passing"),
        ("not_matched", "matched", "newly_passing"),
        ("needs_review", "matched", "newly_passing"),
        ("errored", "matched", "newly_passing"),
        ("matched", "not_matched", "newly_failing"),
        ("matched", "needs_review", "newly_failing"),
        ("matched", "errored", "newly_failing"),
        ("not_matched", "not_matched", "still_failing"),
        ("needs_review", "not_matched", "still_failing"),
        ("not_matched", "needs_review", "still_failing"),
        ("needs_review", "errored", "still_failing"),
        ("needs_review", "needs_review", "unchanged_other"),
        ("errored", "errored", "unchanged_other"),
    ],
)
def test_transition_bucket_rules(status_a: str, status_b: str, expected_transition: str) -> None:
    comparison = _compare({1: status_a}, {1: status_b})
    assert comparison.entries[0].transition == expected_transition


def test_mismatched_content_hash_raises_before_any_entry_is_built() -> None:
    run_a = _run("a", "hash1", {1: "matched"})
    run_b = _run("b", "hash2", {1: "matched"})
    store = InMemoryRunStore({"a": run_a, "b": run_b})

    with pytest.raises(IncompatibleRunsError):
        compare_runs("a", "b", store=store)
